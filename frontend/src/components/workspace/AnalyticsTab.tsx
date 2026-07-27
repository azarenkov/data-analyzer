import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { datasetsApi } from "../../api/datasets";
import { Panel } from "../ui/Panel";
import { Select } from "../ui/Select";
import { DataGrid } from "./DataGrid";
import { GroupBarChart } from "../charts/GroupBarChart";
import { TimeSeriesChart } from "../charts/TimeSeriesChart";
import { AGG_LABELS, FREQ_LABELS, formatNumber } from "../../lib/format";
import type { Aggregation, ColumnInfo, TimeFrequency } from "../../types/dataset";

const AGGREGATIONS: Aggregation[] = ["sum", "mean", "median", "min", "max", "count"];
const FREQUENCIES: TimeFrequency[] = ["day", "week", "month", "quarter"];

export function AnalyticsTab({ datasetId, columns }: { datasetId: string; columns: ColumnInfo[] }) {
  const numericColumns = useMemo(
    () => columns.filter((c) => c.kind === "numeric").map((c) => c.name),
    [columns],
  );
  const categoryColumns = useMemo(
    () => columns.filter((c) => c.kind === "categorical").map((c) => c.name),
    [columns],
  );
  const dateColumns = useMemo(
    () => columns.filter((c) => c.kind === "datetime").map((c) => c.name),
    [columns],
  );

  const [metric, setMetric] = useState(numericColumns[0] ?? "");
  const [topAscending, setTopAscending] = useState(false);
  const [groupCol, setGroupCol] = useState(categoryColumns[0] ?? "");
  const [groupAgg, setGroupAgg] = useState<Aggregation>("sum");
  const [dateColumn, setDateColumn] = useState(dateColumns[0] ?? "");
  const [frequency, setFrequency] = useState<TimeFrequency>("week");
  const [timeAgg, setTimeAgg] = useState<Aggregation>("sum");

  const summary = useQuery({
    queryKey: ["summary", datasetId],
    queryFn: () => datasetsApi.summary(datasetId),
  });

  const top = useQuery({
    queryKey: ["top", datasetId, metric, topAscending],
    queryFn: () => datasetsApi.top(datasetId, metric, 10, topAscending),
    enabled: metric !== "",
    placeholderData: keepPreviousData,
  });

  const groups = useQuery({
    queryKey: ["groups", datasetId, groupCol, metric, groupAgg],
    queryFn: () =>
      datasetsApi.groupBy(datasetId, groupCol, groupAgg === "count" ? null : metric, groupAgg),
    enabled: groupCol !== "" && (groupAgg === "count" || metric !== ""),
    placeholderData: keepPreviousData,
  });

  const series = useQuery({
    queryKey: ["series", datasetId, dateColumn, metric, timeAgg, frequency],
    queryFn: () =>
      datasetsApi.timeSeries(
        datasetId,
        dateColumn,
        timeAgg === "count" ? null : metric,
        timeAgg,
        frequency,
      ),
    enabled: dateColumn !== "" && (timeAgg === "count" || metric !== ""),
    placeholderData: keepPreviousData,
  });

  if (numericColumns.length === 0) {
    return <p className="error-note">В файле нет числовых колонок — аналитика недоступна.</p>;
  }

  const metricOptions = numericColumns.map((name) => ({ value: name, label: name }));
  const aggOptions = AGGREGATIONS.map((a) => ({ value: a, label: AGG_LABELS[a] }));

  return (
    <div className="tab-stack">
      <div className="metric-bar">
        <Select label="Метрика для анализа" value={metric} options={metricOptions} onChange={setMetric} />
      </div>

      <Panel title="Summary statistics" subtitle="Описательная статистика по числовым колонкам">
        {summary.data && (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Колонка</th>
                  <th className="num">Count</th>
                  <th className="num">Mean</th>
                  <th className="num">Std</th>
                  <th className="num">Min</th>
                  <th className="num">P25</th>
                  <th className="num">Median</th>
                  <th className="num">P75</th>
                  <th className="num">Max</th>
                </tr>
              </thead>
              <tbody>
                {summary.data.map((row) => (
                  <tr key={row.column} className={row.column === metric ? "highlight" : undefined}>
                    <td className="mono">{row.column}</td>
                    <td className="num">{formatNumber(row.count)}</td>
                    <td className="num">{formatNumber(row.mean)}</td>
                    <td className="num">{formatNumber(row.std)}</td>
                    <td className="num">{formatNumber(row.minimum)}</td>
                    <td className="num">{formatNumber(row.p25)}</td>
                    <td className="num">{formatNumber(row.median)}</td>
                    <td className="num">{formatNumber(row.p75)}</td>
                    <td className="num">{formatNumber(row.maximum)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel
        title={topAscending ? `Худшие записи по ${metric}` : `Лучшие записи по ${metric}`}
        subtitle="Десять строк с крайними значениями выбранной метрики"
        actions={
          <div className="segmented">
            <button
              className={`segment${!topAscending ? " active" : ""}`}
              onClick={() => setTopAscending(false)}
            >
              Топ
            </button>
            <button
              className={`segment${topAscending ? " active" : ""}`}
              onClick={() => setTopAscending(true)}
            >
              Антитоп
            </button>
          </div>
        }
      >
        <DataGrid columns={columns.map((c) => c.name)} rows={top.data?.rows ?? []} />
      </Panel>

      {categoryColumns.length > 0 && (
        <Panel
          title="Группировка"
          subtitle={`${AGG_LABELS[groupAgg]} ${groupAgg === "count" ? "строк" : `по ${metric}`} в разрезе ${groupCol}`}
          actions={
            <>
              <Select
                label="Категория"
                value={groupCol}
                options={categoryColumns.map((name) => ({ value: name, label: name }))}
                onChange={setGroupCol}
              />
              <Select
                label="Агрегация"
                value={groupAgg}
                options={aggOptions}
                onChange={(v) => setGroupAgg(v as Aggregation)}
              />
            </>
          }
        >
          {groups.data && (
            <GroupBarChart
              data={groups.data}
              valueLabel={groupAgg === "count" ? "строк" : `${AGG_LABELS[groupAgg]} ${metric}`}
            />
          )}
        </Panel>
      )}

      {dateColumns.length > 0 && (
        <Panel
          title="Динамика во времени"
          subtitle={`${AGG_LABELS[timeAgg]} ${timeAgg === "count" ? "строк" : `по ${metric}`} с шагом «${FREQ_LABELS[frequency]}»`}
          actions={
            <>
              <Select
                label="Дата"
                value={dateColumn}
                options={dateColumns.map((name) => ({ value: name, label: name }))}
                onChange={setDateColumn}
              />
              <Select
                label="Агрегация"
                value={timeAgg}
                options={aggOptions}
                onChange={(v) => setTimeAgg(v as Aggregation)}
              />
              <Select
                label="Шаг"
                value={frequency}
                options={FREQUENCIES.map((f) => ({ value: f, label: FREQ_LABELS[f] }))}
                onChange={(v) => setFrequency(v as TimeFrequency)}
              />
            </>
          }
        >
          {series.data && (
            <TimeSeriesChart
              data={series.data}
              valueLabel={timeAgg === "count" ? "строк" : `${AGG_LABELS[timeAgg]} ${metric}`}
            />
          )}
        </Panel>
      )}
    </div>
  );
}
