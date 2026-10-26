import React from 'react';
import { HelpCircle, TrendingUp, AlertTriangle, Shield, Activity, BarChart2, CheckCircle2 } from 'lucide-react';

export default function MetricsCards({ metrics, loading }) {
  if (loading || !metrics) {
    return (
      <div className="metrics-grid">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="metric-card" style={{ minHeight: '100px', opacity: 0.5 }}>
            <div className="spinner" style={{ width: '20px', height: '20px', margin: 'auto' }}></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'MAE',
      value: `${metrics.mae?.toLocaleString()} MW`,
      tag: 'Mean Absolute Error',
      tooltip: 'Average magnitude of forecast error, measuring typical deviation regardless of whether it was over or under.',
      icon: <Activity size={15} color="var(--accent-cyan)" />,
    },
    {
      title: 'RMSE',
      value: `${metrics.rmse?.toLocaleString()} MW`,
      tag: 'Root Mean Squared Error',
      tooltip: 'Penalizes large forecast misses more heavily than MAE, highlighting periods with extreme forecast errors.',
      icon: <BarChart2 size={15} color="#a78bfa" />,
    },
    {
      title: 'Bias',
      value: `${metrics.bias > 0 ? '+' : ''}${metrics.bias?.toLocaleString()} MW`,
      tag: metrics.bias > 0 ? 'Over-forecasting' : 'Under-forecasting',
      tooltip: 'Average signed error (forecast - actual). Positive means the day-ahead model systematically over-predicted wind.',
      color: metrics.bias > 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)',
      icon: <TrendingUp size={15} color="var(--accent-amber)" />,
    },
    {
      title: 'Over-Forecast %',
      value: `${metrics.over_forecast_pct}%`,
      tag: `${Math.round((metrics.over_forecast_pct / 100) * metrics.count || 1263)} / ${metrics.count || 1488} slots`,
      tooltip: 'Share of all 30-minute settlement periods where the day-ahead forecast exceeded actual wind generation.',
      color: 'var(--accent-rose)',
      icon: <AlertTriangle size={15} color="var(--accent-rose)" />,
    },
    {
      title: 'P90 Abs Error',
      value: `${metrics.p90?.toLocaleString()} MW`,
      tag: '90th percentile error',
      tooltip: '90% of all half-hour settlement periods had an absolute forecast error less than or equal to this value.',
      icon: <CheckCircle2 size={15} color="#38bdf8" />,
    },
    {
      title: 'P95 Abs Error',
      value: `${metrics.p95?.toLocaleString()} MW`,
      tag: '95th percentile error',
      tooltip: '95% of all half-hour settlement periods had an absolute forecast error less than or equal to this value.',
      icon: <CheckCircle2 size={15} color="#818cf8" />,
    },
    {
      title: '90% Safe Buffer',
      value: `${metrics.buffer_90?.toLocaleString()} MW`,
      tag: 'Shortfall reserve needed',
      tooltip: 'The reserve capacity in MW required to cover generation shortfalls (forecast > actual) in 90% of settlement periods.',
      color: 'var(--accent-cyan)',
      icon: <Shield size={15} color="var(--accent-cyan)" />,
    },
  ];

  return (
    <div className="metrics-grid">
      {cards.map((c, idx) => (
        <div key={idx} className="metric-card">
          <div className="metric-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {c.icon}
              <span className="metric-title">{c.title}</span>
            </div>
            <div className="tooltip-container">
              <HelpCircle size={14} className="tooltip-icon" />
              <div className="tooltip-box">{c.tooltip}</div>
            </div>
          </div>
          <div>
            <div className="metric-value" style={c.color ? { color: c.color } : {}}>
              {c.value}
            </div>
            <div className="metric-tag">{c.tag}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
