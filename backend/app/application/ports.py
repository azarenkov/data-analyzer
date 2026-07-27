from typing import Protocol

from app.domain.dataset.entity import Dataset
from app.domain.dataset.results import Insight
from app.domain.dataset.table import DataTable


class DatasetParser(Protocol):
    def parse(self, filename: str, content: bytes) -> DataTable: ...


class ReportBuilder(Protocol):
    def build(self, dataset: Dataset, insights: list[Insight]) -> bytes: ...
