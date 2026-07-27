import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { datasetsApi } from "../../api/datasets";
import { formatNumber } from "../../lib/format";
import { OverviewTab } from "./OverviewTab";
import { DataTab } from "./DataTab";
import { AnalyticsTab } from "./AnalyticsTab";
import { InsightsTab } from "./InsightsTab";

const TABS = [
  { id: "overview", label: "Обзор" },
  { id: "data", label: "Данные" },
  { id: "analytics", label: "Аналитика" },
  { id: "insights", label: "Инсайты" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function Workspace({ datasetId }: { datasetId: string }) {
  const [tab, setTab] = useState<TabId>("overview");
  const overview = useQuery({
    queryKey: ["overview", datasetId],
    queryFn: () => datasetsApi.overview(datasetId),
  });
  const report = useMutation({ mutationFn: () => datasetsApi.exportReport(datasetId) });

  if (overview.isLoading) {
    return <main className="workspace app-boot">Загрузка…</main>;
  }
  if (overview.isError || !overview.data) {
    return (
      <main className="workspace app-boot">
        Не удалось открыть датасет: {(overview.error as Error)?.message}
      </main>
    );
  }

  const { dataset, columns, preview } = overview.data;
  const missing = columns.reduce((acc, c) => acc + c.missing, 0);

  return (
    <main className="workspace">
      <header className="passport">
        <div className="passport-file">
          <div className="passport-name">{dataset.name}</div>
          <div className="passport-date">
            загружен {new Date(dataset.uploadedAt).toLocaleString("ru-RU")}
          </div>
        </div>
        <dl className="passport-stats">
          <div>
            <dt>строк</dt>
            <dd>{formatNumber(dataset.rowCount)}</dd>
          </div>
          <div>
            <dt>колонок</dt>
            <dd>{dataset.columnCount}</dd>
          </div>
          <div>
            <dt>пропусков</dt>
            <dd>{formatNumber(missing)}</dd>
          </div>
        </dl>
        <button className="btn btn-primary" disabled={report.isPending} onClick={() => report.mutate()}>
          {report.isPending ? "Готовим…" : "Скачать отчёт .xlsx"}
        </button>
      </header>

      <nav className="tab-bar">
        {TABS.map((item) => (
          <button
            key={item.id}
            className={`tab${tab === item.id ? " active" : ""}`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="tab-content">
        {tab === "overview" && <OverviewTab columns={columns} preview={preview} />}
        {tab === "data" && <DataTab datasetId={datasetId} columns={columns} />}
        {tab === "analytics" && <AnalyticsTab datasetId={datasetId} columns={columns} />}
        {tab === "insights" && <InsightsTab datasetId={datasetId} />}
      </div>
    </main>
  );
}
