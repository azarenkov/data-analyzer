import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { axisTickStyle, chart } from "./chartTheme";
import { ChartTooltip } from "./ChartTooltip";
import { formatNumber } from "../../lib/format";
import type { TimePoint } from "../../types/dataset";

export function TimeSeriesChart({ data, valueLabel }: { data: TimePoint[]; valueLabel: string }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 8, right: 24, bottom: 4, left: 8 }}>
        <defs>
          <linearGradient id="tsFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chart.series1} stopOpacity={0.18} />
            <stop offset="100%" stopColor={chart.series1} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke={chart.grid} />
        <XAxis
          dataKey="period"
          tick={axisTickStyle}
          axisLine={{ stroke: chart.grid }}
          tickLine={false}
          minTickGap={24}
        />
        <YAxis
          tick={axisTickStyle}
          tickFormatter={(v: number) => formatNumber(v, 0)}
          axisLine={false}
          tickLine={false}
          width={70}
        />
        <Tooltip
          cursor={{ stroke: chart.axisInk, strokeDasharray: "3 3" }}
          content={<ChartTooltip valueLabel={valueLabel} />}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={chart.series1}
          strokeWidth={2}
          fill="url(#tsFill)"
          activeDot={{ r: 4, fill: chart.series1, stroke: chart.surface, strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
