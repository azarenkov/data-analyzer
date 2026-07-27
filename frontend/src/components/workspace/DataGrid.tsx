import { formatCell } from "../../lib/format";
import type { Row, SortSpec } from "../../types/dataset";

interface DataGridProps {
  columns: string[];
  rows: Row[];
  sort?: SortSpec[];
  onSort?: (column: string) => void;
}

export function DataGrid({ columns, rows, sort, onSort }: DataGridProps) {
  const sortFor = (column: string) => sort?.find((s) => s.column === column);

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => {
              const active = sortFor(column);
              return (
                <th
                  key={column}
                  className={onSort ? "sortable" : undefined}
                  onClick={onSort ? () => onSort(column) : undefined}
                >
                  <span>{column}</span>
                  {active && <span className="sort-mark">{active.descending ? "↓" : "↑"}</span>}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="empty-cell" colSpan={columns.length}>
                Нет строк, подходящих под фильтры
              </td>
            </tr>
          ) : (
            rows.map((row, index) => (
              <tr key={index}>
                {columns.map((column) => {
                  const value = row[column];
                  return (
                    <td key={column} className={typeof value === "number" ? "num" : undefined}>
                      {formatCell(value ?? null)}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
