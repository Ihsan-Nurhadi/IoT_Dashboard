import React, { useState, useEffect } from 'react';
import { FaBoxes, FaDownload } from 'react-icons/fa';
import './RfidMonitoringDetail.css';

interface RFIDLog {
  timestamp: string;
  reader_id: string;
  tag_epc: string;
}

const RfidMonitoringDetail: React.FC = () => {
  const [liveLogs, setLiveLogs] = useState<RFIDLog[]>([]);
  const [historyLogs, setHistoryLogs] = useState<RFIDLog[]>([]);
  const [loadingLive, setLoadingLive] = useState<boolean>(true);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [searchTag, setSearchTag] = useState<string>('');

  const getTodayDateString = () => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [startDate, setStartDate] = useState<string>(getTodayDateString());
  const [endDate, setEndDate] = useState<string>(getTodayDateString());
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Fetch live RFID scans
  useEffect(() => {
    const fetchLiveScans = async () => {
      try {
        const res = await fetch('/api/rfid/latest/');
        if (res.ok) {
          const data = await res.json();
          setLiveLogs(data);
        }
      } catch (err) {
        console.error("Failed to fetch live RFID scans:", err);
      } finally {
        setLoadingLive(false);
      }
    };

    fetchLiveScans();
    const interval = setInterval(fetchLiveScans, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch history RFID scans
  const fetchHistoryScans = async () => {
    setLoadingHistory(true);
    try {
      const url = `/api/rfid/history-logs/?start_date=${startDate}&end_date=${endDate}&tag_epc=${searchTag}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setHistoryLogs(data);
      }
    } catch (err) {
      console.error("Failed to fetch history RFID scans:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Run history fetch on dates/search query change or initially
  useEffect(() => {
    fetchHistoryScans();
  }, [startDate, endDate]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchHistoryScans();
  };

  // Generate and export CSV
  const handleExportCSV = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const url = `/api/rfid/history-logs/?start_date=${startDate}&end_date=${endDate}&tag_epc=${searchTag}`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('Gagal mengambil data log RFID untuk diekspor.');
      }
      const logs = await res.json();
      if (logs.length === 0) {
        alert('Tidak ada log RFID ditemukan untuk kriteria pencarian dan rentang tanggal terpilih.');
        return;
      }

      const headers = ['No', 'Waktu (WIB)', 'ID Reader', 'EPC Tag RFID'];
      const rows = logs.map((l: RFIDLog, idx: number) => [
        idx + 1,
        l.timestamp,
        l.reader_id,
        l.tag_epc
      ]);

      const csvContent = [
        headers.join(','),
        ...rows.map((row: any[]) => row.map(val => `"${val}"`).join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', downloadUrl);
      link.setAttribute('download', `RFID_Scan_Report_${startDate}_to_${endDate}.csv`);
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

  const formatLastScanned = (timestampStr: string) => {
    try {
      const date = new Date(timestampStr);
      const diffMs = new Date().getTime() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 5) return 'Just now';
      if (diffSec < 60) return `${diffSec}s ago`;
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      return date.toLocaleString('id-ID');
    } catch (e) {
      return timestampStr;
    }
  };

  return (
    <div className="rfid-detail-page">
      {/* 1. Header Banner */}
      <div className="rfid-info-card glass-card">
        <div className="rfid-status-badge">
          <span className="status-dot-indigo animate-pulse"></span> RFID SCANNING ONLINE
        </div>
        <h1 className="rfid-title">RFID Asset Monitoring & Logging</h1>
        <p className="rfid-subtitle">
          Real-time RFID scanning, tracking, and logs audit at Tower Landing Page (opposite to BLE Sector).
        </p>
        <div className="rfid-meta-row">
          <div className="meta-item">
            <span className="meta-label">Site:</span> NAYAKA WS (PRR-01-004)
          </div>
          <div className="meta-item">
            <span className="meta-label">Default Reader:</span> Raspi_RFID_Reader_01
          </div>
        </div>
      </div>

      {/* 2. Content Split Layout */}
      <div className="rfid-content-split">
        {/* Left Column: Live scans */}
        <div className="split-column left-live glass-card">
          <div className="card-section-title-row">
            <div className="section-title-container">
              <span className="section-icon indigo-icon"><FaBoxes /></span>
              <h2>Real-Time RFID Scans</h2>
            </div>
            <span className="live-pill animate-pulse">LIVE</span>
          </div>

          <div className="table-scroll-container">
            {loadingLive ? (
              <div className="loading-spinner-container">
                <div className="spinner"></div>
                <p>Loading real-time scans...</p>
              </div>
            ) : liveLogs.length === 0 ? (
              <div className="no-data-alert">
                Tidak ada data scan yang terdeteksi saat ini. Silakan jalankan simulasi atau scan kartu.
              </div>
            ) : (
              <table className="rfid-table">
                <thead>
                  <tr>
                    <th>Waktu (WIB)</th>
                    <th>ID Reader</th>
                    <th>EPC Tag RFID</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {liveLogs.map((log, idx) => (
                    <tr key={idx} className="fade-in">
                      <td className="time-col">{formatLastScanned(log.timestamp)}</td>
                      <td><span className="reader-badge">{log.reader_id}</span></td>
                      <td className="epc-col">{log.tag_epc}</td>
                      <td><span className="status-pill active-pill">SCANNED</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Column: Historical search and CSV export */}
        <div className="split-column right-history glass-card">
          <div className="card-section-title-row">
            <div className="section-title-container">
              <h2>Historical Logs & Export</h2>
            </div>
          </div>

          <form onSubmit={handleSearchSubmit} className="history-filter-form">
            <div className="filter-grid">
              <div className="filter-item">
                <label>Tanggal Mulai</label>
                <input 
                  type="date" 
                  value={startDate} 
                  onChange={(e) => setStartDate(e.target.value)} 
                />
              </div>
              <div className="filter-item">
                <label>Tanggal Selesai</label>
                <input 
                  type="date" 
                  value={endDate} 
                  onChange={(e) => setEndDate(e.target.value)} 
                />
              </div>
              <div className="filter-item full-width">
                <label>Cari Berdasarkan EPC Tag</label>
                <input 
                  type="text" 
                  placeholder="Contoh: E2 80 68..." 
                  value={searchTag}
                  onChange={(e) => setSearchTag(e.target.value)}
                />
              </div>
            </div>
            
            <div className="form-actions">
              <button type="submit" className="action-btn search-btn">
                Tampilkan Log
              </button>
              <button 
                type="button" 
                onClick={handleExportCSV} 
                className="action-btn export-btn" 
                disabled={isExporting || historyLogs.length === 0}
              >
                <FaDownload /> {isExporting ? 'Mengekspor...' : 'Export CSV'}
              </button>
            </div>
          </form>

          <div className="table-scroll-container history-logs-container">
            {loadingHistory ? (
              <div className="loading-spinner-container">
                <div className="spinner"></div>
                <p>Mengambil data log...</p>
              </div>
            ) : historyLogs.length === 0 ? (
              <div className="no-data-alert text-muted">
                Tidak ada data log RFID ditemukan untuk filter dan rentang tanggal yang dipilih.
              </div>
            ) : (
              <table className="rfid-table history-table">
                <thead>
                  <tr>
                    <th>No</th>
                    <th>Waktu (WIB)</th>
                    <th>ID Reader</th>
                    <th>EPC Tag RFID</th>
                  </tr>
                </thead>
                <tbody>
                  {historyLogs.map((log, idx) => (
                    <tr key={idx}>
                      <td>{idx + 1}</td>
                      <td>{log.timestamp}</td>
                      <td><span className="reader-badge">{log.reader_id}</span></td>
                      <td className="epc-col">{log.tag_epc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RfidMonitoringDetail;
