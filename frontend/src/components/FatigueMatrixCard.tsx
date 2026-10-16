import React, { useState, useEffect } from 'react';
import { FileSpreadsheet, Download, RefreshCw, Clock, Layers } from 'lucide-react';
import './FatigueMatrixCard.css';

interface FatigueReportStatus {
  exists: boolean;
  file_name: string;
  download_url: string;
  file_size?: string;
  last_modified?: string;
  sheets?: string[];
  active_sheet?: string;
  total_sites?: number;
  recorded_intervals?: string[];
  latest_interval?: string;
  message?: string;
}

const FatigueMatrixCard: React.FC = () => {
  const [reportStatus, setReportStatus] = useState<FatigueReportStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [syncing, setSyncing] = useState<boolean>(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/verticality/fatigue-report/status/');
      if (res.ok) {
        const data: FatigueReportStatus = await res.json();
        setReportStatus(data);
      }
    } catch (err) {
      console.error('Error fetching fatigue report status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleDownload = () => {
    window.open('/api/verticality/fatigue-report/download/', '_blank');
  };

  const handleManualSync = async () => {
    try {
      setSyncing(true);
      const res = await fetch('/api/verticality/fatigue-report/trigger/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (res.ok) {
        await fetchStatus();
      }
    } catch (err) {
      console.error('Error triggering fatigue manual sync:', err);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="fatigue-matrix-card-wrapper">
      {/* Top Banner Card */}
      <div className="fatigue-matrix-header-card">
        <div className="fatigue-matrix-header-left">
          <div className="fatigue-matrix-icon-box">
            <FileSpreadsheet className="fatigue-matrix-icon" />
          </div>
          <div>
            <div className="fatigue-matrix-title-row">
              <h3>Monitoring Status Fatigue Tower (30-Minute Matrix Excel)</h3>
              <span className="badge-interval-30m">
                ● Interval 30 Menit
              </span>
            </div>
            <p className="fatigue-matrix-subtitle">
              Pencatatan status berkala seluruh 21 site sensor fatigue &amp; verticality ke dalam matriks horizontal Excel setiap 30 menit (00:00, 00:30, 01:00, ...) beserta status ONLINE dan OFFLINE.
            </p>
          </div>
        </div>

        <div className="fatigue-matrix-actions">
          <button
            type="button"
            className="btn-fatigue-download"
            onClick={handleDownload}
            disabled={loading}
          >
            <Download size={16} />
            Download File Excel (.xlsx)
          </button>
          <button
            type="button"
            className="btn-fatigue-sync"
            onClick={handleManualSync}
            disabled={syncing}
          >
            <RefreshCw size={15} className={syncing ? 'spinner-rotate' : ''} />
            {syncing ? 'Sedang Menarik Data...' : 'Tarik Data Sekarang (Manual Sync)'}
          </button>
        </div>
      </div>

      {/* Metric Info Row */}
      <div className="fatigue-matrix-stats-grid">
        <div className="fatigue-stat-card">
          <span className="fatigue-stat-label">NAMA FILE LAPORAN</span>
          <span className="fatigue-stat-val code">
            {reportStatus?.file_name || 'monitoring_fatigue_30min.xlsx'}
          </span>
          <span className="fatigue-stat-sub">Format Excel Matriks Horizontal (.xlsx)</span>
        </div>

        <div className="fatigue-stat-card">
          <span className="fatigue-stat-label">TERAKHIR DIUPDATE</span>
          <span className="fatigue-stat-val green">
            {reportStatus?.last_modified || '-'}
          </span>
          <span className="fatigue-stat-sub">Sinkronisasi otomatis per 30 menit</span>
        </div>

        <div className="fatigue-stat-card">
          <span className="fatigue-stat-label">TOTAL SITE TERPANTAU</span>
          <span className="fatigue-stat-val cyan">
            {reportStatus?.total_sites ? `${reportStatus.total_sites} Site` : '21 Site'}
          </span>
          <span className="fatigue-stat-sub">Seluruh Site Sensor Verticality</span>
        </div>

        <div className="fatigue-stat-card">
          <span className="fatigue-stat-label">INTERVAL TERAKHIR</span>
          <span className="fatigue-stat-val yellow">
            {reportStatus?.latest_interval ? `${reportStatus.latest_interval} WIB` : '-'}
          </span>
          <span className="fatigue-stat-sub">Sheet: {reportStatus?.active_sheet || 'Hari Ini'}</span>
        </div>
      </div>

      {/* Recorded Intervals Container */}
      <div className="fatigue-intervals-card">
        <div className="fatigue-intervals-header">
          <div className="fatigue-intervals-title">
            <h4>Interval Pemantauan Tercatat Hari Ini ({reportStatus?.active_sheet || 'Hari Ini'})</h4>
            <p>Kolom interval 30 menit yang telah dicatat ke dalam matriks sheet Excel hari ini.</p>
          </div>
          <button
            type="button"
            className="btn-refresh-mini"
            onClick={fetchStatus}
            disabled={loading}
          >
            <RefreshCw size={13} className={loading ? 'spinner-rotate' : ''} />
            Refresh Status
          </button>
        </div>

        <div className="fatigue-intervals-pills">
          {reportStatus?.recorded_intervals && reportStatus.recorded_intervals.length > 0 ? (
            reportStatus.recorded_intervals.map((slot, idx) => (
              <div key={idx} className="interval-pill">
                <span className="interval-dot"></span>
                <span>{slot} WIB</span>
              </div>
            ))
          ) : (
            <p className="fatigue-empty-msg">
              {reportStatus?.exists
                ? 'Belum ada kolom interval 30 menit tercatat untuk hari ini.'
                : 'File excel belum di-generate. Klik tombol "Tarik Data Sekarang (Manual Sync)" di atas untuk membuat file awal.'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default FatigueMatrixCard;
