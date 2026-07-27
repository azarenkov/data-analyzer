import io
import json
import math

import numpy as np
import pandas as pd

from app.domain.dataset.errors import ColumnNotFoundError, InvalidQueryError
from app.domain.dataset.results import (
    CorrelationPair,
    GroupRow,
    NumericSummary,
    SegmentChange,
    TablePage,
    TimePoint,
)
from app.domain.dataset.values import (
    Aggregation,
    ColumnInfo,
    ColumnKind,
    ExportFormat,
    FilterOperator,
    FilterSpec,
    SortSpec,
    TimeFrequency,
)

_FREQ_MAP = {
    TimeFrequency.DAY: "D",
    TimeFrequency.WEEK: "W-SUN",
    TimeFrequency.MONTH: "MS",
    TimeFrequency.QUARTER: "QS",
}

def _finite_mask(series: pd.Series) -> pd.Series:
    mask = series.notna()
    if pd.api.types.is_float_dtype(series):
        mask = mask & series.ne(np.inf) & series.ne(-np.inf)
    if mask.isna().any():
        mask = mask.fillna(False)
    return mask.astype(bool)


def _sum_with_min_count(series: pd.Series) -> float:
    return series.sum(min_count=1)


_AGG_MAP = {
    Aggregation.SUM: _sum_with_min_count,
    Aggregation.MEAN: "mean",
    Aggregation.MEDIAN: "median",
    Aggregation.MIN: "min",
    Aggregation.MAX: "max",
}

_JS_SAFE_INT = 9_007_199_254_740_991

_EXCEL_SAFE_INT = 999_999_999_999_999

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

_EXCEL_MAX_ROWS = 1_048_575

_EXCEL_MAX_COLS = 16_384

_CORR_MAX_COLS = 40


def excel_safe_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        series = out[column]
        if isinstance(series.dtype, pd.DatetimeTZDtype):
            out[column] = series.dt.tz_convert("UTC").dt.tz_localize(None)
        elif pd.api.types.is_integer_dtype(series):
            out[column] = series.astype(object).map(
                lambda v: str(v) if pd.notna(v) and abs(int(v)) > _EXCEL_SAFE_INT else v
            )
        elif series.dtype == object:
            out[column] = series.map(
                lambda v: str(v)
                if isinstance(v, int) and not isinstance(v, bool) and abs(v) > _EXCEL_SAFE_INT
                else v
            )
    return out


def safe_excel_writer(buffer: io.BytesIO) -> pd.ExcelWriter:
    return pd.ExcelWriter(
        buffer,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_formulas": False, "strings_to_urls": False}},
    )


