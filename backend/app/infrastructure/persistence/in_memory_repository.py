from threading import RLock

from app.domain.dataset.entity import Dataset
from app.domain.dataset.errors import DatasetNotFoundError


class InMemoryDatasetRepository:
    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._lock = RLock()

    def add(self, dataset: Dataset) -> None:
        with self._lock:
            self._datasets[dataset.id] = dataset

    def get(self, dataset_id: str) -> Dataset:
        with self._lock:
            dataset = self._datasets.get(dataset_id)
        if dataset is None:
            raise DatasetNotFoundError(dataset_id)
        return dataset

    def list_all(self) -> list[Dataset]:
        with self._lock:
            return list(self._datasets.values())

    def remove(self, dataset_id: str) -> None:
        with self._lock:
            if dataset_id not in self._datasets:
                raise DatasetNotFoundError(dataset_id)
            del self._datasets[dataset_id]
