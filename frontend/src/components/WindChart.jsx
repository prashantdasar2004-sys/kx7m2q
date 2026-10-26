import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { Eye } from 'lucide-react';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isOverForecast = data.error > 0;
    
    return (
      <div className="recharts-custom-tooltip">
        <div className="tooltip-header">
          <span>Slot {data.slot} of 48 ({label} UK)</span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: 'var(--accent-cyan)' }}>Actual (FUELHH):</span>
          <span style={{ fontWeight: 600 }}>
            {data.actual !== null ? `${data.actual.toLocaleString()} MW` : 'N/A'}
          </span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: 'var(--accent-amber)' }}>Forecast (WINDFOR):</span>
          <span style={{ fontWeight: 600 }}>
            {data.forecast !== null ? `${data.forecast.toLocaleString()} MW` : 'N/A'}
          </span>
        </div>
        <div className="tooltip-row" style={{ marginTop: '4px', borderTop: '1px dashed rgba(255,255,255,0.1)', paddingTop: '4px' }}>
          <span>Error (Forecast - Actual):</span>
          <span style={{ fontWeight: 700, color: isOverForecast ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
            {data.error !== null ? `${data.error > 0 ? '+' : ''}${data.error.toLocaleString()} MW` : 'N/A'}
          </span>
        </div>
        {data.publishTime && (
          <div style={{ marginTop: '4px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Published: {data.publishTime} ({data.horizon_hours}h ahead)
          </div>
        )}
      </div>
    );
  }
  return null;
}

export default function WindChart({ forecastData, loading }) {
  if (loading) {
    return (
      <div className="card chart-card">
        <div className="loading-box">
          <div className="spinner"></div>
          <span>Loading day-ahead settlement slots...</span>
        </div>
      </div>
    );
  }

  if (!forecastData || !forecastData.slots || forecastData.slots.length === 0) {
    return (
      <div className="card chart-card">
        <div className="loading-box">
          <span>No settlement data available for this date.</span>
        </div>
      </div>
    );
  }

  const slots = forecastData.slots;

  // Fixed Y-axis ticks every 3000 MW from 0 up to 21000 MW
  const yTicks = [0, 3000, 6000, 9000, 12000, 15000, 18000, 21000];

  return (
    <div className="card chart-card">
      <div className="chart-header">
        <div className="chart-title-block">
          <h3>Day View: Actuals vs Day-Ahead Forecast ({forecastData.day})</h3>
          <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
            48 half-hour settlement periods across delivery day {forecastData.day}
          </span>
        </div>

        {/* Text badge showing exact publication date and time */}
        <div className="chart-publish-info" title="Forecast runs published after D-1 cutoff were discarded">
          <Eye size={14} />
          <span>{forecastData.publish_times_summary}</span>
        </div>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={slots} margin={{ top: 10, right: 30, left: 20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
            <XAxis
              dataKey="timeLabel"
              stroke="#6b7280"
              fontSize={11}
              interval={3}
              tickLine={false}
            />
            <YAxis
              ticks={yTicks}
              domain={[0, 21000]}
              tickFormatter={(v) => `${v.toLocaleString()} MW`}
              stroke="#6b7280"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={75}
            />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Actual Outturn Line */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual Wind (FUELHH)"
              stroke="#06b6d4"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, fill: '#06b6d4' }}
            />

            {/* Selected Forecast Line */}
            <Line
              type="stepAfter"
              dataKey="forecast"
              name="Day-Ahead Forecast (WINDFOR)"
              stroke="#f59e0b"
              strokeWidth={2.2}
              strokeDasharray="4 2"
              dot={false}
              activeDot={{ r: 5, fill: '#f59e0b' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-legend-custom">
        <div>
          <span className="legend-dot" style={{ backgroundColor: 'var(--accent-cyan)' }}></span>
          <span style={{ fontWeight: 600, color: '#f3f4f6' }}>Actual Wind (FUELHH)</span>
          <span style={{ color: 'var(--text-muted)', marginLeft: '4px' }}>— 30-minute metered outturn</span>
        </div>
        <div>
          <span className="legend-dot" style={{ backgroundColor: 'var(--accent-amber)' }}></span>
          <span style={{ fontWeight: 600, color: '#f3f4f6' }}>Day-Ahead Forecast (WINDFOR)</span>
          <span style={{ color: 'var(--text-muted)', marginLeft: '4px' }}>— latest run at or before the D-1 cutoff (carried forward)</span>
        </div>
      </div>
    </div>
  );
}
