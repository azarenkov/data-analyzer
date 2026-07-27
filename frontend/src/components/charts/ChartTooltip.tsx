import { formatNumber } from "../../lib/format";

interface ChartTooltipProps {
  active?: boolean;
  label?: string | number;
  payload?: { value?: number | string }[];
  valueLabel: string;
}

export function ChartTooltip({ active, label, payload, valueLabel }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const value = payload[0]?.value;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{String(label)}</div>
      <div className="chart-tooltip-value">
        <span className="chart-tooltip-swatch" />
        {valueLabel}: <b>{typeof value === "number" ? formatNumber(value) : String(value)}</b>
      </div>
    </div>
  );
}
