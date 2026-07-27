import { useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetsApi } from "../../api/datasets";
import { useUpload } from "../../hooks/useUpload";
import type { DatasetMeta } from "../../types/dataset";

interface SidebarProps {
  datasets: DatasetMeta[];
  activeId: string;
  onSelect: (id: string) => void;
}

export function Sidebar({ datasets, activeId, onSelect }: SidebarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const upload = useUpload(onSelect);
  const remove = useMutation({
    mutationFn: (id: string) => datasetsApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }),
  });

  return (
    <aside className="sidebar">
      <div className="wordmark sidebar-wordmark">Разбор</div>
      <div className="sidebar-section-label">Файлы</div>
      <nav className="sidebar-list">
        {datasets.map((dataset) => (
          <div
            key={dataset.id}
            className={`sidebar-item${dataset.id === activeId ? " active" : ""}`}
            onClick={() => onSelect(dataset.id)}
          >
            <div className="sidebar-item-name" title={dataset.name}>
              {dataset.name}
            </div>
            <div className="sidebar-item-meta">
              {dataset.rowCount.toLocaleString("ru-RU")} × {dataset.columnCount}
            </div>
            <button
              className="sidebar-item-delete"
              title="Удалить"
              onClick={(e) => {
                e.stopPropagation();
                remove.mutate(dataset.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </nav>
      <button
        className="btn btn-primary sidebar-upload"
        disabled={upload.isPending}
        onClick={() => inputRef.current?.click()}
      >
        {upload.isPending ? "Загрузка…" : "+ Загрузить файл"}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls,.json"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload.mutate(file);
          e.target.value = "";
        }}
      />
      {upload.isError && <p className="sidebar-error">{(upload.error as Error).message}</p>}
    </aside>
  );
}
