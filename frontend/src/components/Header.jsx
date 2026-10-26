import React from 'react';
import { Wind, Database } from 'lucide-react';

export default function Header() {
  return (
    <header className="header-wrapper">
      <div>
        <div className="header-title-row">
          <div className="header-badge">
            <Wind size={14} />
            <span>UK Energy Utility</span>
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>|</span>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Day-Ahead Wind Decisions (January 2026)
          </span>
        </div>
        <h1 className="header-title" style={{ marginTop: '6px' }}>
          Wind Generation: Forecast vs Actuals
        </h1>
        <p className="header-subtitle">
          Benchmarking Elexon WINDFOR day-ahead forecasts against actual outturn without lookahead bias.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
        <div className="status-badge">
          <div className="status-dot"></div>
          <span>Data: Elexon BMRS, Jan 2026</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <Database size={13} />
          <span>FUELHH (WIND) + WINDFOR</span>
        </div>
      </div>
    </header>
  );
}
