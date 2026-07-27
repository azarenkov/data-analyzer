from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import GroupRow
from app.domain.dataset.values import Aggregation, FilterSpec


class GetGroupBreakdown:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(
        self,
        dataset_id: str,
        by: str,
        metric: str | None,
        aggregation: Aggregation,
        filters: list[FilterSpec],
    ) -> list[GroupRow]:
        dataset = self._repository.get(dataset_id)
        return dataset.table.group_by(by=by, metric=metric, aggregation=aggregation, filters=filters)
