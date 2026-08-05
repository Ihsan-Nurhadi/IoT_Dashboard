import React, { useState, useEffect } from 'react';
import { FaBoxes } from 'react-icons/fa';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';
import CCTVStreamCard from './CCTVStreamCard';
import './AssetMonitoringDetail.css';

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
}

const INITIAL_TAGS: RFIDTag[] = [
  { 
    no: 1, 
    assetName: 'Antenna Sector A - 800MHz', 
    tagId: 'EPC-RFID-E280-A001', 
    frequency: '924.2 MHz', 
    rssi: -58, 
    status: 'Detected', 
    lastScanned: 'Just now',
    installationDate: '12 Maret 2024',
    serialNumber: 'SN-ANT-800-00A1',
    location: 'Sector A - Upper Level',
    vendor: 'Huawei',
    height: '38 Meter',
    photoUrl: '/contoh cctv.jpg'
  },
  { 
    no: 2, 
    assetName: 'Antenna Sector A - 1800MHz', 
    tagId: 'EPC-RFID-E280-A002', 
    frequency: '924.4 MHz', 
    rssi: -62, 
    status: 'Detected', 
    lastScanned: 'Just now',
    installationDate: '15 Maret 2024',
    serialNumber: 'SN-ANT-1800-00A2',
    location: 'Sector A - Upper Level',
    vendor: 'Kathrein',
    height: '38 Meter',
    photoUrl: '/camera_4.jpeg'
  },
  { 
    no: 3, 
    assetName: 'Antenna Sector B - 800MHz', 
    tagId: 'EPC-RFID-E280-B001', 
    frequency: '924.2 MHz', 
    rssi: -55, 
    status: 'Detected', 
    lastScanned: '1s ago',
    installationDate: '12 Juni 2024',
    serialNumber: 'SN-ANT-800-00B1',
    location: 'Sector B - Mid Level',
    vendor: 'Huawei',
    height: '32 Meter',
    photoUrl: '/antena3.png'
  },
  { 
    no: 4, 
    assetName: 'Antenna Sector B - 1800MHz', 
    tagId: 'EPC-RFID-E280-B002', 
    frequency: '924.4 MHz', 
    rssi: -60, 
    status: 'Detected', 
    lastScanned: 'Just now',
    installationDate: '18 Juni 2024',
    serialNumber: 'SN-ANT-1800-00B2',
    location: 'Sector B - Mid Level',
    vendor: 'Kathrein',
    height: '32 Meter',
    photoUrl: '/antenna 4.jpg'
  },
  { 
    no: 5, 
    assetName: 'Microwave Dish Backhaul A', 
    tagId: 'EPC-RFID-E280-M001', 
    frequency: '925.0 MHz', 
    rssi: -52, 
    status: 'Detected', 
    lastScanned: '3s ago',
    installationDate: '05 Januari 2023',
    serialNumber: 'SN-MW-BH-009',
    location: 'Dish Platform - Lower Level',
    vendor: 'Ericsson',
    height: '26 Meter',
    photoUrl: '/antenna 5.png'
  },
  { 
    no: 6, 
    assetName: 'GPS Timing Antenna', 
    tagId: 'EPC-RFID-E280-G001', 
    frequency: '923.8 MHz', 
    rssi: -67, 
    status: 'Detected', 
    lastScanned: 'Just now',
    installationDate: '20 Oktober 2022',
    serialNumber: 'SN-GPS-TIM-882',
    location: 'Shelter Roof',
    vendor: 'Trimble',
    height: '2 Meter',
    photoUrl: '/antenna 6.jpg'
  },
];

const DUMMY_CHART_DATA = [
  { date: '25 Jul', count: 5 },
  { date: '26 Jul', count: 5 },
  { date: '27 Jul', count: 5 },
  { date: '28 Jul', count: 6 },
  { date: '29 Jul', count: 6 },
  { date: '30 Jul', count: 6 },
  { date: '31 Jul', count: 6 }
];

