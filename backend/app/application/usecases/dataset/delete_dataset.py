from app.domain.dataset.repository import DatasetRepository


class DeleteDataset:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(self, dataset_id: str) -> None:
        self._repository.remove(dataset_id)
