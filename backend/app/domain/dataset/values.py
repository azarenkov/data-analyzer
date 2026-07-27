from dataclasses import dataclass
from enum import StrEnum


class ColumnKind(StrEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"


class FilterOperator(StrEnum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    IN = "in"


class Aggregation(StrEnum):
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    COUNT = "count"


class TimeFrequency(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"


class ExportFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    dtype: str
    kind: ColumnKind
    missing: int
    unique: int


@dataclass(frozen=True)
class FilterSpec:
    column: str
    operator: FilterOperator
    value: object


@dataclass(frozen=True)
class SortSpec:
    column: str
    descending: bool
