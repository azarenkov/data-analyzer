import io

import pandas as pd

from app.domain.dataset.errors import DomainError, FileParsingError, UnsupportedFileError
from app.infrastructure.dataframe.pandas_table import PandasDataTable


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
            return pd.read_csv(io.StringIO(self._decode(content)), sep=None, engine="python")
        if extension in ("xlsx", "xls"):
            return pd.read_excel(io.BytesIO(content))
        if extension == "json":
            return pd.read_json(io.BytesIO(content))
        raise UnsupportedFileError(filename)

    @staticmethod
    def _decode(content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")