class PandasDataTable:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._df = self._normalize(frame)

    @staticmethod
    def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
        df = frame.copy()
        df.columns = PandasDataTable._unique_names(str(c).strip() for c in df.columns)
        for column in df.columns:
            series = df[column]
            if not pd.api.types.is_string_dtype(series) and series.dtype != object:
                continue
            if series.map(lambda v: isinstance(v, (list, dict))).any():
                series = series.map(
                    lambda v: json.dumps(v, ensure_ascii=False)
                    if isinstance(v, (list, dict))
                    else v
                )
                df[column] = series
            non_null = series.dropna()
            if non_null.empty:
                continue
            parsed = PandasDataTable._parse_datetime(non_null)
            if parsed is not None and parsed.notna().all():
                full = PandasDataTable._parse_datetime(series)
                if full is not None:
                    df[column] = full
        return df

    @staticmethod
    def _parse_datetime(series: pd.Series) -> pd.Series | None:
        try:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
            if pd.api.types.is_datetime64_any_dtype(parsed):
                return parsed
        except (ValueError, TypeError):
            pass
        try:
            parsed = pd.to_datetime(series, errors="coerce", format="mixed", utc=True)
        except (ValueError, TypeError):
            return None
        return parsed if pd.api.types.is_datetime64_any_dtype(parsed) else None

    @staticmethod
    def _unique_names(names) -> list[str]:
        seen: set[str] = set()
        result = []
        for raw in names:
            base = raw or "column"
            name = base
            suffix = 1
            while name in seen:
                suffix += 1
                name = f"{base}_{suffix}"
            seen.add(name)
            result.append(name)
        return result

    def frame(self) -> pd.DataFrame:
        return self._df.copy()

    def row_count(self) -> int:
        return int(len(self._df))

    def column_count(self) -> int:
        return int(len(self._df.columns))

    def columns(self) -> list[ColumnInfo]:
        result = []
        for column in self._df.columns:
            series = self._df[column]
            result.append(
                ColumnInfo(
                    name=column,
                    dtype=str(series.dtype),
                    kind=self._kind_of(series),
                    missing=int(series.isna().sum()),
                    unique=int(series.nunique(dropna=True)),
                )
            )
        return result

    @staticmethod
    def _kind_of(series: pd.Series) -> ColumnKind:
        if pd.api.types.is_bool_dtype(series):
            return ColumnKind.BOOLEAN
        if pd.api.types.is_numeric_dtype(series):
            return ColumnKind.NUMERIC
        if pd.api.types.is_datetime64_any_dtype(series):
            return ColumnKind.DATETIME
        unique = series.nunique(dropna=True)
        if unique <= 50 and unique <= max(20, len(series) * 0.5):
            return ColumnKind.CATEGORICAL
        return ColumnKind.TEXT

    def rows(
        self,
        filters: list[FilterSpec],
        sort: list[SortSpec],
        page: int,
        page_size: int,
    ) -> TablePage:
        df = self._apply_sort(self._apply_filters(self._df, filters), sort)
        total = int(len(df))
        start = max(page - 1, 0) * page_size
        return TablePage(
            rows=self._records(df.iloc[start : start + page_size]),
            total=total,
            page=page,
            page_size=page_size,
        )

    def summary(self) -> list[NumericSummary]:
        result = []
        for column in self._df.columns:
            series = self._df[column]
            if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
                continue
            values = series[_finite_mask(series)]
            described = values.describe()
            result.append(
                NumericSummary(
                    column=column,
                    count=int(described.get("count", 0)),
                    mean=self._safe_float(described.get("mean")),
                    std=self._safe_float(described.get("std")),
                    minimum=self._safe_float(described.get("min")),
                    p25=self._safe_float(described.get("25%")),
                    median=self._safe_float(described.get("50%")),
                    p75=self._safe_float(described.get("75%")),
                    maximum=self._safe_float(described.get("max")),
                )
            )
        return result

    def top(
        self,
        metric: str,
        limit: int,
        ascending: bool,
        filters: list[FilterSpec],
    ) -> TablePage:
        self._require_numeric(metric)
        df = self._apply_filters(self._df, filters)
        df = df[_finite_mask(df[metric])]
        df = df.sort_values(metric, ascending=ascending).head(limit)
        return TablePage(rows=self._records(df), total=int(len(df)), page=1, page_size=limit)

    def group_by(
        self,
        by: str,
        metric: str | None,
        aggregation: Aggregation,
        filters: list[FilterSpec],
    ) -> list[GroupRow]:
        self._require_column(by)
        df = self._apply_filters(self._df, filters)
        grouped = df.groupby(by, dropna=False)
        counts = grouped.size()
        if metric is None or aggregation == Aggregation.COUNT:
            values = counts.astype(float)
        else:
            self._require_numeric(metric)
            values = grouped[metric].agg(_AGG_MAP[aggregation])
        result = []
        for label, value in values.items():
            if pd.isna(value) or not math.isfinite(float(value)):
                continue
            result.append(
                GroupRow(
                    label="(пусто)" if pd.isna(label) else str(label),
                    value=float(value),
                    count=int(counts.get(label, 0)),
                )
            )
        result.sort(key=lambda g: g.value, reverse=True)
        return result

    def time_series(
        self,
        date_column: str,
        metric: str | None,
        aggregation: Aggregation,
        frequency: TimeFrequency,
        filters: list[FilterSpec],
    ) -> list[TimePoint]:
        self._require_datetime(date_column)
        df = self._apply_filters(self._df, filters).dropna(subset=[date_column])
        grouper = pd.Grouper(key=date_column, freq=_FREQ_MAP[frequency])
        if metric is None or aggregation == Aggregation.COUNT:
            values = df.groupby(grouper).size().astype(float)
        else:
            self._require_numeric(metric)
            values = df.groupby(grouper)[metric].agg(_AGG_MAP[aggregation])
        result = []
        for period, value in values.items():
            if pd.isna(value) or not math.isfinite(float(value)):
                continue
            if frequency == TimeFrequency.WEEK:
                period = period - pd.Timedelta(days=6)
            result.append(TimePoint(period=self._period_label(period, frequency), value=float(value)))
        return result

    @staticmethod
    def _period_label(period: pd.Timestamp, frequency: TimeFrequency) -> str:
        if frequency == TimeFrequency.MONTH:
            return period.strftime("%Y-%m")
        if frequency == TimeFrequency.QUARTER:
            return f"{period.year}-Q{period.quarter}"
        return period.strftime("%Y-%m-%d")

    def halves_change(
        self,
        date_column: str,
        metric: str,
        by: str | None,
    ) -> list[SegmentChange]:
        self._require_datetime(date_column)
        self._require_numeric(metric)
        df = self._df.dropna(subset=[date_column, metric])
        df = df[_finite_mask(df[metric])]
        if len(df) < 6:
            return []
        start = df[date_column].min()
        end = df[date_column].max()
        midpoint = start + (end - start) / 2
        first_half = df[df[date_column] <= midpoint]
        second_half = df[df[date_column] > midpoint]
        if first_half.empty or second_half.empty:
            return []
        if by is None:
            return self._segment(metric, first_half, second_half, metric)
        self._require_column(by)
        result = []
        for label in df[by].dropna().unique():
            first = first_half[first_half[by] == label]
            second = second_half[second_half[by] == label]
            if len(first) < 3 or len(second) < 3:
                continue
            result.extend(self._segment(str(label), first, second, metric))
        return result

    @staticmethod
    def _segment(
        label: str, first: pd.DataFrame, second: pd.DataFrame, metric: str
    ) -> list[SegmentChange]:
        first_mean = float(first[metric].mean())
        second_mean = float(second[metric].mean())
        if not (math.isfinite(first_mean) and math.isfinite(second_mean)):
            return []
        change = (
            (second_mean - first_mean) / abs(first_mean) * 100 if first_mean != 0 else None
        )
        return [
            SegmentChange(label=label, first=first_mean, second=second_mean, change_pct=change)
        ]

    def correlation_pairs(self, limit: int) -> list[CorrelationPair]:
        numeric = self._df.select_dtypes(include="number")
        if len(numeric.columns) < 2:
            return []
        numeric = numeric.iloc[:, :_CORR_MAX_COLS]
        matrix = numeric.replace([np.inf, -np.inf], np.nan).corr()
        pairs = []
        cols = list(matrix.columns)
        for i, left in enumerate(cols):
            for right in cols[i + 1 :]:
                value = matrix.loc[left, right]
                if pd.isna(value):
                    continue
                pairs.append(CorrelationPair(left=left, right=right, value=float(value)))
        pairs.sort(key=lambda p: abs(p.value), reverse=True)
        return pairs[:limit]

    def export(
        self,
        filters: list[FilterSpec],
        sort: list[SortSpec],
        fmt: ExportFormat,
    ) -> bytes:
        df = self._apply_sort(self._apply_filters(self._df, filters), sort)
        if fmt == ExportFormat.CSV:
            return self._escape_csv_formulas(df).to_csv(index=False).encode("utf-8-sig")
        if len(df) > _EXCEL_MAX_ROWS:
            raise InvalidQueryError(
                f"XLSX supports at most {_EXCEL_MAX_ROWS} rows; export CSV instead"
            )
        if len(df.columns) > _EXCEL_MAX_COLS:
            raise InvalidQueryError(
                f"XLSX supports at most {_EXCEL_MAX_COLS} columns; export CSV instead"
            )
        buffer = io.BytesIO()
        with safe_excel_writer(buffer) as writer:
            excel_safe_frame(df).to_excel(writer, index=False, sheet_name="Data")
        return buffer.getvalue()

    @staticmethod
    def _escape_csv_formulas(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for column in out.columns:
            series = out[column]
            if not (pd.api.types.is_string_dtype(series) or series.dtype == object):
                continue
            mask = series.notna() & series.astype(str).str.startswith(_FORMULA_PREFIXES)
            if mask.any():
                out.loc[mask, column] = "'" + series[mask].astype(str)
        return out

    def _apply_filters(self, df: pd.DataFrame, filters: list[FilterSpec]) -> pd.DataFrame:
        for spec in filters:
            self._require_column(spec.column, df)
            series = df[spec.column]
            mask = pd.Series(self._filter_mask(series, spec), index=df.index)
            if mask.isna().any():
                mask = mask.fillna(False)
            df = df[mask.astype(bool)]
        return df

    def _filter_mask(self, series: pd.Series, spec: FilterSpec) -> pd.Series:
        op = spec.operator
        if op == FilterOperator.CONTAINS:
            return series.notna() & series.astype(str).str.contains(
                str(spec.value), case=False, na=False, regex=False
            )
        if op == FilterOperator.IN:
            values = spec.value if isinstance(spec.value, list) else [spec.value]
            return series.notna() & series.astype(str).isin([str(v) for v in values])
        value = self._coerce(series, spec.value)
        if op == FilterOperator.EQ:
            if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
                return series == value
            return series.astype(str) == str(value)
        if op == FilterOperator.NEQ:
            if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
                return series != value
            return series.astype(str) != str(value)
        if not (
            pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_datetime64_any_dtype(series)
        ):
            raise InvalidQueryError(
                f"Operator '{op.value}' is not supported for column '{spec.column}'"
            )
        if op == FilterOperator.GT:
            return series > value
        if op == FilterOperator.GTE:
            return series >= value
        if op == FilterOperator.LT:
            return series < value
        return series <= value

    @staticmethod
    def _coerce(series: pd.Series, value: object) -> object:
        try:
            if pd.api.types.is_bool_dtype(series):
                if isinstance(value, bool):
                    return value
                text = str(value).strip().lower()
                if text in ("true", "1", "да", "yes"):
                    return True
                if text in ("false", "0", "нет", "no"):
                    return False
                raise InvalidQueryError(f"Invalid boolean filter value '{value}'")
            if pd.api.types.is_integer_dtype(series):
                text = str(value).strip()
                try:
                    return int(text)
                except ValueError:
                    return float(text)
            if pd.api.types.is_numeric_dtype(series):
                return float(value)
            if pd.api.types.is_datetime64_any_dtype(series):
                timestamp = pd.to_datetime(value)
                series_tz = getattr(series.dtype, "tz", None)
                if series_tz is not None and timestamp.tzinfo is None:
                    return timestamp.tz_localize(series_tz)
                if series_tz is None and timestamp.tzinfo is not None:
                    return timestamp.tz_convert("UTC").tz_localize(None)
                return timestamp
        except (TypeError, ValueError) as error:
            raise InvalidQueryError(f"Invalid filter value '{value}'") from error
        return value

    def _apply_sort(self, df: pd.DataFrame, sort: list[SortSpec]) -> pd.DataFrame:
        if not sort:
            return df
        for spec in sort:
            self._require_column(spec.column, df)
        return df.sort_values(
            [s.column for s in sort],
            ascending=[not s.descending for s in sort],
            key=lambda s: s.map(str, na_action="ignore") if s.dtype == object else s,
        )

    def _records(self, df: pd.DataFrame) -> list[dict]:
        converted = df.copy()
        for column in converted.columns:
            series = converted[column]
            if pd.api.types.is_datetime64_any_dtype(series):
                non_null = series.dropna()
                naive = not isinstance(series.dtype, pd.DatetimeTZDtype)
                date_only = naive and (
                    non_null.empty or (non_null.dt.time == pd.Timestamp(0).time()).all()
                )
                if date_only:
                    converted[column] = series.dt.strftime("%Y-%m-%d")
                else:
                    converted[column] = series.map(
                        lambda ts: ts.isoformat() if pd.notna(ts) else None
                    )
        for column in converted.columns:
            series = converted[column]
            if pd.api.types.is_float_dtype(series):
                converted[column] = series.where(_finite_mask(series))
            elif pd.api.types.is_integer_dtype(series):
                converted[column] = series.astype(object).map(
                    lambda v: str(v) if pd.notna(v) and abs(int(v)) > _JS_SAFE_INT else v
                )
            elif series.dtype == object:
                converted[column] = series.map(
                    lambda v: str(v)
                    if isinstance(v, int) and not isinstance(v, bool) and abs(v) > _JS_SAFE_INT
                    else v
                )
        converted = converted.astype(object).where(pd.notna(converted), None)
        return converted.to_dict(orient="records")

    def _require_column(self, column: str, df: pd.DataFrame | None = None) -> None:
        target = self._df if df is None else df
        if column not in target.columns:
            raise ColumnNotFoundError(column)

    def _require_numeric(self, column: str) -> None:
        self._require_column(column)
        if not pd.api.types.is_numeric_dtype(self._df[column]):
            raise InvalidQueryError(f"Column '{column}' is not numeric")

    def _require_datetime(self, column: str) -> None:
        self._require_column(column)
        if not pd.api.types.is_datetime64_any_dtype(self._df[column]):
            raise InvalidQueryError(f"Column '{column}' is not a date column")

    @staticmethod
    def _safe_float(value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        result = float(value)
        return result if math.isfinite(result) else None
