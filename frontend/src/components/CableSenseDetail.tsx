import React, { useState, useEffect } from 'react';
import { FaHeartbeat, FaDownload, FaExclamationTriangle, FaShieldAlt } from 'react-icons/fa';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import './CableSenseDetail.css';

interface CableLog {
  id: number;
  timestamp: string;
  device_id: string;
  vibration: number;
  tension: number;
  impact: number;
  is_cut: boolean;
  temperature: number;
  device_status: string;
  signal_strength: number;
  is_connected: boolean;
}

const CableSenseDetail: React.FC = () => {
  const [latestData, setLatestData] = useState<CableLog | null>(null);
  const [historyLogs, setHistoryLogs] = useState<CableLog[]>([]);
  const [loadingLatest, setLoadingLatest] = useState<boolean>(true);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [searchDevice, setSearchDevice] = useState<string>('Cable_Sense_01');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Fetch latest telemetry reading
  useEffect(() => {
    const fetchLatest = async () => {
      try {
        const res = await fetch(`/api/cablesense/latest/?device_id=${searchDevice}`);
        if (res.ok) {
          const data = await res.json();
          setLatestData(data);
        }
      } catch (err) {
        console.error("Failed to fetch latest Cable Sense data:", err);
      } finally {
        setLoadingLatest(false);
      }
    };

    fetchLatest();
    const interval = setInterval(fetchLatest, 3000);
    return () => clearInterval(interval);
  }, [searchDevice]);

  // Fetch historical data logs for chart & table
  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const url = `/api/cablesense/history-logs/?start_date=${startDate}&end_date=${endDate}&device_id=${searchDevice}&limit=100`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setHistoryLogs(data);
      }
    } catch (err) {
      console.error("Failed to fetch history Cable Sense data:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [startDate, endDate, searchDevice]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistory();
  };

  const handleResetFilters = () => {
    setStartDate('');
    setEndDate('');
    setSearchDevice('Cable_Sense_01');
  };

  // Export logs to CSV file
  const handleExportCSV = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const url = `/api/cablesense/history-logs/?start_date=${startDate}&end_date=${endDate}&device_id=${searchDevice}&limit=1000`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('Gagal mengambil data log untuk diekspor.');
      }
      const logs: CableLog[] = await res.json();
      if (logs.length === 0) {
        alert('Tidak ada data ditemukan untuk diekspor.');
        return;
      }

      const headers = [
        'No',
        'Waktu (WIB)',
        'ID Perangkat',
        'Status',
        'Getaran (m/s²)',
        'Tegangan Tarik (%)',
        'Suhu (°C)',
        'Benturan (g)',
        'Status Pencurian',
        'Sinyal (dBm)',
        'Konektivitas'
      ];

      const rows = logs.map((l, idx) => [
        idx + 1,
        l.timestamp,
        l.device_id,
        l.device_status,
        l.vibration,
        l.tension,
        l.temperature,
        l.impact,
        l.is_cut ? '🚨 Terpotong' : 'Aman',
        l.signal_strength,
        l.is_connected ? 'Connected' : 'Disconnected'
      ]);

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(val => `"${val}"`).join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', downloadUrl);
      const fileSuffix = startDate && endDate ? `${startDate}_to_${endDate}` : 'All';
      link.setAttribute('download', `CableSense_Logs_${fileSuffix}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Terjadi kesalahan saat mengekspor laporan CSV.');
    } finally {
      setIsExporting(false);
    }
  };

  // Format historical data for Recharts (reversed so it goes chronological left-to-right)
  const chartData = [...historyLogs]
    .reverse()
    .map(log => ({
      time: log.timestamp.split(' ')[1] || log.timestamp,
      vibration: log.vibration,
      tension: log.tension,
      temperature: log.temperature
    }));

  const getStatusClass = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'normal': return 'status-normal';
      case 'warning': return 'status-warning';
      case 'critical': return 'status-critical';
      default: return 'status-offline';
    }
  };

  return (
    <div className="cablesense-detail-page">
      {/* 1. Header Card Banner */}
      <div className="cablesense-info-card glass-card">
        <div className="cablesense-status-container">
          <div className="cablesense-status-badge">
            <span className={`status-dot-pulse ${latestData?.device_status?.toLowerCase() || 'offline'}`}></span>
            CABLE SENSE &middot; {latestData?.device_status?.toUpperCase() || 'OFFLINE'}
          </div>
          {latestData?.is_connected ? (
            <div className="connection-pill online">ONLINE</div>
          ) : (
            <div className="connection-pill offline">DISCONNECTED</div>
          )}
        </div>
        
        <h1 className="cablesense-title">Cable Health & Integrity Monitoring</h1>
        <p className="cablesense-subtitle">
          Real-time structural health monitoring of BTS coaxial and optical fiber cables. Assesses mechanical tension, localized vibrations, sudden impact forces, cut alarms, and environmental thermal trends.
        </p>

        <div className="cablesense-meta-grid">
          <div className="meta-item">
            <span className="meta-label">Site Name:</span>
            <span className="meta-val">NAYAKA WS (PRR-01-004)</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Device ID:</span>
            <span className="meta-val">{searchDevice}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Sinyal Gateway:</span>
            <span className="meta-val">{latestData ? `${latestData.signal_strength} dBm` : '-'}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Data Terakhir:</span>
            <span className="meta-val">{latestData ? latestData.timestamp : '-'}</span>
          </div>
        </div>
      </div>

      {/* 2. Real-Time Telemetry Grid */}
      <div className="cablesense-telemetry-grid">
        {/* Mechanical Stress & Tension */}
        <div className="cablesense-metric-card glass-card">
          <div className="cablesense-card-top">
            <span className="cablesense-metric-icon tension">🏹</span>
            <h3 className="cablesense-metric-name">Tegangan Mekanis (Tension)</h3>
          </div>
          <div className="cablesense-metric-value-container">
            <span className="cablesense-metric-value">{latestData ? `${latestData.tension.toFixed(1)}` : '-'}</span>
            <span className="cablesense-metric-unit">%</span>
          </div>
          <div className="cablesense-progress-bar-container">
            <div 
              className="cablesense-progress-bar-fill tension" 
              style={{ width: `${latestData ? Math.min(100, latestData.tension) : 0}%` }}
            ></div>
          </div>
          <span className="cablesense-metric-desc">Tegangan fisik penarikan kabel (Aman: 90% - 105%)</span>
        </div>

        {/* Localized Vibration */}
        <div className="cablesense-metric-card glass-card">
          <div className="cablesense-card-top">
            <span className="cablesense-metric-icon vibration">〽️</span>
            <h3 className="cablesense-metric-name">Intensitas Getaran (Vibration)</h3>
          </div>
          <div className="cablesense-metric-value-container">
            <span className="cablesense-metric-value">{latestData ? `${latestData.vibration.toFixed(3)}` : '-'}</span>
            <span className="cablesense-metric-unit">m/s²</span>
          </div>
          <div className="cablesense-progress-bar-container">
            <div 
              className="cablesense-progress-bar-fill vibration" 
              style={{ width: `${latestData ? Math.min(100, (latestData.vibration / 0.8) * 100) : 0}%` }}
            ></div>
          </div>
          <span className="cablesense-metric-desc">Sensor akselerometer getaran (Aman: &lt; 0.50 m/s²)</span>
        </div>

        {/* Environmental Temperature */}
        <div className="cablesense-metric-card glass-card">
          <div className="cablesense-card-top">
            <span className="cablesense-metric-icon temperature">🌡️</span>
            <h3 className="cablesense-metric-name">Suhu Kabel & Sekitar</h3>
          </div>
          <div className="cablesense-metric-value-container">
            <span className="cablesense-metric-value">{latestData ? `${latestData.temperature.toFixed(1)}` : '-'}</span>
            <span className="cablesense-metric-unit">&deg;C</span>
          </div>
          <div className="cablesense-progress-bar-container">
            <div 
              className="cablesense-progress-bar-fill temperature" 
              style={{ width: `${latestData ? Math.min(100, (latestData.temperature / 60) * 100) : 0}%` }}
            ></div>
          </div>
          <span className="cablesense-metric-desc">Suhu kabel tembaga/optik (Maks optimal: 45.0&deg;C)</span>
        </div>

        {/* Anti-Theft Status (Security) */}
        <div className={`cablesense-metric-card glass-card cablesense-security ${latestData?.is_cut ? 'triggered' : ''}`}>
          <div className="cablesense-card-top">
            <span className="cablesense-metric-icon security"><FaShieldAlt /></span>
            <h3 className="cablesense-metric-name">Deteksi Pencurian & Integritas</h3>
          </div>
          <div className="cablesense-security-status-container">
            {latestData ? (
              latestData.is_cut ? (
                <div className="cablesense-security-alert alert-red">
                  <FaExclamationTriangle className="alert-icon animate-bounce" />
                  <span>KABEL TERPOTONG / HILANG!</span>
                </div>
              ) : (
                <div className="cablesense-security-alert alert-green">
                  <span>INTEGRITAS UTUH (AMAN)</span>
                </div>
              )
            ) : (
              <span className="cablesense-metric-value">-</span>
            )}
          </div>
          <span className="cablesense-metric-desc" style={{ marginTop: 'auto' }}>Memonitor pelepasan atau pemotongan kabel listrik / optik secara real-time.</span>
        </div>
      </div>

      {/* 3. Recharts Dynamic History Graphs */}
      <div className="cablesense-charts-section glass-card">
        <h2 className="cablesense-section-title">Tren Historis & Analisis Sensor</h2>
        <div className="cablesense-charts-grid">
          {/* Tension Chart */}
          <div className="cablesense-chart-container">
            <h4 className="cablesense-chart-title">Grafik Tegangan Kabel (Tension %)</h4>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorTension" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#eab308" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3042" />
                  <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} />
                  <YAxis domain={[80, 120]} stroke="#94a3b8" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff' }} />
                  <Area type="monotone" dataKey="tension" stroke="#eab308" fillOpacity={1} fill="url(#colorTension)" name="Tegangan (%)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Vibration Chart */}
          <div className="cablesense-chart-container">
            <h4 className="cablesense-chart-title">Grafik Tingkat Getaran (Vibration m/s²)</h4>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorVibration" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f97316" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3042" />
                  <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} />
                  <YAxis domain={[0, 'auto']} stroke="#94a3b8" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff' }} />
                  <Area type="monotone" dataKey="vibration" stroke="#f97316" fillOpacity={1} fill="url(#colorVibration)" name="Getaran (m/s²)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Temperature Chart */}
          <div className="cablesense-chart-container" style={{ gridColumn: '1 / -1' }}>
            <h4 className="cablesense-chart-title">Grafik Suhu Termal Lingkungan (&deg;C)</h4>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#f43f5e" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3042" />
                  <XAxis dataKey="time" stroke="#94a3b8" fontSize={10} />
                  <YAxis domain={[20, 45]} stroke="#94a3b8" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#fff' }} />
                  <Area type="monotone" dataKey="temperature" stroke="#f43f5e" fillOpacity={1} fill="url(#colorTemp)" name="Suhu (°C)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Logs Audit Table & Filter Section */}
      <div className="cablesense-audit-section glass-card">
        <div className="cablesense-section-header">
          <h2 className="cablesense-section-title">Audit Log Pemantauan Kabel</h2>
          <button className="cablesense-export-btn" onClick={handleExportCSV} disabled={isExporting}>
            <FaDownload /> {isExporting ? 'Mengekspor...' : 'Ekspor Laporan CSV'}
          </button>
        </div>

        {/* Filter Form */}
        <form onSubmit={handleSearchSubmit} className="cablesense-filter-form">
          <div className="cablesense-filter-group">
            <label>ID Sensor</label>
            <input 
              type="text" 
              value={searchDevice} 
              onChange={(e) => setSearchDevice(e.target.value)} 
              placeholder="e.g. Cable_Sense_01" 
            />
          </div>
          <div className="cablesense-filter-group">
            <label>Tanggal Mulai</label>
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)} 
            />
          </div>
          <div className="cablesense-filter-group">
            <label>Tanggal Selesai</label>
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)} 
            />
          </div>
          <div className="cablesense-filter-actions">
            <button type="submit" className="cablesense-search-btn">Cari</button>
            <button type="button" className="cablesense-reset-btn" onClick={handleResetFilters}>Reset</button>
          </div>
        </form>

        {/* Table logs */}
        <div className="cablesense-table-responsive">
          <table className="cablesense-audit-table">
            <thead>
              <tr>
                <th>Waktu (WIB)</th>
                <th>Device ID</th>
                <th>Status</th>
                <th>Getaran (m/s²)</th>
                <th>Tegangan Tarik</th>
                <th>Suhu</th>
                <th>Benturan (g)</th>
                <th>Integritas Kabel</th>
                <th>RSSI Gateway</th>
              </tr>
            </thead>
            <tbody>
              {loadingHistory ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    Memuat logs histori...
                  </td>
                </tr>
              ) : historyLogs.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    Tidak ada logs ditemukan dalam kriteria filter.
                  </td>
                </tr>
              ) : (
                historyLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{log.timestamp}</td>
                    <td style={{ fontFamily: 'monospace' }}>{log.device_id}</td>
                    <td>
                      <span className={`cablesense-status-pill ${getStatusClass(log.device_status)}`}>
                        {log.device_status}
                      </span>
                    </td>
                    <td>{log.vibration.toFixed(3)}</td>
                    <td>{log.tension.toFixed(1)}%</td>
                    <td>{log.temperature.toFixed(1)}&deg;C</td>
                    <td>{log.impact > 0 ? `${log.impact} g` : '0.00'}</td>
                    <td>
                      {log.is_cut ? (
                        <span style={{ color: '#ef4444', fontWeight: 'bold' }}>🚨 Terpotong</span>
                      ) : (
                        <span style={{ color: '#22c55e' }}>Aman</span>
                      )}
                    </td>
                    <td>{log.signal_strength} dBm</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CableSenseDetail;
