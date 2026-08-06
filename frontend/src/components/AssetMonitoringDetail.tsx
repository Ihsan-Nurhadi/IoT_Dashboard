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
  uuid?: string;
  namespaceId?: string;
  instanceId?: string;
  power?: string;
}

const AssetMonitoringDetail: React.FC = () => {
  const [tags, setTags] = useState<RFIDTag[]>([]);
  const [chartData, setChartData] = useState<any[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<RFIDTag | null>(null);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

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
              installationDate: '12 Maret 2024',
              serialNumber: `SN-BLE-${item.mac.replace(/:/g, '')}`,
              location: 'Sector A - Upper Level',
              vendor: 'Huawei',
              height: '38 Meter',
              photoUrl: '/contoh cctv.jpg',
              uuid: item.uuid,
              namespaceId: item.namespace_id,
              instanceId: item.instance_id,
              power: item.power
            };
          });
          setTags(mappedTags);
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
              <div className="metric-value">{detectedCount} / 1</div>
              <div className="metric-footer">
                {detectedCount === 1 ? (
                  <span className="text-green">✓ 100% Accounted For</span>
                ) : (
                  <span className="text-red">✗ 0% Detected (Missing)</span>
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
                  <th>Scan Terakhir</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center text-muted">Memuat data sensor...</td>
                  </tr>
                ) : tags.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center text-muted">Belum ada data sensor BLE diterima.</td>
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
                      <td className={
                        tag.status === 'Anomaly'
                          ? 'text-red font-bold blinking'
                          : tag.rssi > -75
                            ? 'text-green font-bold'
                            : 'text-yellow font-bold'
                      }>
                        {tag.rssi !== -100 ? `${tag.rssi} dBm` : 'N/A'}
                      </td>
                      <td>
                        <span className={`status-pill ${
                          tag.status === 'Detected' 
                            ? 'green-pill' 
                            : tag.status === 'Anomaly' 
                              ? 'anomaly-pill blinking' 
                              : 'red-pill'
                        }`}>
                          {tag.status === 'Anomaly' ? 'ANOMALY (Stolen Alert)' : tag.status}
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
                    {detectedCount} / 1 antennas
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
                    {detectedCount} / 1 antennas
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
          <h3 className="card-section-title">Tren Kuantitas Antena Terdeteksi (BLE)</h3>
          <span className="badge-green">Parameter: Tanggal</span>
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
              <YAxis stroke="var(--text-muted, #94a3b8)" fontSize={10} tickLine={false} axisLine={false} domain={[0, 1.2]} allowDecimals={false} />
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
                  <span 
                    className={`info-value font-bold ${selectedAsset.status === 'Anomaly' ? 'blinking' : ''}`}
                    style={{ 
                      color: selectedAsset.status === 'Anomaly' 
                        ? '#ef4444' 
                        : selectedAsset.rssi > -75 
                          ? '#10b981' 
                          : '#f59e0b' 
                    }}
                  >
                    {selectedAsset.rssi !== -100 ? `${selectedAsset.rssi} dBm` : 'N/A'}
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Status Aset:</span>
                  <span className={`status-pill ${
                    selectedAsset.status === 'Detected' 
                      ? 'green-pill' 
                      : selectedAsset.status === 'Anomaly' 
                        ? 'anomaly-pill blinking' 
                        : 'red-pill'
                  }`}>
                    {selectedAsset.status === 'Anomaly' ? 'ANOMALY (Stolen Alert)' : selectedAsset.status}
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
