export type ColumnKind = "numeric" | "categorical" | "datetime" | "text" | "boolean";

export type FilterOperator = "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "contains" | "in";

export type Aggregation = "sum" | "mean" | "median" | "min" | "max" | "count";

export type TimeFrequency = "day" | "week" | "month" | "quarter";

export type ExportFormat = "csv" | "xlsx";

export interface DatasetMeta {
  id: string;
  name: string;
  uploadedAt: string;
  rowCount: number;
  columnCount: number;
}

export interface ColumnInfo {
  name: string;
  dtype: string;
  kind: ColumnKind;
  missing: number;
  unique: number;
}

export type Row = Record<string, string | number | boolean | null>;

export interface Overview {
  dataset: DatasetMeta;
  columns: ColumnInfo[];
  preview: Row[];
}

export interface FilterSpec {
  column: string;
  operator: FilterOperator;
  value: unknown;
}

export interface SortSpec {
  column: string;
  descending: boolean;
}

export interface Page {
  rows: Row[];
  total: number;
  page: number;
  pageSize: number;
}

export interface NumericSummary {
  column: string;
  count: number;
  mean: number | null;
  std: number | null;
  minimum: number | null;
  p25: number | null;
  median: number | null;
  p75: number | null;
  maximum: number | null;
}

export interface GroupRow {
  label: string;
  value: number;
  count: number;
}

export interface TimePoint {
  period: string;
  value: number;
}

export interface Insight {
  kind: string;
  title: string;
  detail: string;
  magnitude: number;
}
