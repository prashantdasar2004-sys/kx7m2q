import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { Clock } from 'lucide-react';

function CustomHourlyTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="recharts-custom-tooltip">
        <div className="tooltip-header">
          <span>Hour {data.hour_label} (January 2026 Aggregate)</span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: '#a78bfa' }}>Mean Absolute Error (MAE):</span>
          <span style={{ fontWeight: 600 }}>{data.mae?.toLocaleString()} MW</span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: data.bias > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>
            Mean Bias (Forecast - Actual):
          </span>
          <span style={{ fontWeight: 700 }}>
            {data.bias > 0 ? '+' : ''}{data.bias?.toLocaleString()} MW
          </span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: 'var(--accent-rose)' }}>Over-Forecast Share:</span>
          <span style={{ fontWeight: 600 }}>{data.over_forecast_pct}%</span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: 'var(--accent-cyan)' }}>90% Safe Reserve Buffer:</span>
          <span style={{ fontWeight: 600 }}>{data.buffer_90?.toLocaleString()} MW</span>
        </div>
      </div>
    );
  }
  return null;
}

export default function HourlyErrorChart({ hourlyData, loading, cutoff }) {
  if (loading) {
    return (
      <div className="card chart-card">
        <div className="loading-box">
          <div className="spinner"></div>
          <span>Loading diurnal error distribution...</span>
        </div>
      </div>
    );
  }

  if (!hourlyData || hourlyData.length === 0) {
    return null;
  }

  // Fixed Y-axis ticks every 3000 MW
  const yTicks = [0, 3000, 6000];

  return (
    <div className="card chart-card">
      <div className="chart-header">
        <div className="chart-title-block">
          <h3>Diurnal Error Distribution by Hour of Day</h3>
          <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
            Mean forecast error and bias across each hour (00:00 to 23:00 UK Time) for January 2026 ({cutoff} cutoff)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <Clock size={14} />
          <span>24 Hourly Trading Windows</span>
        </div>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={hourlyData} margin={{ top: 10, right: 30, left: 20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
            <XAxis
              dataKey="hour_label"
              stroke="#6b7280"
              fontSize={11}
              interval={1}
              tickLine={false}
            />
            <YAxis
              ticks={yTicks}
              domain={[0, 6000]}
              tickFormatter={(v) => `${v.toLocaleString()} MW`}
              stroke="#6b7280"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={75}
            />
            <Tooltip content={<CustomHourlyTooltip />} />
            <ReferenceLine y={0} stroke="rgba(255, 255, 255, 0.2)" />
            
            {/* MAE Bar */}
            <Bar
              dataKey="mae"
              name="Mean Absolute Error (MAE)"
              fill="#8b5cf6"
              radius={[4, 4, 0, 0]}
              maxBarSize={22}
            />

            {/* Bias Bar */}
            <Bar
              dataKey="bias"
              name="Mean Bias (Forecast - Actual)"
              fill="#f59e0b"
              radius={[4, 4, 0, 0]}
              maxBarSize={22}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-legend-custom">
        <div>
          <span className="legend-dot" style={{ backgroundColor: '#8b5cf6' }}></span>
          <span style={{ fontWeight: 600, color: '#f3f4f6' }}>MAE (MW)</span>
          <span style={{ color: 'var(--text-muted)', marginLeft: '4px' }}>— Typical error magnitude</span>
        </div>
        <div>
          <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }}></span>
          <span style={{ fontWeight: 600, color: '#f3f4f6' }}>Mean Bias (MW)</span>
          <span style={{ color: 'var(--text-muted)', marginLeft: '4px' }}>— Systematic over-forecasting (+ values)</span>
        </div>
      </div>
    </div>
  );
}
