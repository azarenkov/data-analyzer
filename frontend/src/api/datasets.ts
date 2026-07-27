import { apiDownload, apiGet, apiSend, apiUpload } from "./client";
import type {
  Aggregation,
  DatasetMeta,
  ExportFormat,
  FilterSpec,
  GroupRow,
  Insight,
  NumericSummary,
  Overview,
  Page,
  SortSpec,
  TimeFrequency,
  TimePoint,
} from "../types/dataset";

const BASE = "/api/datasets";

export const datasetsApi = {
  upload: (file: File) => apiUpload<DatasetMeta>(BASE, file),

  list: () => apiGet<DatasetMeta[]>(BASE),

  overview: (id: string) => apiGet<Overview>(`${BASE}/${id}`),

  remove: (id: string) => apiSend<void>(`${BASE}/${id}`, "DELETE"),

  query: (
    id: string,
    body: { filters: FilterSpec[]; sort: SortSpec[]; page: number; pageSize: number },
  ) => apiSend<Page>(`${BASE}/${id}/query`, "POST", body),

  summary: (id: string) => apiGet<NumericSummary[]>(`${BASE}/${id}/summary`),

  top: (id: string, metric: string, limit: number, ascending: boolean) =>
    apiGet<Page>(`${BASE}/${id}/top`, {
      metric,
      limit: String(limit),
      ascending: String(ascending),
    }),

  groupBy: (id: string, by: string, metric: string | null, aggregation: Aggregation) =>
    apiGet<GroupRow[]>(`${BASE}/${id}/group-by`, {
      by,
      aggregation,
      ...(metric ? { metric } : {}),
    }),

  timeSeries: (
    id: string,
    dateColumn: string,
    metric: string | null,
    aggregation: Aggregation,
    frequency: TimeFrequency,
  ) =>
    apiGet<TimePoint[]>(`${BASE}/${id}/time-series`, {
      dateColumn,
      aggregation,
      frequency,
      ...(metric ? { metric } : {}),
    }),

  insights: (id: string) => apiGet<Insight[]>(`${BASE}/${id}/insights`),

  exportRows: (id: string, filters: FilterSpec[], sort: SortSpec[], format: ExportFormat) =>
    apiDownload(`${BASE}/${id}/export`, { filters, sort, format }),

  exportReport: (id: string) => apiDownload(`${BASE}/${id}/report`),
};
