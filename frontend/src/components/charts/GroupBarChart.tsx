import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { axisTickStyle, chart } from "./chartTheme";
import { ChartTooltip } from "./ChartTooltip";
import { formatNumber } from "../../lib/format";
import type { GroupRow } from "../../types/dataset";

export function GroupBarChart({ data: raw, valueLabel }: { data: GroupRow[]; valueLabel: string }) {
  const data = raw.map((row) => ({ ...row, plotValue: Number(row.value) }));
  const height = Math.max(220, Math.min(560, data.length * 34 + 40));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
        <CartesianGrid horizontal={false} stroke={chart.grid} />
        <XAxis
          type="number"
          tick={axisTickStyle}
          tickFormatter={(v: number) => formatNumber(v, 0)}
          axisLine={{ stroke: chart.grid }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={120}
          tick={axisTickStyle}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(11,11,11,0.04)" }}
          content={<ChartTooltip valueLabel={valueLabel} />}
        />
        <Bar
          dataKey="plotValue"
          fill={chart.series1}
          radius={[0, 4, 4, 0]}
          barSize={18}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
