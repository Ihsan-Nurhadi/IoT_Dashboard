import React, { useState, useEffect } from 'react';
import { 
  FaImage, 
  FaVideo, 
  FaChevronLeft, 
  FaChevronRight, 
  FaPlay, 
  FaSpinner,
  FaMapMarkerAlt,
  FaBuilding,
  FaCamera,
  FaDoorClosed,
  FaDoorOpen,
  FaBolt,
  FaMinusCircle
} from 'react-icons/fa';
import './SiteDetail.css';

interface MediaItem {
  name: string;
  url: string;
  camera: string;
  timestamp: string;
  size: string;
}

interface PaginatedResponse {
  items: MediaItem[];
  total_count: number;
  total_pages: number;
  current_page: number;
}

interface DoorLogItem {
  id: number;
  status: 'OPEN' | 'CLOSE';
  timestamp: string;
}

interface DoorLogResponse {
  current_status: 'OPEN' | 'CLOSE';
  logs: DoorLogItem[];
  total_count: number;
  total_pages: number;
  current_page: number;
}

const ITEMS_PER_PAGE = 10; // 2 rows of 5 items

const SiteDetail: React.FC = () => {
  // Door Logs State
  const [doorLogsData, setDoorLogsData] = useState<DoorLogResponse>({
    current_status: 'CLOSE',
    logs: [],
    total_count: 0,
    total_pages: 1,
    current_page: 1,
  });
  const [doorLogsPage, setDoorLogsPage] = useState(1);
  const [doorLogsLoading, setDoorLogsLoading] = useState(false);

  // Photos State
  const [photosData, setPhotosData] = useState<PaginatedResponse>({
    items: [],
    total_count: 0,
    total_pages: 0,
    current_page: 1,
  });
  const [photosPage, setPhotosPage] = useState(1);
  const [photosLoading, setPhotosLoading] = useState(false);

  // Videos State
  const [videosData, setVideosData] = useState<PaginatedResponse>({
    items: [],
    total_count: 0,
    total_pages: 0,
    current_page: 1,
  });
  const [videosPage, setVideosPage] = useState(1);
  const [videosLoading, setVideosLoading] = useState(false);

  // Video Modal State
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(null);
  const [activeVideoTitle, setActiveVideoTitle] = useState("");

  // Photo Modal State (for fullscreen viewing)
  const [activePhotoUrl, setActivePhotoUrl] = useState<string | null>(null);
  const [activePhotoTitle, setActivePhotoTitle] = useState("");

  // Fetch Door Logs
  useEffect(() => {
    const fetchDoorLogs = async () => {
      setDoorLogsLoading(true);
      try {
        const res = await fetch(`/api/door-logs/?page=${doorLogsPage}&limit=5`);
        if (res.ok) {
          const data = await res.json();
          setDoorLogsData(data);
        }
      } catch (err) {
        console.error("Error fetching door logs:", err);
      } finally {
        setDoorLogsLoading(false);
      }
    };
    fetchDoorLogs();
  }, [doorLogsPage]);

  // Fetch photos
  useEffect(() => {
    const fetchPhotos = async () => {
      setPhotosLoading(true);
      try {
        const res = await fetch(`/api/cctv/history/?type=photos&page=${photosPage}&limit=${ITEMS_PER_PAGE}`);
        if (res.ok) {
          const data = await res.json();
          setPhotosData(data);
        }
      } catch (err) {
        console.error("Error fetching photos history:", err);
      } finally {
        setPhotosLoading(false);
      }
    };
    fetchPhotos();
  }, [photosPage]);

  // Fetch videos
  useEffect(() => {
    const fetchVideos = async () => {
      setVideosLoading(true);
      try {
        const res = await fetch(`/api/cctv/history/?type=videos&page=${videosPage}&limit=${ITEMS_PER_PAGE}`);
        if (res.ok) {
          const data = await res.json();
          setVideosData(data);
        }
      } catch (err) {
        console.error("Error fetching videos history:", err);
      } finally {
        setVideosLoading(false);
      }
    };
    fetchVideos();
  }, [videosPage]);

  const getCompanionThumbnail = (videoUrl: string) => {
    return videoUrl.replace('/videos/', '/photos/').replace('.mp4', '.jpg');
  };

  const isDoorOpen = doorLogsData.current_status === 'OPEN';

  return (
    <div className="site-detail-page">
      {/* 1. Site Info Header Banner */}
      <div className="site-info-card">
        <div className="site-status-badge">
          <span className="status-dot-green"></span> Online
        </div>
        <h1 className="site-title">NAYAKA WS</h1>
        <div className="site-address">
          <FaMapMarkerAlt className="info-icon" />
          <span>Blok AX no, Jl. Kav. Marinir No.18, RT.14/RW.7, Pd. Klp., Kec. Duren Sawit, Kota Jakarta Timur, Daerah Khusus Ibukota Jakarta 17423</span>
        </div>
        <div className="site-tenant-info">
          <FaBuilding className="info-icon" />
          <span>Mitratel TSEL - Jabodetabek</span>
        </div>

        {/* Quick Status Pills Row */}
        <div className="site-status-pills-row">
          <div className="pill-badge pill-green">
            <FaCamera /> 2/2 kamera aktif
          </div>
          <div className="pill-badge pill-gray">
            <FaVideo /> Cam 1
          </div>
          <div className="pill-badge pill-gray">
            <FaVideo /> Cam 2
          </div>
          <div className={`pill-badge ${isDoorOpen ? 'pill-red-glow' : 'pill-gray'}`}>
            {isDoorOpen ? <FaDoorOpen /> : <FaDoorClosed />}
            {isDoorOpen ? ' Terbuka' : ' Tertutup'}
          </div>
        </div>
      </div>

      {/* 2. Device Control & Door Parameter Log Section */}
      <div className="device-cards-grid">
        {/* Power Device Card */}
        <div className="device-card">
          <div className="device-card-header">
            <div className="card-title-group">
              <FaBolt className="card-header-icon yellow-icon" />
              <h3>Power Device</h3>
            </div>
            <span className="status-pill pill-on-outline">ON</span>
          </div>
          <div className="device-card-body empty-state-body">
            <FaMinusCircle className="empty-icon" />
            <p>Tidak ada data</p>
          </div>
        </div>

        {/* Pintu Log Card */}
        <div className="device-card">
          <div className="device-card-header">
            <div className="card-title-group">
              <FaDoorClosed className="card-header-icon cyan-icon" />
              <h3>Pintu</h3>
            </div>
            <span className={`status-pill ${isDoorOpen ? 'pill-open-outline' : 'pill-close-outline'}`}>
              {doorLogsData.current_status}
            </span>
          </div>
          <div className="device-card-body door-logs-body">
            {doorLogsLoading ? (
              <div className="logs-loader">
                <FaSpinner className="spinner-icon spinning" />
                <p>Memuat log pintu...</p>
              </div>
            ) : doorLogsData.logs.length === 0 ? (
              <div className="empty-state-body">
                <FaMinusCircle className="empty-icon" />
                <p>Belum ada riwayat perubahan status pintu</p>
              </div>
            ) : (
              <div className="door-logs-list">
                {doorLogsData.logs.map((log) => (
                  <div key={log.id} className="door-log-row">
                    <span className="log-timestamp">{log.timestamp}</span>
                    <span className={`log-badge ${log.status === 'OPEN' ? 'log-badge-open' : 'log-badge-close'}`}>
                      {log.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
          {/* Pagination Footer */}
          <div className="device-card-footer">
            <span className="pagination-text">
              {doorLogsPage} / {doorLogsData.total_pages || 1}
            </span>
            <div className="pagination-controls">
              <button 
                disabled={doorLogsPage <= 1}
                onClick={() => setDoorLogsPage(doorLogsPage - 1)}
                className="mini-page-btn"
                title="Previous Page"
              >
                <FaChevronLeft />
              </button>
              <button 
                disabled={doorLogsPage >= doorLogsData.total_pages}
                onClick={() => setDoorLogsPage(doorLogsPage + 1)}
                className="mini-page-btn"
                title="Next Page"
              >
                <FaChevronRight />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Foto Section */}
      <div className="media-section">
        <div className="section-header-row">
          <div className="title-block orange-theme">
            <div className="icon-badge">
              <FaImage />
            </div>
            <h2>Foto</h2>
          </div>
          <div className="total-count-badge">{photosData.total_count}</div>
        </div>

        {photosLoading ? (
          <div className="section-loader">
            <FaSpinner className="spinner-icon spinning" />
            <p>Memuat Foto...</p>
          </div>
        ) : photosData.items.length === 0 ? (
          <div className="empty-history-placeholder">
            <p>Belum ada foto yang diambil</p>
          </div>
        ) : (
          <>
            <div className="media-grid">
              {photosData.items.map((item) => (
                <div key={item.name} className="media-item-card">
                  <div 
                    className="thumbnail-wrapper clickable" 
                    onClick={() => {
                      setActivePhotoUrl(item.url);
                      setActivePhotoTitle(item.camera + " - " + item.timestamp);
                    }}
                    title="View fullscreen image"
                  >
                    <img src={item.url} alt={item.camera} className="media-thumbnail" />
                  </div>
                  <div className="item-meta-footer">
                    <div className="meta-left">
                      <span className="camera-name">{item.camera}</span>
                      <span className="meta-timestamp">{item.timestamp}</span>
                    </div>
                    <div className="meta-right">
                      <span className="file-size">{item.size}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination photos */}
            <div className="history-pagination">
              <span className="page-indicator">Page {photosPage} of {photosData.total_pages || 1}</span>
              <div className="pagination-buttons">
                <button
                  disabled={photosPage <= 1}
                  onClick={() => setPhotosPage(photosPage - 1)}
                  className="page-btn"
                  title="Previous Page"
                >
                  <FaChevronLeft />
                </button>
                <button
                  disabled={photosPage >= photosData.total_pages}
                  onClick={() => setPhotosPage(photosPage + 1)}
                  className="page-btn"
                  title="Next Page"
                >
                  <FaChevronRight />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 4. Rekaman Section */}
      <div className="media-section">
        <div className="section-header-row">
          <div className="title-block purple-theme">
            <div className="icon-badge">
              <FaVideo />
            </div>
            <h2>Rekaman</h2>
          </div>
          <div className="total-count-badge">{videosData.total_count}</div>
        </div>

        {videosLoading ? (
          <div className="section-loader">
            <FaSpinner className="spinner-icon spinning" />
            <p>Memuat Rekaman...</p>
          </div>
        ) : videosData.items.length === 0 ? (
          <div className="empty-history-placeholder">
            <p>Belum ada video rekaman 10 detik</p>
          </div>
        ) : (
          <>
            <div className="media-grid">
              {videosData.items.map((item) => (
                <div key={item.name} className="media-item-card">
                  <div className="thumbnail-wrapper">
                    <img 
                      src={getCompanionThumbnail(item.url)} 
                      alt={item.camera} 
                      className="media-thumbnail"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "/placeholder-thumbnail.jpg";
                      }}
                    />
                    <div className="rec-badge">🔴 REC</div>
                    <button
                      className="play-overlay-circle"
                      onClick={() => {
                        setActiveVideoUrl(item.url);
                        setActiveVideoTitle(item.camera + " - " + item.timestamp);
                      }}
                      title="Play video"
                    >
                      <FaPlay />
                    </button>
                  </div>
                  <div className="item-meta-footer">
                    <div className="meta-left">
                      <span className="camera-name">{item.camera}</span>
                      <span className="meta-timestamp">{item.timestamp}</span>
                    </div>
                    <div className="meta-right">
                      <span className="file-size">{item.size}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination videos */}
            <div className="history-pagination">
              <span className="page-indicator">Page {videosPage} of {videosData.total_pages || 1}</span>
              <div className="pagination-buttons">
                <button
                  disabled={videosPage <= 1}
                  onClick={() => setVideosPage(videosPage - 1)}
                  className="page-btn"
                  title="Previous Page"
                >
                  <FaChevronLeft />
                </button>
                <button
                  disabled={videosPage >= videosData.total_pages}
                  onClick={() => setVideosPage(videosPage + 1)}
                  className="page-btn"
                  title="Next Page"
                >
                  <FaChevronRight />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Video Modal Player */}
      {activeVideoUrl && (
        <div className="video-modal-overlay" onClick={() => setActiveVideoUrl(null)}>
          <div className="video-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setActiveVideoUrl(null)}>×</button>
            <h3 className="modal-title">{activeVideoTitle}</h3>
            <video src={`${activeVideoUrl}?t=${new Date().getTime()}`} controls autoPlay className="modal-video" />
          </div>
        </div>
      )}

      {/* Fullscreen Photo Modal */}
      {activePhotoUrl && (
        <div className="video-modal-overlay" onClick={() => setActivePhotoUrl(null)}>
          <div className="video-modal-content image-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setActivePhotoUrl(null)}>×</button>
            <h3 className="modal-title">{activePhotoTitle}</h3>
            <img src={activePhotoUrl} alt="Fullscreen View" className="modal-image-fullscreen" />
          </div>
        </div>
      )}
    </div>
  );
};

export default SiteDetail;
