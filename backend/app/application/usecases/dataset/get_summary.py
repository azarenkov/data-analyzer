from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import NumericSummary


class GetSummary:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(self, dataset_id: str) -> list[NumericSummary]:
        dataset = self._repository.get(dataset_id)
        return dataset.table.summary()
