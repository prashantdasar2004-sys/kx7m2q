import React from 'react';
import { Calendar, Clock, AlertCircle } from 'lucide-react';

export default function CutoffControls({
  selectedDate,
  onDateChange,
  selectedCutoff,
  onCutoffChange,
  allowedCutoffs = ['06:00', '08:00', '09:00'],
  dateRange = { start: '2026-01-01', end: '2026-01-31' },
}) {
  return (
    <div className="card controls-card">
      <div className="controls-group">
        {/* Date Picker */}
        <div className="control-item">
          <Calendar size={16} color="var(--accent-cyan)" />
          <label htmlFor="delivery-date-input" className="control-label">Delivery Date:</label>
          <input
            id="delivery-date-input"
            type="date"
            className="input-date"
            value={selectedDate}
            min={dateRange.start}
            max={dateRange.end}
            onChange={(e) => onDateChange(e.target.value)}
          />
        </div>

        {/* Morning D-1 Cutoff Picker */}
        <div className="control-item">
          <Clock size={16} color="var(--accent-amber)" />
          <span className="control-label">D-1 Decision Cutoff (UK Time):</span>
          <div className="cutoff-btn-group">
            {allowedCutoffs.map((cutoff) => (
              <button
                key={cutoff}
                type="button"
                className={`cutoff-btn ${selectedCutoff === cutoff ? 'active' : ''}`}
                onClick={() => onCutoffChange(cutoff)}
                title={`Only consider forecasts published before ${cutoff} on the previous day`}
              >
                {cutoff}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Domain Context Note */}
      <div className="controls-note">
        <span style={{ color: 'var(--accent-amber)', fontWeight: 600 }}>Pre-Auction Discipline: </span>
        All 48 half-hour slots evaluate only forecasts published before this D-1 cutoff. Later runs are excluded to simulate what the trader actually saw before auction gate closure (EPEX 09:20, N2EX 09:50 UK time).
      </div>
    </div>
  );
}
