from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.domain.dataset.errors import EmptyDatasetError
from app.domain.dataset.table import DataTable


@dataclass
class Dataset:
    id: str
    name: str
    uploaded_at: datetime
    table: DataTable

    @classmethod
    def create(cls, name: str, table: DataTable) -> "Dataset":
        if table.row_count() == 0:
            raise EmptyDatasetError()
        return cls(
            id=str(uuid4()),
            name=name.strip() or "dataset",
            uploaded_at=datetime.now(UTC),
            table=table,
        )
