from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import TimePoint
from app.domain.dataset.values import Aggregation, FilterSpec, TimeFrequency


class GetTimeSeries:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(
        self,
        dataset_id: str,
        date_column: str,
        metric: str | None,
        aggregation: Aggregation,
        frequency: TimeFrequency,
        filters: list[FilterSpec],
    ) -> list[TimePoint]:
        dataset = self._repository.get(dataset_id)
        return dataset.table.time_series(
            date_column=date_column,
            metric=metric,
            aggregation=aggregation,
            frequency=frequency,
            filters=filters,
        )
