import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Header.css';
import { FaHome, FaBell, FaCheckDouble, FaSun, FaMoon, FaCamera, FaMapMarkerAlt, FaExternalLinkAlt } from 'react-icons/fa';
import { PiSiren } from 'react-icons/pi';

interface AlertItem {
  id: string;
  type?: 'camera' | 'pir' | 'stolen';
  camera: string;
  title?: string;
  url: string;
  timestamp: string;
  raw_time: string;
}

const Header: React.FC = () => {
  const location = useLocation();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertCategory, setAlertCategory] = useState<'all' | 'camera' | 'pir'>('all');
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [showDropdown, setShowDropdown] = useState<boolean>(false);
  const [fullscreenPhotoUrl, setFullscreenPhotoUrl] = useState<string | null>(null);
  const [fullscreenPhotoTitle, setFullscreenPhotoTitle] = useState<string>("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const lastKnownAlertIdRef = useRef<string | null>(null);

  // Dark/Light Mode state
  const [theme, setTheme] = useState<string>(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) return savedTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.className = theme;
    localStorage.setItem("theme", theme);
    window.dispatchEvent(new CustomEvent('theme-change', { detail: theme }));
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const playNotificationSound = () => {
    try {
      const audio = new Audio('/notification.wav');
      audio.volume = 0.7;
      audio.play().catch(err => {
        console.log("Audio autoplay waiting for user interaction:", err);
      });
    } catch (err) {
      console.error("Error playing notification sound:", err);
    }
  };

  // Fetch alerts
  const fetchAlerts = async () => {
    try {
      const res = await fetch(`/api/cctv/alerts/?category=${alertCategory}`);
      if (res.ok) {
        const data: AlertItem[] = await res.json();
        
        // Trigger ringtone sound if a new alert arrives
        if (data.length > 0) {
          const latestAlertId = data[0].id;
          if (lastKnownAlertIdRef.current !== null && lastKnownAlertIdRef.current !== latestAlertId) {
            playNotificationSound();
          }
          lastKnownAlertIdRef.current = latestAlertId;
        }

        setAlerts(data);
        
        // Calculate unread count
        const lastReadTime = localStorage.getItem("lastReadAlertTime");
        if (lastReadTime) {
          const unread = data.filter((item: AlertItem) => item.raw_time > lastReadTime).length;
          setUnreadCount(unread);
        } else if (data.length > 0) {
          setUnreadCount(data.length);
        }
      }
    } catch (err) {
      console.error("Failed to fetch CCTV alerts:", err);
    }
  };

  useEffect(() => {
    fetchAlerts();
    // Poll every 5 seconds
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [alertCategory]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleBellClick = () => {
    setShowDropdown(!showDropdown);
    if (alerts.length > 0) {
      localStorage.setItem("lastReadAlertTime", alerts[0].raw_time);
      setUnreadCount(0);
    }
  };

  const handleMarkAllRead = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (alerts.length > 0) {
      localStorage.setItem("lastReadAlertTime", alerts[0].raw_time);
      setUnreadCount(0);
    }
  };

  return (
    <header className="app-header">
      <div className="header-left">
        <Link to="/" className="nav-logo" style={{ textDecoration: 'none' }}>
          <div className="nav-logo-icon">📡</div>
          TOWER SENTINEL
        </Link>
        <div className="status-badge">
          <div className="status-dot"></div>
          <span className="badge-text">ACTIVE</span>
        </div>
      </div>

      <div className="header-nav-links">
        <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}><FaHome /> Portal</Link>
        <Link to="/site-detail" className={`nav-link ${location.pathname === '/site-detail' ? 'active' : ''}`}>🖥️ NMS</Link>
        <Link to="/verticality/E32_VER_WS" className={`nav-link ${location.pathname.startsWith('/verticality') ? 'active' : ''}`}>📐 Verticality</Link>
        <Link to="/aqms" className={`nav-link ${location.pathname === '/aqms' ? 'active' : ''}`}>🌤️ AQMS</Link>
        <Link to="/asset-monitoring" className={`nav-link ${location.pathname === '/asset-monitoring' ? 'active' : ''}`}>📦 Asset</Link>
        <Link to="/rfid-monitoring" className={`nav-link ${location.pathname === '/rfid-monitoring' ? 'active' : ''}`}>🏷️ RFID</Link>
        <Link to="/cable-sense" className={`nav-link ${location.pathname === '/cable-sense' ? 'active' : ''}`}>⚡ Cable Sense</Link>
      </div>

      <div className="nav-actions">
        {/* Notification Bell Container */}
        <div className="notification-bell-container" ref={dropdownRef}>
          <button 
            className={`bell-btn ${unreadCount > 0 ? 'has-unread' : ''}`} 
            onClick={handleBellClick}
            title="Notification Alerts"
          >
            <FaBell />
            {unreadCount > 0 && (
              <span className="bell-badge">{unreadCount}</span>
            )}
          </button>

          {/* Alerts Dropdown Menu */}
          {showDropdown && (
            <div className="alerts-dropdown">
              <div className="dropdown-header">
                <h3>Notifikasi</h3>
                {unreadCount > 0 && (
                  <button className="mark-read-btn" onClick={handleMarkAllRead}>
                    <FaCheckDouble /> Tandai dibaca
                  </button>
                )}
              </div>
              
              {/* Notification Category Tabs */}
              <div className="alert-category-tabs">
                <button 
                  className={`alert-tab-btn ${alertCategory === 'all' ? 'active' : ''}`}
                  onClick={() => setAlertCategory('all')}
                >
                  Semua
                </button>
                <button 
                  className={`alert-tab-btn ${alertCategory === 'camera' ? 'active' : ''}`}
                  onClick={() => setAlertCategory('camera')}
                >
                  <FaCamera className="tab-icon" /> Kamera
                </button>
                <button 
                  className={`alert-tab-btn ${alertCategory === 'pir' ? 'active' : ''}`}
                  onClick={() => setAlertCategory('pir')}
                >
                  <PiSiren className="tab-icon" /> PIR
                </button>
              </div>

              <div className="dropdown-list">
                {alerts.length === 0 ? (
                  <div className="dropdown-empty">Tidak ada notifikasi</div>
                ) : (
                  alerts.map((item) => (
                    <div 
                      key={item.id} 
                      className={`dropdown-item ${item.type === 'stolen' ? 'alert-stolen-item' : ''}`}
                      onClick={() => {
                        setFullscreenPhotoUrl(item.url);
                        setFullscreenPhotoTitle(`${item.title || item.camera} - ${item.timestamp}`);
                        setShowDropdown(false);
                      }}
                    >
                      <div className="dropdown-item-thumb">
                        <img src={item.url} alt="thumbnail" />
                      </div>
                      <div className="dropdown-item-details">
                        <span className="item-text" style={{ color: item.type === 'stolen' ? '#ef4444' : 'inherit', fontWeight: item.type === 'stolen' ? 600 : 'normal' }}>
                          {item.title || `Orang terdeteksi di ${item.camera}`}
                        </span>
                        <span className="item-time">{item.timestamp}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Theme Toggle Button */}
        <button 
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? <FaMoon /> : <FaSun />}
        </button>

      </div>


      {/* Fullscreen Alert Photo Viewer Modal */}
      {fullscreenPhotoUrl && (
        <div className="video-modal-overlay" onClick={() => setFullscreenPhotoUrl(null)}>
          <div className="video-modal-content image-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setFullscreenPhotoUrl(null)}>×</button>
            <h3 className="modal-title">{fullscreenPhotoTitle}</h3>
            <img src={fullscreenPhotoUrl} alt="Detection Alert" className="modal-image-fullscreen" />
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
