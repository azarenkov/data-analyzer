import { StatTile } from "../ui/StatTile";
import { Panel } from "../ui/Panel";
import { DataGrid } from "./DataGrid";
import { KIND_LABELS, formatNumber } from "../../lib/format";
import type { ColumnInfo, Row } from "../../types/dataset";

export function OverviewTab({ columns, preview }: { columns: ColumnInfo[]; preview: Row[] }) {
  const numeric = columns.filter((c) => c.kind === "numeric").length;
  const categorical = columns.filter((c) => c.kind === "categorical").length;
  const dates = columns.filter((c) => c.kind === "datetime").length;
  const missing = columns.reduce((acc, c) => acc + c.missing, 0);

  return (
    <div className="tab-stack">
      <div className="stat-row">
        <StatTile label="числовых колонок" value={String(numeric)} />
        <StatTile label="категориальных" value={String(categorical)} />
        <StatTile label="колонок с датами" value={String(dates)} />
        <StatTile
          label="пропущенных значений"
          value={formatNumber(missing)}
          hint={missing === 0 ? "данные полные" : undefined}
        />
      </div>

      <Panel title="Колонки" subtitle="Типы данных, пропуски и мощность каждой колонки">
        <div className="table-scroll">
          <table className="data-table columns-table">
            <thead>
              <tr>
                <th>Колонка</th>
                <th>Класс</th>
                <th>Тип</th>
                <th className="num">Пропуски</th>
                <th className="num">Уникальных</th>
              </tr>
            </thead>
            <tbody>
              {columns.map((column) => (
                <tr key={column.name}>
                  <td className="mono">{column.name}</td>
                  <td>
                    <span className={`kind-badge kind-${column.kind}`}>
                      {KIND_LABELS[column.kind] ?? column.kind}
                    </span>
                  </td>
                  <td className="mono muted">{column.dtype}</td>
                  <td className="num">{column.missing > 0 ? formatNumber(column.missing) : "—"}</td>
                  <td className="num">{formatNumber(column.unique)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Первые строки" subtitle="Предпросмотр десяти первых записей файла">
        <DataGrid columns={columns.map((c) => c.name)} rows={preview} />
      </Panel>
    </div>
  );
}
