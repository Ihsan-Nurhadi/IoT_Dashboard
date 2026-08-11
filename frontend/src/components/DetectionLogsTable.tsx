import React, { useState, useEffect } from 'react';
import { 
  FaCamera, 
  FaVideo, 
  FaImage, 
  FaChevronLeft, 
  FaChevronRight, 
  FaUser, 
  FaCalendarAlt,
  FaArrowRight,
  FaSpinner,
  FaSignal
} from 'react-icons/fa';
import { PiSiren } from 'react-icons/pi';
import './DetectionLogsTable.css';

interface DetectionLogItem {
  id: string;
  type: 'person' | 'motion' | 'stolen';
  type_label: string;
  camera: string;
  video_src: string;
  photo_url: string;
  video_url: string | null;
  timestamp: string;
  raw_time: string;
}

interface PaginatedResponse {
  items: DetectionLogItem[];
  total_count: number;
  total_pages: number;
  current_page: number;
}

const ITEMS_PER_PAGE = 10;

const DetectionLogsTable: React.FC = () => {
  const [category, setCategory] = useState<'all' | 'gerakan' | 'orang' | 'stolen'>('all');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [logsData, setLogsData] = useState<PaginatedResponse>({
    items: [],
    total_count: 0,
    total_pages: 1,
    current_page: 1
  });

  // Modal State
  const [previewPhotoUrl, setPreviewPhotoUrl] = useState<string | null>(null);
  const [previewPhotoTitle, setPreviewPhotoTitle] = useState<string>('');
  const [previewVideoUrl, setPreviewVideoUrl] = useState<string | null>(null);
  const [previewVideoTitle, setPreviewVideoTitle] = useState<string>('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      let url = `/api/cctv/detection-logs/?category=${category}&page=${page}&limit=${ITEMS_PER_PAGE}`;
      if (startDate) url += `&start_date=${encodeURIComponent(startDate)}`;
      if (endDate) url += `&end_date=${encodeURIComponent(endDate)}`;

      const res = await fetch(url);
      if (res.ok) {
        const data: PaginatedResponse = await res.json();
        setLogsData(data);
      }
    } catch (err) {
      console.error("Error fetching detection logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [category, page, startDate, endDate]);

  const handleCategoryChange = (newCat: 'all' | 'gerakan' | 'orang' | 'stolen') => {
    if (category !== newCat) {
      setCategory(newCat);
      setPage(1);
    }
  };

  const openCameraModal = (item: DetectionLogItem) => {
    // If companion video exists, play video, else show live stream endpoint
    if (item.video_url) {
      setPreviewVideoUrl(item.video_url);
    } else {
      setPreviewVideoUrl(`/api/cctv-stream/?src=${item.video_src}`);
    }
    setPreviewVideoTitle(`${item.camera} - Rekaman Deteksi (${item.timestamp})`);
  };

  const openPhotoModal = (item: DetectionLogItem) => {
    setPreviewPhotoUrl(item.photo_url);
    setPreviewPhotoTitle(`${item.camera} - Snapshot ${item.type_label} (${item.timestamp})`);
  };

  return (
    <div className="detection-logs-container">
      {/* 1. Date Range Filter Inputs Bar */}
      <div className="date-range-bar">
        <div className="date-picker-box">
          <FaCalendarAlt className="date-icon" />
          <input 
            type="datetime-local" 
            className="date-input"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <span className="range-arrow">→</span>
        <div className="date-picker-box">
          <FaCalendarAlt className="date-icon" />
          <input 
            type="datetime-local" 
            className="date-input"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {/* 2. Main Logs Card Container */}
      <div className="detection-card">
        {/* Card Top Title Row */}
        <div className="detection-card-header">
          <div className="header-title-left">
            <FaCamera className="section-cam-icon" />
            <h2 className="detection-title">Gerakan</h2>
          </div>
          <span className="live-pill-badge">
            <span className="live-dot"></span> Live
          </span>
        </div>

        {/* Filter Category Tabs */}
        <div className="detection-tabs-row">
          <button 
            className={`tab-btn ${category === 'all' ? 'active' : ''}`}
            onClick={() => handleCategoryChange('all')}
          >
            Semua
          </button>
          <button 
            className={`tab-btn ${category === 'gerakan' ? 'active' : ''}`}
            onClick={() => handleCategoryChange('gerakan')}
          >
            Gerakan
          </button>
          <button 
            className={`tab-btn ${category === 'orang' ? 'active' : ''}`}
            onClick={() => handleCategoryChange('orang')}
          >
            Orang
          </button>
          <button 
            className={`tab-btn ${category === 'stolen' ? 'active' : ''}`}
            onClick={() => handleCategoryChange('stolen')}
          >
            Antena
          </button>
        </div>

        {/* Data Table */}
        <div className="table-responsive">
          {loading ? (
            <div className="table-loading">
              <FaSpinner className="spinner-icon" /> Memuat data log deteksi...
            </div>
          ) : logsData.items.length === 0 ? (
            <div className="table-empty">Belum ada riwayat deteksi</div>
          ) : (
            <table className="detection-table">
              <thead>
                <tr>
                  <th>Waktu</th>
                  <th>Kamera</th>
                  <th>Tipe</th>
                  <th className="th-aksi">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {logsData.items.map((item) => (
                  <tr key={item.id}>
                    {/* Waktu */}
                    <td className="col-waktu">
                      <span className="red-dot"></span>
                      <span className="timestamp-text">{item.timestamp}</span>
                    </td>

                    {/* Kamera */}
                    <td className="col-kamera">{item.camera}</td>

                    {/* Tipe */}
                    <td className="col-tipe">
                      <span className={`type-badge ${item.type}`}>
                        {item.type === 'person' ? (
                          <>
                            <FaUser className="type-badge-icon" />
                            <span>{item.type_label}</span>
                          </>
                        ) : item.type === 'stolen' ? (
                          <>
                            <PiSiren className="type-badge-icon" style={{ color: '#ef4444' }} />
                            <span style={{ color: '#ef4444', fontWeight: 600 }}>{item.type_label}</span>
                          </>
                        ) : (
                          <>
                            <FaSignal className="type-badge-icon" />
                            <span>{item.type_label}</span>
                          </>
                        )}
                      </span>
                    </td>

                    {/* Aksi Buttons */}
                    <td className="col-aksi">
                      {item.type === 'person' && (
                        <button 
                          className="btn-action btn-camera"
                          onClick={() => openCameraModal(item)}
                          title="Buka Rekaman/Kamera"
                        >
                          <FaVideo /> Buka Kamera
                        </button>
                      )}
                      <button 
                        className="btn-action btn-photo"
                        onClick={() => openPhotoModal(item)}
                        title="Lihat Snapshot Foto"
                      >
                        <FaImage /> Lihat Foto
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination Footer */}
        <div className="detection-pagination">
          <span className="page-info">
            Page {logsData.current_page} of {logsData.total_pages || 1}
          </span>
          <div className="pagination-nav">
            <button 
              className="page-nav-btn"
              disabled={page <= 1 || loading}
              onClick={() => setPage(p => Math.max(1, p - 1))}
            >
              <FaChevronLeft />
            </button>
            <button 
              className="page-nav-btn"
              disabled={page >= logsData.total_pages || loading}
              onClick={() => setPage(p => Math.min(logsData.total_pages, p + 1))}
            >
              <FaChevronRight />
            </button>
          </div>
        </div>
      </div>

      {/* Photo Viewer Modal */}
      {previewPhotoUrl && (
        <div className="detection-modal-overlay" onClick={() => setPreviewPhotoUrl(null)}>
          <div className="detection-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setPreviewPhotoUrl(null)}>×</button>
            <h3 className="modal-title">{previewPhotoTitle}</h3>
            <img src={previewPhotoUrl} alt="Detection Snapshot" className="modal-preview-img" />
          </div>
        </div>
      )}

      {/* Video Viewer Modal */}
      {previewVideoUrl && (
        <div className="detection-modal-overlay" onClick={() => setPreviewVideoUrl(null)}>
          <div className="detection-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setPreviewVideoUrl(null)}>×</button>
            <h3 className="modal-title">{previewVideoTitle}</h3>
            {previewVideoUrl.endsWith('.mp4') ? (
              <video src={previewVideoUrl} controls autoPlay className="modal-preview-video" />
            ) : (
              <img src={previewVideoUrl} alt="Live Stream" className="modal-preview-img" />
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DetectionLogsTable;
