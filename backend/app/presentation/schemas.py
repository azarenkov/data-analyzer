from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.dataset.values import (
    Aggregation,
    ColumnKind,
    ExportFormat,
    FilterOperator,
    TimeFrequency,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ColumnSchema(ApiModel):
    name: str
    dtype: str
    kind: ColumnKind
    missing: int
    unique: int


class DatasetMetaSchema(ApiModel):
    id: str
    name: str
    uploaded_at: datetime
    row_count: int
    column_count: int


class OverviewSchema(ApiModel):
    dataset: DatasetMetaSchema
    columns: list[ColumnSchema]
    preview: list[dict[str, Any]]


class FilterSchema(ApiModel):
    column: str
    operator: FilterOperator
    value: Any = None


class SortSchema(ApiModel):
    column: str
    descending: bool = False


class QueryRequest(ApiModel):
    filters: list[FilterSchema] = Field(default_factory=list)
    sort: list[SortSchema] = Field(default_factory=list)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=500)


class ExportRequest(ApiModel):
    filters: list[FilterSchema] = Field(default_factory=list)
    sort: list[SortSchema] = Field(default_factory=list)
    format: ExportFormat = ExportFormat.CSV


class PageSchema(ApiModel):
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class NumericSummarySchema(ApiModel):
    column: str
    count: int
    mean: float | None
    std: float | None
    minimum: float | None
    p25: float | None
    median: float | None
    p75: float | None
    maximum: float | None


class GroupRowSchema(ApiModel):
    label: str
    value: int | float | str
    count: int


class TimePointSchema(ApiModel):
    period: str
    value: int | float | str


class InsightSchema(ApiModel):
    kind: str
    title: str
    detail: str
    magnitude: float


class GroupByParams(ApiModel):
    by: str
    metric: str | None = None
    aggregation: Aggregation = Aggregation.SUM


class TimeSeriesParams(ApiModel):
    date_column: str
    metric: str | None = None
    aggregation: Aggregation = Aggregation.SUM
    frequency: TimeFrequency = TimeFrequency.DAY
