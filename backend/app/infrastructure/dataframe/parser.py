import csv
import io
import zipfile

import pandas as pd

from app.domain.dataset.errors import DomainError, FileParsingError, UnsupportedFileError
from app.infrastructure.dataframe.pandas_table import PandasDataTable

MAX_DECOMPRESSED_BYTES = 200 * 1024 * 1024


class PandasDatasetParser:
    def parse(self, filename: str, content: bytes) -> PandasDataTable:
        extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        try:
            frame = self._read(extension, filename, content)
        except DomainError:
            raise
        except Exception as error:
            raise FileParsingError(str(error)) from error
        return PandasDataTable(frame)

    def _read(self, extension: str, filename: str, content: bytes) -> pd.DataFrame:
        if extension == "csv":
            text = self._decode(content)
            frame = pd.read_csv(
                io.StringIO(text),
                sep=self._detect_delimiter(text),
                keep_default_na=False,
                na_values=[""],
                dtype=str,
            )
            return frame.apply(self._infer_series)
        if extension in ("xlsx", "xls"):
            if extension == "xlsx":
                self._check_decompressed_size(content)
            return pd.read_excel(
                io.BytesIO(content),
                keep_default_na=False,
                na_values=[""],
                dtype_backend="numpy_nullable",
            )
        if extension == "json":
            return pd.read_json(io.BytesIO(content))
        raise UnsupportedFileError(filename)

    @staticmethod
    def _check_decompressed_size(content: bytes) -> None:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                total = sum(entry.file_size for entry in archive.infolist())
        except zipfile.BadZipFile as error:
            raise FileParsingError("file is not a valid xlsx workbook") from error
        if total > MAX_DECOMPRESSED_BYTES:
            raise FileParsingError(
                f"workbook expands to more than {MAX_DECOMPRESSED_BYTES // (1024 * 1024)} MB"
            )

    @staticmethod
    def _infer_series(series: pd.Series) -> pd.Series:
        non_null = series.dropna()
        if non_null.empty:
            return series
        if series.str.strip().str.fullmatch(r"[+-]?0\d+").dropna().any():
            return series
        try:
            return series.astype("Int64")
        except (ValueError, TypeError, OverflowError):
            pass
        if series.str.strip().str.fullmatch(r"[+-]?\d+").dropna().all():
            return series
        try:
            return series.astype("Float64")
        except (ValueError, TypeError, OverflowError):
            pass
        lowered = series.str.strip().str.lower()
        if lowered.dropna().isin(("true", "false")).all():
            return lowered.map({"true": True, "false": False}).astype("boolean")
        return series

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        sample = text[:8192]
        try:
            return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            return ","

    @staticmethod
    def _decode(content: bytes) -> str:
        if content.startswith((b"\xff\xfe", b"\xfe\xff")):
            try:
                return content.decode("utf-16")
            except UnicodeDecodeError:
                pass
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")