const AssetMonitoringDetail: React.FC = () => {
  const [tags, setTags] = useState<RFIDTag[]>(INITIAL_TAGS);
  const [selectedAsset, setSelectedAsset] = useState<RFIDTag | null>(null);
  const [currentTime, setCurrentTime] = useState<string>('');

  // Set formatted dynamic timestamp
  useEffect(() => {
    const today = new Date();
    const dateStr = `${today.getMonth() + 1}/${today.getDate()}/${today.getFullYear()}`;
    setCurrentTime(`${dateStr}, 9:00:15 AM`);
  }, []);

  // Periodic simulation for dynamic live data feel (RSSI jitter)
  useEffect(() => {
    const interval = setInterval(() => {
      setTags(prevTags =>
        prevTags.map(tag => {
          const rssiChange = Math.floor(Math.random() * 5) - 2; // change by -2 to +2
          const newRssi = Math.max(-80, Math.min(-45, tag.rssi + rssiChange));
          return {
            ...tag,
            rssi: newRssi,
            lastScanned: Math.random() > 0.5 ? 'Just now' : '1s ago'
          };
        })
      );
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="asset-detail-page">
      {/* 1. Banner Header */}
      <div className="asset-info-card glass-card">
        <div className="asset-status-badge">
          <span className="status-dot-green"></span> Connected
        </div>
        <h1 className="asset-title">Antenna Asset Monitoring & Counting</h1>
        <p className="asset-subtitle">
          Real-time RFID tag scanning & CCTV surveillance for SST antenna inventory audit management.
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
                <div className="metric-value">6 / 6</div>
                <div className="metric-footer">
                  <span className="text-green">✓ 100% Accounted For</span>
                </div>
              </div>
            </div>
          <div className="card-section-title-row">
            <h3 className="card-section-title">RFID Tag Inventory Scan</h3>
            <span className="badge-green">Scanning Live</span>
          </div>
          <div className="table-responsive">
            <table className="asset-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Nama Aset Antena</th>
                  <th>ID Tag RFID (EPC)</th>
                  <th>Frekuensi</th>
                  <th>RSSI</th>
                  <th>Status</th>
                  <th>Scan Terakhir</th>
                </tr>
              </thead>
              <tbody>
                {tags.map((tag) => (
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
                    <td className={tag.rssi > -60 ? 'text-green font-bold' : 'text-yellow font-bold'}>
                      {tag.rssi} dBm
                    </td>
                    <td>
                      <span className="status-pill green-pill">{tag.status}</span>
                    </td>
                    <td className="text-muted">{tag.lastScanned}</td>
                  </tr>
                ))}
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
            {/* Camera 3 */}
            <div className="cctv-container-with-info">
              <div className="cctv-stream-box">
                <CCTVStreamCard streamId="cctv_asset_1" cameraName="Camera 3" fallbackPhotoUrl="/camera_4.jpeg" />
              </div>
              <div className="cctv-description-box">
                <div className="cctv-info-header">
                  <span className="cctv-count-badge">Antenna count</span>
                </div>
                <div className="cctv-info-body">
                  <div className="cctv-count-value">
                    {tags.filter(t => t.status === 'Detected').length} antennas
                  </div>
                  <div className="cctv-time-sub">{currentTime}</div>
                </div>
                <div className="cctv-info-footer">
                  Updated daily at 09:00 local time
                </div>
              </div>
            </div>

            {/* Camera 4 */}
            <div className="cctv-container-with-info">
              <div className="cctv-stream-box">
                <CCTVStreamCard streamId="cctv_asset_2" cameraName="Camera 4" fallbackPhotoUrl="/contoh cctv.jpg" />
              </div>
              <div className="cctv-description-box">
                <div className="cctv-info-header">
                  <span className="cctv-count-badge">Antenna count</span>
                </div>
                <div className="cctv-info-body">
                  <div className="cctv-count-value">
                    {tags.filter(t => t.status === 'Detected').length} antennas
                  </div>
                  <div className="cctv-time-sub">{currentTime}</div>
                </div>
                <div className="cctv-info-footer">
                  Updated daily at 09:00 local time
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Chart Section */}
      <div className="asset-chart-section glass-card">
        <div className="card-section-title-row">
          <h3 className="card-section-title">Tren Kuantitas Antena Terdeteksi (RFID)</h3>
          <span className="badge-green">Parameter: Tanggal</span>
        </div>
        <div className="asset-chart-container" style={{ height: '260px', width: '100%', marginTop: '16px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={DUMMY_CHART_DATA} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-green, #10b981)" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="var(--accent-green, #10b981)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="date" stroke="var(--text-muted, #94a3b8)" fontSize={10} tickLine={false} axisLine={{ stroke: 'rgba(255,255,255,0.05)' }} tickMargin={8} />
              <YAxis stroke="var(--text-muted, #94a3b8)" fontSize={10} tickLine={false} axisLine={false} domain={[0, 8]} allowDecimals={false} />
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
                  <span className="info-label">ID Tag RFID (EPC):</span>
                  <span className="info-value mono-text">{selectedAsset.tagId}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Serial Number:</span>
                  <span className="info-value font-bold">{selectedAsset.serialNumber}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Tanggal Instalasi:</span>
                  <span className="info-value">{selectedAsset.installationDate}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Vendor / Brand:</span>
                  <span className="info-value">{selectedAsset.vendor}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Ketinggian:</span>
                  <span className="info-value">{selectedAsset.height}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Lokasi Tower:</span>
                  <span className="info-value">{selectedAsset.location}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Frekuensi Deteksi:</span>
                  <span className="info-value">{selectedAsset.frequency}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">RSSI Terakhir:</span>
                  <span className="info-value font-bold" style={{ color: selectedAsset.rssi > -60 ? '#10b981' : '#f59e0b' }}>
                    {selectedAsset.rssi} dBm
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Status Aset:</span>
                  <span className="status-pill green-pill">{selectedAsset.status}</span>
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
