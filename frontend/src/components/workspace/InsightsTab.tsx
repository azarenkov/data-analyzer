import { useQuery } from "@tanstack/react-query";
import { datasetsApi } from "../../api/datasets";

const KIND_META: Record<string, { icon: string; label: string }> = {
  trend: { icon: "↗", label: "тренд" },
  mover: { icon: "⇅", label: "изменение" },
  correlation: { icon: "∿", label: "корреляция" },
  concentration: { icon: "◉", label: "концентрация" },
  quality: { icon: "!", label: "качество данных" },
};

export function InsightsTab({ datasetId }: { datasetId: string }) {
  const insights = useQuery({
    queryKey: ["insights", datasetId],
    queryFn: () => datasetsApi.insights(datasetId),
  });

  if (insights.isLoading) return <p className="muted">Считаем инсайты…</p>;
  if (insights.isError) return <p className="error-note">{(insights.error as Error).message}</p>;
  if (!insights.data || insights.data.length === 0) {
    return <p className="muted">Заметных изменений в данных не нашлось.</p>;
  }

  return (
    <div className="insight-grid">
      {insights.data.map((insight, index) => {
        const meta = KIND_META[insight.kind] ?? { icon: "•", label: insight.kind };
        return (
          <article className={`insight-card kind-${insight.kind}`} key={index}>
            <header className="insight-head">
              <span className="insight-icon">{meta.icon}</span>
              <span className="insight-kind">{meta.label}</span>
            </header>
            <h3 className="insight-title">{insight.title}</h3>
            <p className="insight-detail">{insight.detail}</p>
          </article>
        );
      })}
    </div>
  );
}
