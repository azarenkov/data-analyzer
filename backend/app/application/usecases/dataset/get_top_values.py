from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import TablePage
from app.domain.dataset.values import FilterSpec


class GetTopValues:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(
        self,
        dataset_id: str,
        metric: str,
        limit: int,
        ascending: bool,
        filters: list[FilterSpec],
    ) -> TablePage:
        dataset = self._repository.get(dataset_id)
        return dataset.table.top(metric=metric, limit=limit, ascending=ascending, filters=filters)
