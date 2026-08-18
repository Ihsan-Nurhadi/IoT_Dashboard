import React, { useState, useEffect } from 'react';
import { FaBoxes, FaDownload } from 'react-icons/fa';
import './RfidMonitoringDetail.css';
import CCTVStreamCard from './CCTVStreamCard';

interface RFIDLog {
  timestamp: string;
  reader_id: string;
  tag_epc: string;
}

interface RFIDTagGroup {
  tag_epc: string;
  last_scan: string;
  last_reader: string;
}

const RfidMonitoringDetail: React.FC = () => {
  const [liveLogs, setLiveLogs] = useState<RFIDLog[]>([]);
  const [historyLogs, setHistoryLogs] = useState<RFIDTagGroup[]>([]);
  const [loadingLive, setLoadingLive] = useState<boolean>(true);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [searchTag, setSearchTag] = useState<string>('');

  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [isExporting, setIsExporting] = useState<boolean>(false);

  interface CCTVCamera {
    camera_id: string;
    camera_name: string;
    is_active: boolean;
    detection_zones: { name: string; points: [number, number][] }[];
  }
  const [cameras, setCameras] = useState<CCTVCamera[]>([]);
  const [verifiedCounts, setVerifiedCounts] = useState<{ [camId: string]: { total: number; present: number } }>({});

  // Fetch CCTV Cameras dynamically
  useEffect(() => {
    const fetchCams = async () => {
      try {
        const res = await fetch('/api/cameras/');
        if (res.ok) {
          const data = await res.json();
          setCameras(data.filter((c: CCTVCamera) => c.is_active));
        }
      } catch (err) {
        console.error("Failed to fetch cameras:", err);
      }
    };
    fetchCams();
    const interval = setInterval(fetchCams, 10000);
    return () => clearInterval(interval);
  }, []);

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

  const handleResetFilters = async () => {
    setStartDate('');
    setEndDate('');
    setSearchTag('');
    setLoadingHistory(true);
    try {
      const url = `/api/rfid/history-logs/?start_date=&end_date=&tag_epc=`;
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

  // Generate and export CSV
  const handleExportCSV = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const url = `/api/rfid/history-logs/?start_date=${startDate}&end_date=${endDate}&tag_epc=${searchTag}&raw_scans=true`;
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error('Gagal mengambil data log scan RFID untuk diekspor.');
      }
      const logs = await res.json();
      if (logs.length === 0) {
        alert('Tidak ada data scan RFID ditemukan untuk kriteria pencarian dan rentang tanggal terpilih.');
        return;
      }

      const headers = ['No', 'Waktu (WIB)', 'ID Reader', 'EPC Tag RFID'];
      const rows = logs.map((l: any, idx: number) => [
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
      const fileSuffix = startDate && endDate ? `${startDate}_to_${endDate}` : 'All';
      link.setAttribute('download', `RFID_Tags_Report_${fileSuffix}.csv`);
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
    if (!timestampStr) return '-';
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
              <h2>Daftar RFID Tags Terdeteksi & Export</h2>
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
                Cari / Filter
              </button>
              <button 
                type="button" 
                onClick={handleResetFilters} 
                className="action-btn reset-btn"
              >
                Reset Filter
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
                Tidak ada data RFID tag terdeteksi dengan filter yang dipilih.
              </div>
            ) : (
              <table className="rfid-table history-table">
                <thead>
                  <tr>
                    <th>No</th>
                    <th>EPC Tag RFID</th>
                    <th>Terakhir Terdeteksi</th>
                    <th>Reader Terakhir</th>
                  </tr>
                </thead>
                <tbody>
                  {historyLogs.map((log, idx) => (
                    <tr key={idx}>
                      <td>{idx + 1}</td>
                      <td className="epc-col">{log.tag_epc}</td>
                      <td>{formatLastScanned(log.last_scan)}</td>
                      <td><span className="reader-badge">{log.last_reader}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Column 3: CCTV feeds */}
        <div className="split-column right-cctv glass-card">
          <div className="card-section-title-row">
            <div className="section-title-container">
              <h2>RFID CCTV Monitoring</h2>
            </div>
            <span className="live-pill animate-pulse" style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', borderColor: 'rgba(59, 130, 246, 0.3)', color: '#3b82f6' }}>LIVE FEED</span>
          </div>
          <div className="rfid-cctv-column">
            {cameras.length === 0 ? (
              <div className="cctv-placeholder" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                <p>Belum ada kamera CCTV aktif terpasang</p>
              </div>
            ) : (
              cameras.map((cam) => {
                return (
                  <div className="cctv-container-with-info" key={cam.camera_id}>
                    <div className="cctv-stream-box">
                      <CCTVStreamCard 
                        streamId={cam.camera_id} 
                        cameraName={cam.camera_name} 
                        fallbackPhotoUrl="/contoh cctv.jpg" 
                        onVerifyResult={(result) => {
                          setVerifiedCounts(prev => ({
                            ...prev,
                            [cam.camera_id]: {
                              total: result.total,
                              present: result.present
                            }
                          }));
                        }}
                      />
                    </div>
                    <div className="cctv-description-box">
                      <div className="cctv-info-header">
                        <span className="cctv-count-badge">Aset Terdeteksi AI</span>
                      </div>
                      <div className="cctv-info-body">
                        {(() => {
                          const verified = verifiedCounts[cam.camera_id];
                          if (verified) {
                            const diff = verified.total - verified.present;
                            return (
                              <div className="cctv-count-info">
                                <div className="count-stat">
                                  <span className="count-number">{verified.present}</span>
                                  <span className="count-label">Hadir</span>
                                </div>
                                <div className="count-stat">
                                  <span className={`count-number ${diff > 0 ? 'text-red font-bold' : ''}`}>{diff}</span>
                                  <span className="count-label">Hilang</span>
                                </div>
                              </div>
                            );
                          }
                          return <div className="mono-text">Analyzing stream...</div>;
                        })()}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RfidMonitoringDetail;
