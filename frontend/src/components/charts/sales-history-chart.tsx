/**
 * Sales History Chart component.
 *
 * Displays historical sales data in a chart format.
 * This is a visualization component only - all data is provided by props.
 */

import type { ReactNode } from "react";

import type { DailyKPI } from "@/lib/api/analytics";

export interface SalesHistoryChartProps {
  kpis: DailyKPI[];
}

export default function SalesHistoryChart({
  kpis,
}: SalesHistoryChartProps): ReactNode {
  // Sort KPIs by date for proper display
  const sortedKpis = [...kpis].sort((a, b) =>
    a.kpi_date.localeCompare(b.kpi_date)
  );

  // Calculate chart dimensions and scales
  const maxSales = Math.max(...sortedKpis.map((kpi) => kpi.total_sales || 0), 1);
  const chartHeight = 300;
  const chartWidth = 800;
  const padding = 40;
  const barWidth = Math.max(5, (chartWidth - 2 * padding) / sortedKpis.length - 2);

  // Generate bars
  const bars = sortedKpis.map((kpi, index) => {
    const x = padding + index * ((chartWidth - 2 * padding) / sortedKpis.length);
    const barHeight = ((kpi.total_sales || 0) / maxSales) * (chartHeight - 2 * padding);
    const y = chartHeight - padding - barHeight;

    // Color based on whether it's a promo day or holiday
    const isSpecial = kpi.is_promo_day || kpi.has_state_holiday || kpi.has_school_holiday;
    const barColor = isSpecial ? "#ef4444" : "#3b82f6";

    return (
      <g key={kpi.kpi_id}>
        <rect
          x={x}
          y={y}
          width={barWidth}
          height={barHeight}
          fill={barColor}
          rx={2}
        />
        {/* Add tooltip on hover */}
        <title>
          {kpi.kpi_date}: ${(kpi.total_sales || 0).toLocaleString()} sales,{" "}
          {kpi.total_customers || 0} customers
          {kpi.is_promo_day && " - Promo"}
          {(kpi.has_state_holiday || kpi.has_school_holiday) && " - Holiday"}
        </title>
      </g>
    );
  });

  // Generate y-axis labels
  const yTicks = 5;
  const yAxisLabels = Array.from({ length: yTicks }, (_, i) => {
    const value = Math.round((maxSales / yTicks) * i);
    const y = chartHeight - padding - ((maxSales / yTicks) * i / maxSales) * (chartHeight - 2 * padding);
    return (
      <g key={i}>
        <line
          x1={padding}
          y1={y}
          x2={chartWidth - padding}
          y2={y}
          stroke="#e5e7eb"
          strokeDasharray="4"
        />
        <text x={padding - 10} y={y + 4} textAnchor="end" fontSize={12} fill="#6b7280">
          {value}
        </text>
      </g>
    );
  });

  // Show date labels for first, middle, and last dates only
  const xLabelIndices = sortedKpis.length <= 10
    ? sortedKpis.map((_, i) => i)
    : [0, Math.floor(sortedKpis.length / 2), sortedKpis.length - 1];

  const xAxisLabels = xLabelIndices.map((index) => {
    const kpi = sortedKpis[index];
    const x = padding + index * ((chartWidth - 2 * padding) / sortedKpis.length) + barWidth / 2;
    return (
      <text
        key={index}
        x={x}
        y={chartHeight - padding + 20}
        textAnchor="middle"
        fontSize={11}
        fill="#6b7280"
        transform={`rotate(-45, ${x}, ${chartHeight - padding + 20})`}
      >
        {kpi.kpi_date}
      </text>
    );
  });

  return (
    <div className="sales-history-chart">
      <h3>Sales History</h3>
      <div className="chart-container">
        <svg width={chartWidth} height={chartHeight} viewBox={`0 0 ${chartWidth} ${chartHeight}`}>
          {/* Y-axis */}
          <line
            x1={padding}
            y1={padding}
            x2={padding}
            y2={chartHeight - padding}
            stroke="#9ca3af"
            strokeWidth={2}
          />

          {/* X-axis */}
          <line
            x1={padding}
            y1={chartHeight - padding}
            x2={chartWidth - padding}
            y2={chartHeight - padding}
            stroke="#9ca3af"
            strokeWidth={2}
          />

          {/* Grid lines and labels */}
          {yAxisLabels}

          {/* Data bars */}
          {bars}

          {/* X-axis labels */}
          {xAxisLabels}

          {/* Legend */}
          <g transform={`translate(${chartWidth - 150}, 20)`}>
            <rect width={12} height={12} fill="#3b82f6" rx={2} />
            <text x={20} y={11} fontSize={12} fill="#374151">
              Normal Day
            </text>
            <rect y={20} width={12} height={12} fill="#ef4444" rx={2} />
            <text x={20} y={31} fontSize={12} fill="#374151">
              Promo/Holiday
            </text>
          </g>
        </svg>
      </div>

      {sortedKpis.length > 7 && (
        <p className="chart-note">
          * Only showing first, middle, and last date labels for clarity
        </p>
      )}
    </div>
  );
}
