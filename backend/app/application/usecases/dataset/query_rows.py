from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.results import TablePage
from app.domain.dataset.values import FilterSpec, SortSpec


class QueryRows:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(
        self,
        dataset_id: str,
        filters: list[FilterSpec],
        sort: list[SortSpec],
        page: int,
        page_size: int,
    ) -> TablePage:
        dataset = self._repository.get(dataset_id)
        return dataset.table.rows(filters=filters, sort=sort, page=page, page_size=page_size)
