from app.domain.dataset.repository import DatasetRepository
from app.domain.dataset.values import ExportFormat, FilterSpec, SortSpec


class ExportRows:
    def __init__(self, repository: DatasetRepository) -> None:
        self._repository = repository

    def execute(
        self,
        dataset_id: str,
        filters: list[FilterSpec],
        sort: list[SortSpec],
        fmt: ExportFormat,
    ) -> tuple[bytes, str]:
        dataset = self._repository.get(dataset_id)
        content = dataset.table.export(filters=filters, sort=sort, fmt=fmt)
        stem = dataset.name.rsplit(".", 1)[0]
        return content, f"{stem}_filtered.{fmt.value}"
