from app.domain.dataset.entity import Dataset
from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import DatasetOverview


class GetOverview:
    def __init__(self, repository: DatasetRepository, preview_rows: int = 10) -> None:
        self._repository = repository
        self._preview_rows = preview_rows

    def execute(self, dataset_id: str) -> tuple[Dataset, DatasetOverview]:
        dataset = self._repository.get(dataset_id)
        table = dataset.table
        preview = table.rows(filters=[], sort=[], page=1, page_size=self._preview_rows)
        overview = DatasetOverview(
            row_count=table.row_count(),
            column_count=table.column_count(),
            columns=table.columns(),
            preview=preview.rows,
        )
        return dataset, overview
