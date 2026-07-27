import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { useUpload } from "../../hooks/useUpload";

export function UploadScreen({ onUploaded }: { onUploaded: (id: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const upload = useUpload(onUploaded);

  const handleFile = (file: File | undefined) => {
    if (file) upload.mutate(file);
  };

  const handleDrop = (event: DragEvent) => {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files[0]);
  };

  return (
    <div className="upload-screen">
      <header className="upload-brand">
        <span className="wordmark">Разбор</span>
        <span className="upload-brand-sub">внутренний инструмент анализа данных</span>
      </header>
      <main className="upload-main">
        <h1 className="upload-title">
          Файл — на вход.
          <br />
          Понимание — на выход.
        </h1>
        <p className="upload-lede">
          Загрузите таблицу и получите структуру, статистику, графики и инсайты — без
          ноутбуков и SQL.
        </p>
        <div
          className={`dropzone${dragging ? " dragging" : ""}${upload.isPending ? " busy" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.json"
            hidden
            onChange={(e) => handleFile(e.target.files?.[0] ?? undefined)}
          />
          {upload.isPending ? (
            <span className="dropzone-status">Читаем файл…</span>
          ) : (
            <>
              <span className="dropzone-cta">Перетащите файл сюда или нажмите, чтобы выбрать</span>
              <span className="dropzone-formats">csv · xlsx · xls · json</span>
            </>
          )}
        </div>
        {upload.isError && <p className="upload-error">{(upload.error as Error).message}</p>}
      </main>
      <footer className="upload-footer">
        <span>шаг 1 — загрузка</span>
        <span>шаг 2 — просмотр и фильтры</span>
        <span>шаг 3 — аналитика и инсайты</span>
        <span>шаг 4 — экспорт</span>
      </footer>
    </div>
  );
}
