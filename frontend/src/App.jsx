import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import CutoffControls from './components/CutoffControls';
import MetricsCards from './components/MetricsCards';
import WindChart from './components/WindChart';
import HourlyErrorChart from './components/HourlyErrorChart';
import { fetchConfig, fetchForecast, fetchMetrics, fetchHourlyMetrics } from './services/api';
import { AlertCircle, RefreshCw, Info } from 'lucide-react';

export default function App() {
  const [config, setConfig] = useState({
    allowed_cutoffs: ['06:00', '08:00', '09:00'],
    default_cutoff: '09:00',
    date_range: { start: '2026-01-01', end: '2026-01-31' },
  });

  const [selectedDate, setSelectedDate] = useState('2026-01-15');
  const [selectedCutoff, setSelectedCutoff] = useState('09:00');

  const [forecastData, setForecastData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [hourlyMetrics, setHourlyMetrics] = useState([]);

  const [loadingDay, setLoadingDay] = useState(false);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [error, setError] = useState(null);

  // 1. Load initial configuration, guaranteeing default 09:00 cutoff on load
  useEffect(() => {
    async function init() {
      try {
        const cfg = await fetchConfig();
        setConfig(cfg);
        setSelectedCutoff(cfg.default_cutoff || '09:00');
      } catch (err) {
        console.warn('Config fetch error, using default settings:', err);
        setSelectedCutoff('09:00');
      }
    }
    init();
  }, []);

  // 2. Load Day Forecast
  const loadDayData = useCallback(async (day, cutoff) => {
    setLoadingDay(true);
    setError(null);
    try {
      const data = await fetchForecast(day, cutoff);
      setForecastData(data);
    } catch (err) {
      console.error('Forecast fetch failed:', err);
      setError(err.message || 'Failed to load day forecast data.');
    } finally {
      setLoadingDay(false);
    }
  }, []);

  // 3. Load Monthly and Hourly Metrics
  const loadMetricsData = useCallback(async (cutoff) => {
    setLoadingMetrics(true);
    try {
      const [summaryRes, hourlyRes] = await Promise.all([
        fetchMetrics(cutoff),
        fetchHourlyMetrics(cutoff),
      ]);
      setMetrics(summaryRes);
      setHourlyMetrics(hourlyRes.hours || []);
    } catch (err) {
      console.error('Metrics fetch failed:', err);
      setError((prev) => prev || err.message || 'Failed to load summary metrics.');
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  // Trigger data loading when date or cutoff changes
  useEffect(() => {
    loadDayData(selectedDate, selectedCutoff);
  }, [selectedDate, selectedCutoff, loadDayData]);

  useEffect(() => {
    loadMetricsData(selectedCutoff);
  }, [selectedCutoff, loadMetricsData]);

  const handleRetry = () => {
    loadDayData(selectedDate, selectedCutoff);
    loadMetricsData(selectedCutoff);
  };

  return (
    <div className="container">
      {/* Header */}
      <Header />

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={18} color="var(--accent-rose)" />
            <span>{error}</span>
          </div>
          <button type="button" className="btn-retry" onClick={handleRetry}>
            <RefreshCw size={13} style={{ marginRight: '4px' }} />
            Retry
          </button>
        </div>
      )}

      {/* Controls: Date Picker + Morning Cutoff */}
      <CutoffControls
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        selectedCutoff={selectedCutoff}
        onCutoffChange={setSelectedCutoff}
        allowedCutoffs={config.allowed_cutoffs}
        dateRange={config.date_range}
      />

      {/* Metric Cards Section */}
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
          January 2026 Forecast Accuracy and Risk (D-1 {selectedCutoff} cutoff)
        </h2>
        <MetricsCards metrics={metrics} loading={loadingMetrics} />
        
        {/* One-line interpretation note */}
        <div style={{
          marginTop: '10px',
          padding: '10px 14px',
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.825rem',
          color: '#fbbf24',
          lineHeight: '1.4'
        }}>
          <Info size={15} style={{ flexShrink: 0 }} />
          <span>Positive bias means the forecast was higher than actual wind, so plan for less wind than forecast.</span>
        </div>
      </div>

      {/* Day View Chart (Line Chart of Actuals vs Forecast) */}
      <WindChart forecastData={forecastData} loading={loadingDay} />

      {/* Diurnal Error Chart (Bar Chart by Hour of Day) */}
      <HourlyErrorChart hourlyData={hourlyMetrics} loading={loadingMetrics} cutoff={selectedCutoff} />

      {/* Footer */}
      <footer className="footer">
        <div>
          Data sources: Elexon BMRS <code>FUELHH</code> (WIND actuals) &amp; <code>WINDFOR</code> (forecasts).
        </div>
        <div>
          GB Day-Ahead Market Decision Support &bull; Built with FastAPI &amp; React
        </div>
      </footer>
    </div>
  );
}
