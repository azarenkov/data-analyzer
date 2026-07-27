from app.application.ports import DatasetParser
from app.domain.dataset.entity import Dataset
from app.domain.dataset.repository import DatasetRepository


class UploadDataset:
    def __init__(self, repository: DatasetRepository, parser: DatasetParser) -> None:
        self._repository = repository
        self._parser = parser

    def execute(self, filename: str, content: bytes) -> Dataset:
        table = self._parser.parse(filename, content)
        dataset = Dataset.create(filename, table)
        self._repository.add(dataset)
        return dataset
