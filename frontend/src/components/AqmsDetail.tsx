import React, { useEffect, useState } from 'react';
import { HeroCompassCard } from './aqms/HeroCompassCard';
import { MetricCard } from './aqms/MetricCard';
import { AirQualityGrid } from './aqms/AirQualityGrid';
import { AtmosphericCanvas } from './aqms/AtmosphericCanvas';
import type { SensorReading, RangeType } from './aqms/types';
import './AqmsDetail.css';

const AqmsDetail: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'analytics' | 'reports'>('dashboard');
  const [latestReading, setLatestReading] = useState<SensorReading>({
    node_id: 'E32_WS (Sector A)',
    temperature: 32.04,
    humidity: 45.66,
    pressure: 100.67,
    wind_speed: 0.89,
    wind_direction: 324.0,
    rain: 27.40,
    light: 5817.0,
    radiation: 45.0,
    pm25: 1.0,
    pm10: 2.0,
    negative_ion: 138.0,
    noise: 0.0,
    timestamp: new Date().toISOString(),
  });

  const [range, setRange] = useState<RangeType>('day');
  const [historyData, setHistoryData] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch latest readings for dashboard
  useEffect(() => {
    const fetchLatest = async () => {
      try {
        const res = await fetch('/api/sensor-readings/latest/');
        if (res.ok) {
          const data = await res.json();
          if (data) setLatestReading(data);
        }
      } catch (err) {
        console.error('Error fetching latest AQMS readings:', err);
      }
    };

    fetchLatest();
    const interval = setInterval(fetchLatest, 3000);
    return () => clearInterval(interval);
  }, []);

  // Fetch history for analytics
  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/sensor-readings/history/?range=${range}`);
        if (res.ok) {
          const data = await res.json();
          setHistoryData(data.results || []);
        }
      } catch (err) {
        console.error('Error fetching AQMS history:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [range, activeTab]);

  // Calculations for Analytics Summary
  const avgTemp = historyData.length
    ? (historyData.reduce((acc, curr) => acc + curr.temperature, 0) / historyData.length).toFixed(2)
    : latestReading.temperature.toFixed(2);

  const avgHum = historyData.length
    ? (historyData.reduce((acc, curr) => acc + curr.humidity, 0) / historyData.length).toFixed(2)
    : latestReading.humidity.toFixed(2);

  const avgWind = historyData.length
    ? (historyData.reduce((acc, curr) => acc + curr.wind_speed, 0) / historyData.length).toFixed(2)
    : latestReading.wind_speed.toFixed(2);

  return (
    <div className="dashboard-container">
      {/* Top Header section aligned with NMS & Verticality detail pages */}
      <div className="aqms-header-section">
        <div>
          <h1 className="aqms-main-title">Air Quality Monitoring System (AQMS)</h1>
          <p className="aqms-subtitle-text">
            PRR-01-004 &middot; E32_WS &middot; Pemantauan Kualitas Udara, Suhu, dan Parameter Meteorologi Real-time
          </p>
        </div>

        {/* Tab Controls */}
        <div className="aqms-tab-controls">
          <button
            className={`aqms-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={`aqms-tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            📈 Tren Analisis
          </button>
          <button
            className={`aqms-tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
            onClick={() => setActiveTab('reports')}
          >
            📋 Laporan Audit
          </button>
        </div>
      </div>

      <hr className="aqms-divider" />

      {/* Tab Contents */}
      {activeTab === 'dashboard' && (
        <div className="aqms-tab-content fade-in">
          {/* Hero Compass Card */}
          <HeroCompassCard
            windSpeed={latestReading.wind_speed}
            windHeading={latestReading.wind_direction}
          />

          {/* Meteorological Grid */}
          <div className="aqms-section-title-wrap">
            <h3 className="aqms-section-subtitle uppercase">🌤️ KONDISI METEOROLOGI</h3>
          </div>
          <div className="aqms-meteorological-grid">
            <MetricCard
              title="Suhu Udara"
              value={latestReading.temperature.toFixed(2)}
              unit="°C"
              icon="🌡️"
              colorClass="tertiary"
              badgeText="Optimal"
              history={historyData.map(h => h.temperature).slice(-10)}
            />
            <MetricCard
              title="Kelembapan Relatif"
              value={latestReading.humidity.toFixed(2)}
              unit="%RH"
              icon="💧"
              colorClass="primary"
              history={historyData.map(h => h.humidity).slice(-10)}
            />
            <MetricCard
              title="Tekanan Barometrik"
              value={latestReading.pressure.toFixed(2)}
              unit="kPa"
              icon="🧭"
              colorClass="secondary"
              history={historyData.map(h => h.pressure).slice(-10)}
            />
            <MetricCard
              title="Curah Hujan"
              value={latestReading.rain.toFixed(2)}
              unit="mm"
              icon="🌧️"
              colorClass="primary"
              history={historyData.map(h => h.rain).slice(-10)}
            />
            <MetricCard
              title="Intensitas Cahaya"
              value={Math.round(latestReading.light)}
              unit="lux"
              icon="☀️"
              colorClass="secondary"
              history={historyData.map(h => h.light).slice(-10)}
            />
            <MetricCard
              title="Radiasi Matahari"
              value={Math.round(latestReading.radiation)}
              unit="W/m²"
              icon="🌅"
              colorClass="tertiary"
              history={historyData.map(h => h.radiation).slice(-10)}
            />
          </div>

          {/* Air Quality Grid */}
          <AirQualityGrid reading={latestReading} />

          {/* Atmospheric Flow Simulation */}
          <AtmosphericCanvas
            windSpeed={latestReading.wind_speed}
            windHeading={latestReading.wind_direction}
          />
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="aqms-tab-content fade-in">
          {/* Analytics Header & Range Selector */}
          <div className="aqms-analytics-toolbar">
            <div>
              <h2 className="aqms-section-title">Tren Historis & Parameter</h2>
              <p className="aqms-subtitle-text">Analisis fluktuasi parameter meteorologi dan kualitas udara</p>
            </div>

            <div className="aqms-range-buttons">
              {(['day', 'week', 'month'] as RangeType[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={`aqms-range-btn ${range === r ? 'active' : ''}`}
                >
                  {r === 'day' ? '24 Jam' : r === 'week' ? '7 Hari' : '30 Hari'}
                </button>
              ))}
            </div>
          </div>

          {/* Summary Cards */}
          <div className="aqms-summary-grid">
            <div className="aqms-summary-card glass-card">
              <p className="aqms-summary-title">Rata-rata Suhu</p>
              <p className="aqms-summary-value text-tertiary">{avgTemp} °C</p>
              <p className="aqms-summary-sub">Rentang waktu: {range === 'day' ? '24 Jam' : range === 'week' ? '7 Hari' : '30 Hari'}</p>
            </div>

            <div className="aqms-summary-card glass-card">
              <p className="aqms-summary-title">Rata-rata Kelembapan</p>
              <p className="aqms-summary-value text-primary">{avgHum} %RH</p>
              <p className="aqms-summary-sub">Rentang waktu: {range === 'day' ? '24 Jam' : range === 'week' ? '7 Hari' : '30 Hari'}</p>
            </div>

            <div className="aqms-summary-card glass-card">
              <p className="aqms-summary-title">Rata-rata Angin</p>
              <p className="aqms-summary-value text-secondary">{avgWind} m/s</p>
              <p className="aqms-summary-sub">Rentang waktu: {range === 'day' ? '24 Jam' : range === 'week' ? '7 Hari' : '30 Hari'}</p>
            </div>
          </div>

          {/* History Parameter Table */}
          <div className="aqms-table-container glass-card">
            <div className="aqms-table-header">
              <h3 className="aqms-table-title">Log Parameter Telemetri</h3>
              <span className="aqms-table-count">Total Record: {historyData.length}</span>
            </div>

            <div className="aqms-table-scroll">
              <table className="aqms-data-table">
                <thead>
                  <tr>
                    <th>Waktu</th>
                    <th>Suhu (°C)</th>
                    <th>Kelembapan (%RH)</th>
                    <th>Tekanan (kPa)</th>
                    <th>Angin (m/s)</th>
                    <th>PM2.5 (ug/m³)</th>
                    <th>PM10 (ug/m³)</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="aqms-table-loading">Memuat data...</td>
                    </tr>
                  ) : historyData.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="aqms-table-empty">Belum ada data historis.</td>
                    </tr>
                  ) : (
                    historyData.map((row, idx) => (
                      <tr key={idx}>
                        <td className="font-mono">
                          {new Date(row.timestamp).toLocaleString('id-ID', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="font-mono">{row.temperature.toFixed(2)}</td>
                        <td className="font-mono">{row.humidity.toFixed(2)}</td>
                        <td className="font-mono">{row.pressure.toFixed(2)}</td>
                        <td className="font-mono">{row.wind_speed.toFixed(2)}</td>
                        <td className="font-mono">{row.pm25}</td>
                        <td className="font-mono">{row.pm10}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'reports' && (
        <div className="aqms-tab-content fade-in">
          <div className="aqms-reports-grid">
            {/* Custom Export Card */}
            <div className="aqms-report-export-box glass-card">
              <h3 className="aqms-report-title">Ekspor Laporan Kustom</h3>
              <form className="aqms-report-form" onSubmit={(e) => e.preventDefault()}>
                <div className="aqms-form-row">
                  <div className="aqms-form-group">
                    <label>Tanggal Mulai</label>
                    <input type="date" defaultValue="2026-07-01" />
                  </div>
                  <div className="aqms-form-group">
                    <label>Tanggal Selesai</label>
                    <input type="date" defaultValue="2026-07-24" />
                  </div>
                </div>

                <div className="aqms-form-group">
                  <label>Format Laporan</label>
                  <select>
                    <option>Laporan Harian Telemetri (PDF)</option>
                    <option>Ringkasan Mingguan Kepatuhan (CSV)</option>
                    <option>Audit Bulanan Kualitas Udara (PDF)</option>
                  </select>
                </div>

                <button className="aqms-submit-btn uppercase">
                  Generate & Download Report
                </button>
              </form>
            </div>

            {/* System Status summary */}
            <div className="aqms-system-summary glass-card">
              <h3 className="aqms-report-title">Ringkasan Sistem</h3>
              <div className="aqms-summary-items">
                <div className="aqms-summary-item-row">
                  <span className="label">Node Utama:</span>
                  <span className="value text-primary">E32_WS (Sector A)</span>
                </div>
                <div className="aqms-summary-item-row">
                  <span className="label">Rata-rata Suhu:</span>
                  <span className="value text-tertiary">{avgTemp} °C</span>
                </div>
                <div className="aqms-summary-item-row">
                  <span className="label">Rata-rata Kelembapan:</span>
                  <span className="value text-tertiary">{avgHum} %RH</span>
                </div>
                <div className="aqms-summary-item-row">
                  <span className="label">Status Telemetri:</span>
                  <span className="value text-tertiary" style={{ fontWeight: 'bold' }}>Aktif & Normal</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AqmsDetail;
