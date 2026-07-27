import { useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { datasetsApi } from "../../api/datasets";
import { DataGrid } from "./DataGrid";
import { Select } from "../ui/Select";
import { OPERATOR_LABELS, formatNumber } from "../../lib/format";
import type {
  ColumnInfo,
  ExportFormat,
  FilterOperator,
  FilterSpec,
  SortSpec,
} from "../../types/dataset";

const OPERATORS_BY_KIND: Record<string, FilterOperator[]> = {
  numeric: ["eq", "neq", "gt", "gte", "lt", "lte"],
  datetime: ["gte", "lte", "gt", "lt", "eq"],
  categorical: ["eq", "neq", "contains", "in"],
  text: ["contains", "eq", "neq"],
  boolean: ["eq", "neq"],
};

const PAGE_SIZES = [10, 25, 50, 100];

export function DataTab({ datasetId, columns }: { datasetId: string; columns: ColumnInfo[] }) {
  const [filters, setFilters] = useState<FilterSpec[]>([]);
  const [sort, setSort] = useState<SortSpec[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const [draftColumn, setDraftColumn] = useState(columns[0]?.name ?? "");
  const [draftOperator, setDraftOperator] = useState<FilterOperator>("eq");
  const [draftValue, setDraftValue] = useState("");

  const draftKind = columns.find((c) => c.name === draftColumn)?.kind ?? "text";
  const operators = OPERATORS_BY_KIND[draftKind] ?? ["eq"];
  const effectiveOperator = operators.includes(draftOperator) ? draftOperator : operators[0];

  const query = useQuery({
    queryKey: ["rows", datasetId, filters, sort, page, pageSize],
    queryFn: () => datasetsApi.query(datasetId, { filters, sort, page, pageSize }),
    placeholderData: keepPreviousData,
  });

  const exportRows = useMutation({
    mutationFn: (format: ExportFormat) => datasetsApi.exportRows(datasetId, filters, sort, format),
  });

  const totalPages = useMemo(() => {
    if (!query.data) return 1;
    return Math.max(1, Math.ceil(query.data.total / pageSize));
  }, [query.data, pageSize]);

  const addFilter = () => {
    const raw = draftKind === "boolean" && draftValue === "" ? "true" : draftValue;
    if (!draftColumn || raw.trim() === "") return;
    const value =
      effectiveOperator === "in"
        ? raw.split(",").map((part) => part.trim()).filter(Boolean)
        : draftKind === "numeric"
          ? Number(raw)
          : draftKind === "boolean"
            ? raw === "true"
            : raw.trim();
    if (draftKind === "numeric" && effectiveOperator !== "in" && Number.isNaN(value)) return;
    setFilters((current) => [
      ...current,
      { column: draftColumn, operator: effectiveOperator, value },
    ]);
    setDraftValue("");
    setPage(1);
  };

  const removeFilter = (index: number) => {
    setFilters((current) => current.filter((_, i) => i !== index));
    setPage(1);
  };

  const toggleSort = (column: string) => {
    setSort((current) => {
      const existing = current.find((s) => s.column === column);
      if (!existing) return [{ column, descending: false }];
      if (!existing.descending) return [{ column, descending: true }];
      return [];
    });
    setPage(1);
  };

  return (
    <div className="tab-stack">
      <section className="filter-bar">
        <div className="filter-draft">
          <Select
            label="Колонка"
            value={draftColumn}
            options={columns.map((c) => ({ value: c.name, label: c.name }))}
            onChange={(v) => setDraftColumn(v)}
          />
          <Select
            label="Условие"
            value={effectiveOperator}
            options={operators.map((op) => ({ value: op, label: OPERATOR_LABELS[op] }))}
            onChange={(v) => setDraftOperator(v as FilterOperator)}
          />
          {draftKind === "boolean" ? (
            <Select
              label="Значение"
              value={draftValue === "" ? "true" : draftValue}
              options={[
                { value: "true", label: "да" },
                { value: "false", label: "нет" },
              ]}
              onChange={setDraftValue}
            />
          ) : (
            <label className="field filter-value">
              <span className="field-label">
                {effectiveOperator === "in" ? "Значения через запятую" : "Значение"}
              </span>
              <input
                className="field-input"
                type={draftKind === "numeric" ? "number" : draftKind === "datetime" ? "date" : "text"}
                value={draftValue}
                placeholder={effectiveOperator === "in" ? "UAE, UK, USA" : "…"}
                onChange={(e) => setDraftValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") addFilter();
                }}
              />
            </label>
          )}
          <button className="btn" onClick={addFilter}>
            Добавить фильтр
          </button>
        </div>
        {filters.length > 0 && (
          <div className="filter-chips">
            {filters.map((filter, index) => (
              <span className="chip" key={`${filter.column}-${index}`}>
                <span className="mono">{filter.column}</span>
                <span className="chip-op">{OPERATOR_LABELS[filter.operator]}</span>
                <span className="mono">
                  {Array.isArray(filter.value) ? filter.value.join(", ") : String(filter.value)}
                </span>
                <button className="chip-remove" onClick={() => removeFilter(index)}>
                  ×
                </button>
              </span>
            ))}
            <button className="chip-clear" onClick={() => setFilters([])}>
              сбросить всё
            </button>
          </div>
        )}
      </section>

      <section className="panel">
        <header className="panel-head">
          <div>
            <h2 className="panel-title">Таблица</h2>
            <p className="panel-subtitle">
              {query.data
                ? `${formatNumber(query.data.total)} строк после фильтров · сортировка по клику на заголовок`
                : "Загрузка…"}
            </p>
          </div>
          <div className="panel-actions">
            <button
              className="btn"
              disabled={exportRows.isPending}
              onClick={() => exportRows.mutate("csv")}
            >
              Скачать CSV
            </button>
            <button
              className="btn"
              disabled={exportRows.isPending}
              onClick={() => exportRows.mutate("xlsx")}
            >
              Скачать XLSX
            </button>
          </div>
        </header>

        {query.isError ? (
          <p className="error-note">{(query.error as Error).message}</p>
        ) : (
          <DataGrid
            columns={columns.map((c) => c.name)}
            rows={query.data?.rows ?? []}
            sort={sort}
            onSort={toggleSort}
          />
        )}

        <footer className="pager">
          <label className="pager-size">
            <span>строк на странице</span>
            <select
              className="field-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
            >
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
          <div className="pager-nav">
            <button className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              ← Назад
            </button>
            <span className="pager-info">
              стр. {page} из {totalPages}
            </span>
            <button
              className="btn"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
            >
              Вперёд →
            </button>
          </div>
        </footer>
      </section>
    </div>
  );
}
