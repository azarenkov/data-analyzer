from app.domain.dataset.entity import Dataset
from app.domain.dataset.repository import DatasetRepository


class ListDatasets:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(self) -> list[Dataset]:
        return sorted(
            self._repository.list_all(),
            key=lambda d: d.uploaded_at,
            reverse=True,
        )
