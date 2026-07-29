import React, { useEffect, useState } from 'react';
import { HeroCompassCard } from './aqms/HeroCompassCard';
import { MetricCard } from './aqms/MetricCard';
import { AirQualityGrid } from './aqms/AirQualityGrid';
import { AtmosphericCanvas } from './aqms/AtmosphericCanvas';
import type { SensorReading, RangeType } from './aqms/types';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
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

  // States for Audit Report Tab
  const [startDate, setStartDate] = useState<string>(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [reportFormat, setReportFormat] = useState<string>('PDF_DAILY');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

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

  // Generate CSV Report
  const generateCSVReport = (readings: SensorReading[]) => {
    const headers = [
      'Timestamp',
      'Node ID',
      'Suhu (C)',
      'Kelembapan (%RH)',
      'Tekanan (hPa)',
      'Kecepatan Angin (m/s)',
      'Arah Angin (derajat)',
      'Curah Hujan (mm)',
      'Cahaya (lux)',
      'Radiasi (W/m2)',
      'PM2.5 (ug/m3)',
      'PM10 (ug/m3)',
      'Ion Negatif (pcs/cm3)',
      'Noise (dB)'
    ];

    const rows = readings.map(r => [
      r.timestamp ? new Date(r.timestamp).toLocaleString('id-ID') : '',
      r.node_id || 'UNKNOWN',
      r.temperature,
      r.humidity,
      r.pressure,
      r.wind_speed,
      r.wind_direction,
      r.rain || 0,
      r.light || 0,
      r.radiation || 0,
      r.pm25,
      r.pm10,
      r.negative_ion || 0,
      r.noise || 0
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(val => `"${val}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `AQMS_Compliance_Report_${startDate}_to_${endDate}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Generate PDF Report using jsPDF
  const generatePDFReport = (readings: SensorReading[]) => {
    const doc = new jsPDF();
    const isMonthly = reportFormat === 'PDF_MONTHLY';
    const reportTitle = isMonthly ? 'AUDIT BULANAN KUALITAS UDARA' : 'LAPORAN HARIAN TELEMETRI AQMS';
    
    const totalRecords = readings.length;
    const avgTempPdf = (readings.reduce((sum, r) => sum + r.temperature, 0) / totalRecords).toFixed(2);
    const avgHumPdf = (readings.reduce((sum, r) => sum + r.humidity, 0) / totalRecords).toFixed(2);
    const avgPm25Pdf = (readings.reduce((sum, r) => sum + r.pm25, 0) / totalRecords).toFixed(2);
    const avgPm10Pdf = (readings.reduce((sum, r) => sum + r.pm10, 0) / totalRecords).toFixed(2);
    
    // Page Header Banner
    doc.setFillColor(15, 23, 42); // slate-900
    doc.rect(0, 0, 210, 38, 'F');
    
    doc.setTextColor(255, 255, 255);
    doc.setFont('Helvetica', 'bold');
    doc.setFontSize(15);
    doc.text('SENTINEL AIR QUALITY MONITORING SYSTEM', 14, 16);
    
    doc.setFont('Helvetica', 'normal');
    doc.setFontSize(9.5);
    doc.setTextColor(148, 163, 184); // slate-400
    doc.text(`Tipe Dokumen: Laporan Resmi Audit Sistem`, 14, 23);
    doc.text(`Dicetak pada: ${new Date().toLocaleString('id-ID')}`, 14, 28);
    
    // Status Badge
    doc.setFillColor(34, 197, 94); // active green
    doc.rect(162, 12, 34, 6, 'F');
    doc.setFontSize(8);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('STATUS: AKTIF', 167, 16.5);

    // Document Title Section
    doc.setFontSize(11);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(30, 41, 59); // slate-800
    doc.text(reportTitle, 14, 52);
    
    doc.setDrawColor(226, 232, 240); // slate-200
    doc.line(14, 55, 196, 55);
    
    doc.setFontSize(9);
    doc.setFont('Helvetica', 'normal');
    doc.setTextColor(71, 85, 105); // slate-600
    doc.text(`Rentang Audit : ${new Date(startDate).toLocaleDateString('id-ID')} s.d ${new Date(endDate).toLocaleDateString('id-ID')}`, 14, 62);
    doc.text(`Node Sektor   : E32_WS (Sector A)`, 14, 67);
    doc.text(`Total Baris   : ${totalRecords} data telemetri`, 14, 72);
    
    // Telemetry Table Columns
    const tableColumns = [
      'Waktu',
      'Temp (C)',
      'Hum (%RH)',
      'Press (hPa)',
      'Wind (m/s)',
      'PM2.5',
      'PM10',
      'Ion Neg'
    ];
    
    const tableRows = readings.map(r => [
      r.timestamp ? new Date(r.timestamp).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' }) : '',
      r.temperature.toFixed(1),
      r.humidity.toFixed(1),
      r.pressure.toFixed(1),
      r.wind_speed.toFixed(1),
      r.pm25.toFixed(1),
      r.pm10.toFixed(1),
      (r.negative_ion || 0).toFixed(0)
    ]);
    
    autoTable(doc, {
      startY: 78,
      head: [tableColumns],
      body: tableRows,
      theme: 'striped',
      headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontSize: 8, fontStyle: 'bold' },
      bodyStyles: { fontSize: 8, textColor: [51, 65, 85] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      margin: { left: 14, right: 14 },
    });
    
    // Dynamic Summary and Signatures Placement
    let finalY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 10 : 180;
    if (finalY > 230) {
      doc.addPage();
      finalY = 20;
    }
    
    doc.setFillColor(241, 245, 249); // slate-100
    doc.rect(14, finalY, 182, 26, 'F');
    
    doc.setFontSize(9);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(30, 41, 59);
    doc.text('Rangkuman Analisis & Statistik:', 18, finalY + 6);
    
    doc.setFont('Helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(71, 85, 105);
    doc.text(`Rata-rata Suhu       : ${avgTempPdf} C`, 18, finalY + 14);
    doc.text(`Rata-rata Kelembapan : ${avgHumPdf} %RH`, 18, finalY + 20);
    doc.text(`Rata-rata PM2.5 : ${avgPm25Pdf} ug/m3`, 100, finalY + 14);
    doc.text(`Rata-rata PM10  : ${avgPm10Pdf} ug/m3`, 100, finalY + 20);
    
    const signY = finalY + 40;
    const baseSignY = signY > 270 ? 25 : signY;
    if (signY > 270) {
      doc.addPage();
    }
    
    doc.setFontSize(9);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(30, 41, 59);
    doc.text('Dibuat Oleh:', 14, baseSignY);
    doc.line(14, baseSignY + 15, 60, baseSignY + 15);
    doc.setFont('Helvetica', 'normal');
    doc.text('Sentinel System Operator', 14, baseSignY + 20);
    
    doc.setFont('Helvetica', 'bold');
    doc.text('Disetujui Oleh:', 130, baseSignY);
    doc.line(130, baseSignY + 15, 180, baseSignY + 15);
    doc.setFont('Helvetica', 'normal');
    doc.text('Supervisor K3L & Lingkungan', 130, baseSignY + 20);

    doc.save(`AQMS_${isMonthly ? 'Monthly_Audit' : 'Daily_Telemetry'}_${startDate}_to_${endDate}.pdf`);
  };

  // Main Form Submission Handler
  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isGenerating) return;
    setIsGenerating(true);

    try {
      const res = await fetch(`/api/sensor-readings/history/?start_date=${startDate}&end_date=${endDate}`);
      if (!res.ok) {
        throw new Error('Gagal mengambil data telemetri dari server.');
      }
      const data = await res.json();
      const readings: SensorReading[] = data.results || [];

      if (readings.length === 0) {
        alert('Tidak ada data sensor yang ditemukan untuk rentang tanggal yang dipilih.');
        setIsGenerating(false);
        return;
      }

      if (reportFormat === 'CSV_COMPLIANCE') {
        generateCSVReport(readings);
      } else {
        generatePDFReport(readings);
      }
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Terjadi kesalahan saat membuat laporan.');
    } finally {
      setIsGenerating(false);
    }
  };

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
              <form className="aqms-report-form" onSubmit={handleGenerateReport}>
                <div className="aqms-form-row">
                  <div className="aqms-form-group">
                    <label>Tanggal Mulai</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      required
                    />
                  </div>
                  <div className="aqms-form-group">
                    <label>Tanggal Selesai</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="aqms-form-group">
                  <label>Format Laporan</label>
                  <select
                    value={reportFormat}
                    onChange={(e) => setReportFormat(e.target.value)}
                  >
                    <option value="PDF_DAILY">Laporan Harian Telemetri (PDF)</option>
                    <option value="CSV_COMPLIANCE">Ringkasan Mingguan Kepatuhan (CSV)</option>
                    <option value="PDF_MONTHLY">Audit Bulanan Kualitas Udara (PDF)</option>
                  </select>
                </div>

                <button
                  type="submit"
                  className="aqms-submit-btn uppercase"
                  disabled={isGenerating}
                >
                  {isGenerating ? 'Generating Laporan...' : 'Generate & Download Report'}
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
