from typing import Protocol

from app.domain.dataset.results import (
    CorrelationPair,
    GroupRow,
    NumericSummary,
    SegmentChange,
    TablePage,
    TimePoint,
)
from app.domain.dataset.values import (
    Aggregation,
    ColumnInfo,
    ExportFormat,
    FilterSpec,
    SortSpec,
    TimeFrequency,
)


class DataTable(Protocol):
    def row_count(self) -> int: ...

    def column_count(self) -> int: ...

    def columns(self) -> list[ColumnInfo]: ...

    def rows(
        self,
        filters: list[FilterSpec],
        sort: list[SortSpec],
        page: int,
        page_size: int,
    ) -> TablePage: ...

    def summary(self) -> list[NumericSummary]: ...

    def top(
        self,
        metric: str,
        limit: int,
        ascending: bool,
        filters: list[FilterSpec],
    ) -> TablePage: ...

    def group_by(
        self,
        by: str,
        metric: str | None,
        aggregation: Aggregation,
        filters: list[FilterSpec],
    ) -> list[GroupRow]: ...

    def time_series(
        self,
        date_column: str,
        metric: str | None,
        aggregation: Aggregation,
        frequency: TimeFrequency,
        filters: list[FilterSpec],
    ) -> list[TimePoint]: ...

    def halves_change(
        self,
        date_column: str,
        metric: str,
        by: str | None,
    ) -> list[SegmentChange]: ...

    def correlation_pairs(self, limit: int) -> list[CorrelationPair]: ...

    def export(
        self,
        filters: list[FilterSpec],
        sort: list[SortSpec],
        fmt: ExportFormat,
    ) -> bytes: ...
