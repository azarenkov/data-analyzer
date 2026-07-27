from dataclasses import dataclass, field

from app.domain.dataset.values import ColumnInfo


@dataclass(frozen=True)
class TablePage:
    rows: list[dict]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class NumericSummary:
    column: str
    count: int
    mean: float | None
    std: float | None
    minimum: float | None
    p25: float | None
    median: float | None
    p75: float | None
    maximum: float | None


@dataclass(frozen=True)
class GroupRow:
    label: str
    value: float
    count: int


@dataclass(frozen=True)
class TimePoint:
    period: str
    value: float


@dataclass(frozen=True)
class SegmentChange:
    label: str
    first: float
    second: float
    change_pct: float | None


@dataclass(frozen=True)
class CorrelationPair:
    left: str
    right: str
    value: float


@dataclass(frozen=True)
class Insight:
    kind: str
    title: str
    detail: str
    magnitude: float


@dataclass(frozen=True)
class DatasetOverview:
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    preview: list[dict] = field(default_factory=list)
