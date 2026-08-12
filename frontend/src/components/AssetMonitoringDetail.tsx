import React, { useState, useEffect } from 'react';
import { FaBoxes } from 'react-icons/fa';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import CCTVStreamCard from './CCTVStreamCard';
import './AssetMonitoringDetail.css';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

interface RFIDTag {
  no: number;
  assetName: string;
  tagId: string;
  frequency: string;
  rssi: number;
  status: 'Detected' | 'Missing';
  lastScanned: string;
  installationDate: string;
  serialNumber: string;
  location: string;
  vendor: string;
  height: string;
  photoUrl: string;
  uuid?: string;
  namespaceId?: string;
  instanceId?: string;
  power?: string;
  theftAlert?: string;
}

const AssetMonitoringDetail: React.FC = () => {
  const [tags, setTags] = useState<RFIDTag[]>([]);
  const [chartData, setChartData] = useState<any[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<RFIDTag | null>(null);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [activeMac, setActiveMac] = useState<string>('');

  interface CCTVCamera {
    camera_id: string;
    camera_name: string;
    is_active: boolean;
    detection_zones: { name: string; points: [number, number][] }[];
  }
  const [cameras, setCameras] = useState<CCTVCamera[]>([]);
  const [verifiedCounts, setVerifiedCounts] = useState<{ [camId: string]: { total: number; present: number } }>({});

  // Date picker and PDF export states
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
  const [exportFormat, setExportFormat] = useState<string>('PDF');

  // Set formatted dynamic timestamp
  useEffect(() => {
    const today = new Date();
    const dateStr = `${today.getMonth() + 1}/${today.getDate()}/${today.getFullYear()}`;
    setCurrentTime(`${dateStr}, 9:00:15 AM`);
  }, []);

  // Fetch real-time BLE scan from Django backend MQTT client
  useEffect(() => {
    const fetchLatestScans = async () => {
      try {
        const res = await fetch('/api/ble/latest/');
        if (res.ok) {
          const data = await res.json();
          const mappedTags: RFIDTag[] = data.map((item: any, idx: number) => {
            return {
              no: idx + 1,
              assetName: item.name || 'BTSID TII',
              tagId: item.mac,
              frequency: '2.4 GHz (BLE)',
              rssi: item.rssi,
              status: item.status,
              lastScanned: item.timestamp ? formatLastScanned(item.timestamp) : 'Never',
              installationDate: item.installation_date || 'Never',
              serialNumber: `SN-BLE-${item.mac.replace(/:/g, '')}`,
              location: item.location || 'Unknown',
              vendor: item.vendor || 'Unknown',
              height: item.height || 'Unknown',
              photoUrl: item.image ? item.image : '/contoh cctv.jpg',
              uuid: item.uuid,
              namespaceId: item.namespace_id,
              instanceId: item.instance_id,
              power: item.power,
              theftAlert: item.theft_alert || 'Normal'
            };
          });
          setTags(mappedTags);
          if (mappedTags.length > 0) {
            setActiveMac(prev => prev || mappedTags[0].tagId);
          }
        }
      } catch (err) {
        console.error("Failed to fetch BLE scans:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLatestScans();
    const interval = setInterval(fetchLatestScans, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Recharts history chart data
  useEffect(() => {
    const fetchChartData = async () => {
      try {
        const res = await fetch('/api/ble/history/');
        if (res.ok) {
          const data = await res.json();
          setChartData(data);
        }
      } catch (err) {
        console.error("Failed to fetch BLE history:", err);
      }
    };
    fetchChartData();
    const interval = setInterval(fetchChartData, 5000);
    return () => clearInterval(interval);
  }, []);

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

  const formatLastScanned = (timestampStr: string) => {
    try {
      const date = new Date(timestampStr);
      const diffMs = new Date().getTime() - date.getTime();
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 5) return 'Just now';
      if (diffSec < 60) return `${diffSec}s ago`;
      const diffMin = Math.floor(diffSec / 60);
      if (diffMin < 60) return `${diffMin}m ago`;
      return date.toLocaleString();
    } catch (e) {
      return timestampStr;
    }
  };

  const generatePDFReport = (logs: any[]) => {
    const doc = new jsPDF();
    const totalRecords = logs.length;
    
    const totalDetected = logs.filter(l => l.status === 'Detected').length;
    const totalSuspicious = logs.filter(l => l.theft_alert === 'Suspicious').length;
    const suspiciousPercentage = totalRecords > 0 ? ((totalSuspicious / totalRecords) * 100).toFixed(1) : '0.0';

    doc.setFillColor(17,25,45); 
    doc.rect(0, 0, 210, 38, 'F');
    
    doc.setTextColor(255, 255, 255);
    doc.setFont('Helvetica', 'bold');
    doc.setFontSize(14);
    doc.text('TOWER SENTINEL - ASSET SECURITY SYSTEM', 14, 16);
    
    doc.setFont('Helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(148, 163, 184); 
    doc.text('Dokumen: Laporan Log Audit Keamanan Antena (BLE)', 14, 23);
    doc.text(`Tanggal Cetak: ${new Date().toLocaleString('id-ID')}`, 14, 28);
    
    doc.setFillColor(34, 197, 94); 
    doc.rect(162, 12, 34, 6, 'F');
    doc.setFontSize(8);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('STATUS: AKTIF', 167, 16.2);

    doc.setFontSize(11);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(30, 41, 59); 
    doc.text('LAPORAN LOG MONITORING BEACON BLE', 14, 52);
    
    doc.setDrawColor(226, 232, 240); 
    doc.line(14, 55, 196, 55);
    
    doc.setFontSize(9);
    doc.setFont('Helvetica', 'normal');
    doc.setTextColor(71, 85, 105); 
    const activeDevice = tags.find(t => t.tagId === activeMac) || tags[0];
    const activeName = activeDevice ? activeDevice.assetName : 'BTSID TII';
    const activeMacAddress = activeDevice ? activeDevice.tagId : '7C:D9:F4:03:32:47';
    const activeLocation = activeDevice ? activeDevice.location : 'Sector A - Upper Level';

    doc.text(`Periode Laporan : ${new Date(startDate).toLocaleDateString('id-ID')} s.d ${new Date(endDate).toLocaleDateString('id-ID')}`, 14, 62);
    doc.text(`Lokasi Site     : NAYAKA WS (PRR-01-004) - ${activeLocation}`, 14, 67);
    doc.text(`Target Beacon   : ${activeName} (${activeMacAddress})`, 14, 72);
    doc.text(`Total Baris     : ${totalRecords} data scan`, 14, 77);
    
    const tableColumns = [
      'No',
      'Waktu (WIB)',
      'ID Tag BLE (MAC)',
      'RSSI',
      'Status',
      'Kondisi Keamanan',
      'UUID Eddystone'
    ];
    
    const tableRows = logs.map((l: any, index: number) => [
      index + 1,
      l.timestamp,
      activeMacAddress,
      `${l.rssi} dBm`,
      l.status,
      l.theft_alert === 'Suspicious' ? '- CURIGA' : '- AMAN',
      l.uuid
    ]);
    
    autoTable(doc, {
      startY: 83,
      head: [tableColumns],
      body: tableRows,
      theme: 'striped',
      headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontSize: 8, fontStyle: 'bold' },
      bodyStyles: { fontSize: 8, textColor: [51, 65, 85] },
      alternateRowStyles: { fillColor: [248, 250, 252] },
      margin: { left: 14, right: 14 },
    });
    
    let finalY = (doc as any).lastAutoTable ? (doc as any).lastAutoTable.finalY + 10 : 180;
    if (finalY > 230) {
      doc.addPage();
      finalY = 20;
    }
    
    doc.setFillColor(241, 245, 249); 
    doc.rect(14, finalY, 182, 26, 'F');
    
    doc.setFontSize(9);
    doc.setFont('Helvetica', 'bold');
    doc.setTextColor(30, 41, 59);
    doc.text('Rangkuman Analisis & Keamanan:', 18, finalY + 6);
    
    doc.setFont('Helvetica', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(71, 85, 105);
    doc.text(`Total Deteksi Terbaca : ${totalDetected} kali`, 18, finalY + 14);
    doc.text(`Total Indikasi Curiga : ${totalSuspicious} kali (${suspiciousPercentage}%)`, 18, finalY + 20);
    
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
    doc.text('Tower Sentinel Operator', 14, baseSignY + 20);
    
    doc.save(`BLE_Security_Report_${startDate}_to_${endDate}.pdf`);
  };

  const generateCSVReport = (logs: any[]) => {
    const headers = [
      'No',
      'Waktu (WIB)',
      'ID Tag BLE (MAC)',
      'RSSI (dBm)',
      'Status',
      'Kondisi Keamanan',
      'UUID Eddystone',
      'Namespace ID',
      'Instance ID'
    ];

    const activeDevice = tags.find(t => t.tagId === activeMac) || tags[0];
    const activeMacAddress = activeDevice ? activeDevice.tagId : '7C:D9:F4:03:32:47';

    const rows = logs.map((l: any, index: number) => [
      index + 1,
      l.timestamp,
      activeMacAddress,
      l.rssi,
      l.status,
      l.theft_alert === 'Suspicious' ? '🚨 CURIGA' : '✅ AMAN',
      l.uuid,
      l.namespace_id || '',
      l.instance_id || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(val => `"${val}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `BLE_Security_Report_${startDate}_to_${endDate}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportPDF = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isExporting) return;
    setIsExporting(true);
    
    try {
      const res = await fetch(`/api/ble/history-logs/?start_date=${startDate}&end_date=${endDate}&mac=${activeMac}`);
      if (!res.ok) {
        throw new Error('Gagal mengambil data log BLE dari server.');
      }
      const data = await res.json();
      if (data.length === 0) {
        alert('Tidak ada data log BLE ditemukan untuk rentang tanggal yang dipilih.');
        setIsExporting(false);
        return;
      }
      
      if (exportFormat === 'CSV') {
        generateCSVReport(data);
      } else {
        generatePDFReport(data);
      }
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Terjadi kesalahan saat memproses laporan.');
    } finally {
      setIsExporting(false);
    }
  };

  const detectedCount = tags.filter(t => t.status === 'Detected').length;

  return (
    <div className="asset-detail-page">
      {/* 1. Banner Header */}
      <div className="asset-info-card glass-card">
        <div className="asset-status-badge">
          <span className={detectedCount > 0 ? "status-dot-green" : "status-dot-red"}></span> {detectedCount > 0 ? "Connected" : "Disconnected"}
        </div>
        <h1 className="asset-title">Antenna Asset Monitoring & Counting</h1>
        <p className="asset-subtitle">
          Real-time BLE beacon scanning & CCTV surveillance for SST antenna inventory audit management.
        </p>
        <div className="asset-meta-row">
          <div className="meta-item">
            <span className="meta-label">Site:</span> NAYAKA WS (PRR-01-004)
          </div>
        </div>
      </div>

      {/* 3. Split Layout: Left Table, Right CCTV */}
      <div className="asset-content-split">
        {/* RFID Inventory Table */}
        <div className="split-column left-table glass-card">
          {/* Grid Dashboard Metrics */}
          <div className="asset-metrics-grid">
            <div className="metric-card glass-card">
              <div className="metric-header">
                <span className="metric-icon green-icon"><FaBoxes /></span>
                <span className="metric-label">Antenna Inventory Count</span>
              </div>
              <div className="metric-value">{detectedCount} / {tags.length || 1}</div>
              <div className="metric-footer">
                {detectedCount === tags.length ? (
                  <span className="text-green">✓ 100% Accounted For</span>
                ) : (
                  <span className="text-red">
                    ✗ {tags.length - detectedCount} Missing ({Math.round((detectedCount / (tags.length || 1)) * 100)}% Detected)
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="card-section-title-row">
            <h3 className="card-section-title">BLE Beacon Inventory Scan</h3>
            <span className="badge-green">Scanning Live</span>
          </div>
          <div className="table-responsive">
            <table className="asset-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Nama Aset Antena</th>
                  <th>ID Tag BLE (MAC)</th>
                  <th>Frekuensi</th>
                  <th>RSSI</th>
                  <th>Status</th>
                  <th>Keamanan</th>
                  <th>Scan Terakhir</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center text-muted">Memuat data sensor...</td>
                  </tr>
                ) : tags.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center text-muted">Belum ada data sensor BLE diterima.</td>
                  </tr>
                ) : (
                  tags.map((tag) => (
                    <tr key={tag.no}>
                      <td>{tag.no}</td>
                      <td 
                        className="font-bold asset-clickable-name"
                        onClick={() => setSelectedAsset(tag)}
                        title="Klik untuk detail aset"
                      >
                        {tag.assetName}
                      </td>
                      <td className="mono-text">{tag.tagId}</td>
                      <td>{tag.frequency}</td>
                      <td className={tag.rssi > -75 ? 'text-green font-bold' : 'text-yellow font-bold'}>
                        {tag.rssi !== -100 ? `${tag.rssi} dBm` : 'N/A'}
                      </td>
                      <td>
                        <span className={`status-pill ${tag.status === 'Detected' ? 'green-pill' : 'red-pill'}`}>
                          {tag.status}
                        </span>
                      </td>
                      <td>
                        <span className={`status-pill ${tag.theftAlert === 'Normal' ? 'green-pill' : tag.theftAlert === 'Suspicious' ? 'red-pill' : 'yellow-pill'}`}>
                          {tag.theftAlert === 'Normal' ? '✅ Aman' : tag.theftAlert === 'Suspicious' ? '🚨 Alert' : '⚠️ No Signal'}
                        </span>
                      </td>
                      <td className="text-muted">{tag.lastScanned}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* CCTV feeds */}
        <div className="split-column right-cctv glass-card">
          <div className="card-section-title-row">
            <h3 className="card-section-title">Antenna CCTV Monitoring</h3>
            <span className="badge-blue">Antenna Stream</span>
          </div>
          <div className="asset-cctv-column">
            {cameras.length === 0 ? (
              <div className="cctv-placeholder" style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>
                <p>Belum ada kamera CCTV aktif terpasang</p>
              </div>
            ) : (
              cameras.map((cam) => {
                const antennaCount = cam.detection_zones?.length || 0;
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
                        <span className="cctv-count-badge">Antenna count</span>
                      </div>
                      <div className="cctv-info-body">
                        {(() => {
                          const verified = verifiedCounts[cam.camera_id];
                          if (verified) {
                            const isStolen = verified.present < verified.total;
                            return (
                              <div className="cctv-count-value" style={{ color: isStolen ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>
                                {verified.present} / {verified.total} antennas {isStolen ? '🚨 ALERT' : '✅'}
                              </div>
                            );
                          }
                          return (
                            <div className="cctv-count-value">
                              {antennaCount} / {antennaCount} antennas
                            </div>
                          );
                        })()}
                        <div className="cctv-time-sub">{currentTime}</div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 4. Chart Section */}
      <div className="asset-chart-section glass-card">
        <div className="card-section-title-row">
          <h3 className="card-section-title">Tren Kuantitas Antena Terdeteksi (BLE)</h3>
          <span className="badge-green">Parameter: Tanggal</span>
        </div>
        
        <div className="chart-filter-row">
          <form className="chart-filter-form" onSubmit={handleExportPDF}>
            <div className="filter-inputs">
              <div className="filter-field">
                <label className="filter-label">Pilih Antena:</label>
                <select
                  value={activeMac}
                  onChange={(e) => setActiveMac(e.target.value)}
                  className="filter-input-select"
                  style={{ color: '#fff', background: 'rgba(15, 23, 42, 0.45)', border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  {tags.map(t => (
                    <option key={t.tagId} value={t.tagId} style={{ background: '#0f172a' }}>
                      {t.assetName} ({t.tagId})
                    </option>
                  ))}
                  {tags.length === 0 && (
                    <option value="">Tidak ada antena aktif</option>
                  )}
                </select>
              </div>
              <div className="filter-field">
                <label className="filter-label">Mulai Tanggal:</label>
                <input 
                  type="date" 
                  value={startDate} 
                  onChange={(e) => setStartDate(e.target.value)} 
                  className="filter-input-date"
                  required 
                />
              </div>
              <div className="filter-field">
                <label className="filter-label">Sampai Tanggal:</label>
                <input 
                  type="date" 
                  value={endDate} 
                  onChange={(e) => setEndDate(e.target.value)} 
                  className="filter-input-date"
                  required 
                />
              </div>
              <div className="filter-field">
                <label className="filter-label">Format:</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value)}
                  className="filter-input-select"
                >
                  <option value="PDF">PDF Document</option>
                  <option value="CSV">CSV Spreadsheet</option>
                </select>
              </div>
            </div>
            <button 
              type="submit" 
              className="btn-export-pdf"
              disabled={isExporting}
            >
              {isExporting ? 'Mengekspor...' : exportFormat === 'PDF' ? '📄 Ekspor Log ke PDF' : '📊 Ekspor Log ke CSV'}
            </button>
          </form>
        </div>
        <div className="asset-chart-container" style={{ height: '260px', width: '100%', marginTop: '16px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-green, #10b981)" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="var(--accent-green, #10b981)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="date" stroke="var(--text-muted, #94a3b8)" fontSize={10} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickMargin={8} />
              <YAxis stroke="var(--text-muted, #94a3b8)" fontSize={10} tickLine={false} axisLine={false} domain={[0, Math.max(tags.length, 1)]} allowDecimals={false} />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '8px',
                  fontSize: '0.75rem',
                  color: '#f1f5f9',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.5)'
                }}
              />
              <Area 
                type="monotone" 
                dataKey="count" 
                name="Antena Aktif" 
                stroke="var(--accent-green, #10b981)" 
                strokeWidth={2.5} 
                fillOpacity={1} 
                fill="url(#colorCount)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 5. Detail Modal Popup */}
      {selectedAsset && (
        <div className="asset-modal-overlay" onClick={() => setSelectedAsset(null)}>
          <div className="asset-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="asset-modal-close-btn" onClick={() => setSelectedAsset(null)}>&times;</button>
            <h3 className="asset-modal-title">Detail Aset Antena</h3>
            
            <div className="asset-modal-body">
              {/* Left Side: Photo */}
              <div className="asset-modal-image-wrapper">
                <img src={selectedAsset.photoUrl} alt={selectedAsset.assetName} className="asset-modal-image" />
              </div>
              
              {/* Right Side: Metadata Details */}
              <div className="asset-modal-info">
                <div className="info-row">
                  <span className="info-label">Nama Aset:</span>
                  <span className="info-value font-bold">{selectedAsset.assetName}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">ID Tag BLE (MAC):</span>
                  <span className="info-value mono-text">{selectedAsset.tagId}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">UUID Eddystone:</span>
                  <span className="info-value mono-text text-yellow">{selectedAsset.uuid || 'N/A'}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Namespace ID:</span>
                  <span className="info-value mono-text">{selectedAsset.namespaceId || 'N/A'}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Instance ID:</span>
                  <span className="info-value mono-text">{selectedAsset.instanceId || 'N/A'}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">TX Power (RSSI@0m):</span>
                  <span className="info-value">{selectedAsset.power ? `${selectedAsset.power} dBm` : 'N/A'}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">RSSI Terakhir:</span>
                  <span className="info-value font-bold" style={{ color: selectedAsset.rssi > -75 ? '#10b981' : '#f59e0b' }}>
                    {selectedAsset.rssi !== -100 ? `${selectedAsset.rssi} dBm` : 'N/A'}
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Status Aset:</span>
                  <span className={`status-pill ${selectedAsset.status === 'Detected' ? 'green-pill' : 'red-pill'}`}>
                    {selectedAsset.status}
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Keamanan Antena:</span>
                  <span className={`status-pill ${selectedAsset.theftAlert === 'Normal' ? 'green-pill' : selectedAsset.theftAlert === 'Suspicious' ? 'red-pill' : 'yellow-pill'}`}>
                    {selectedAsset.theftAlert === 'Normal' ? '✅ Aman' : selectedAsset.theftAlert === 'Suspicious' ? '🚨 Alert Stolen' : '⚠️ No Signal'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AssetMonitoringDetail;
