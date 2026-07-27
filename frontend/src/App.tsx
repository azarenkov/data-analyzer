import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { datasetsApi } from "./api/datasets";
import { UploadScreen } from "./components/upload/UploadScreen";
import { Sidebar } from "./components/layout/Sidebar";
import { Workspace } from "./components/workspace/Workspace";

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: datasetsApi.list });

  const list = datasets.data ?? [];
  const activeId = list.some((d) => d.id === selectedId) ? selectedId : (list[0]?.id ?? null);

  if (datasets.isLoading) {
    return <div className="app-boot">Загрузка…</div>;
  }

  if (!activeId) {
    return <UploadScreen onUploaded={setSelectedId} />;
  }

  return (
    <div className="app-shell">
      <Sidebar datasets={list} activeId={activeId} onSelect={setSelectedId} />
      <Workspace key={activeId} datasetId={activeId} />
    </div>
  );
}
