import io

import pandas as pd

from app.domain.dataset.entity import Dataset
from app.domain.dataset.results import Insight
from app.domain.dataset.errors import InvalidQueryError
from app.infrastructure.dataframe.pandas_table import (
    _EXCEL_MAX_COLS,
    _EXCEL_MAX_ROWS,
    excel_safe_frame,
    safe_excel_writer,
)


class XlsxReportBuilder:
    def build(self, dataset: Dataset, insights: list[Insight]) -> bytes:
        table = dataset.table
        if table.row_count() > _EXCEL_MAX_ROWS:
            raise InvalidQueryError(
                f"XLSX report supports at most {_EXCEL_MAX_ROWS} rows; export CSV instead"
            )
        if table.column_count() > _EXCEL_MAX_COLS:
            raise InvalidQueryError(
                f"XLSX report supports at most {_EXCEL_MAX_COLS} columns; export CSV instead"
            )
        overview = pd.DataFrame(
            {
                "Параметр": ["Файл", "Загружен", "Строк", "Колонок"],
                "Значение": [
                    dataset.name,
                    dataset.uploaded_at.strftime("%Y-%m-%d %H:%M UTC"),
                    table.row_count(),
                    table.column_count(),
                ],
            }
        )
        columns = pd.DataFrame(
            [
                {
                    "Колонка": c.name,
                    "Тип": c.dtype,
                    "Категория": c.kind.value,
                    "Пропуски": c.missing,
                    "Уникальных": c.unique,
                }
                for c in table.columns()
            ]
        )
        summary = pd.DataFrame(
            [
                {
                    "Колонка": s.column,
                    "Count": s.count,
                    "Mean": s.mean,
                    "Std": s.std,
                    "Min": s.minimum,
                    "P25": s.p25,
                    "Median": s.median,
                    "P75": s.p75,
                    "Max": s.maximum,
                }
                for s in table.summary()
            ]
        )
        insight_rows = pd.DataFrame(
            [{"Инсайт": i.title, "Описание": i.detail} for i in insights]
        )
        data = excel_safe_frame(
            pd.DataFrame(
                table.rows(filters=[], sort=[], page=1, page_size=max(table.row_count(), 1)).rows
            )
        )

        buffer = io.BytesIO()
        with safe_excel_writer(buffer) as writer:
            overview.to_excel(writer, index=False, sheet_name="Обзор")
            columns.to_excel(writer, index=False, sheet_name="Колонки")
            if not summary.empty:
                summary.to_excel(writer, index=False, sheet_name="Статистика")
            if not insight_rows.empty:
                insight_rows.to_excel(writer, index=False, sheet_name="Инсайты")
            data.to_excel(writer, index=False, sheet_name="Данные")
        return buffer.getvalue()
