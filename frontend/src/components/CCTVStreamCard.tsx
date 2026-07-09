import React, { useState, useEffect } from 'react';
import Card from './Card';
import { FaVideo, FaVideoSlash, FaPlay, FaPause, FaInfoCircle } from 'react-icons/fa';
import './CCTVStreamCard.css';

const CCTVStreamCard: React.FC = () => {
  const [streamActive, setStreamActive] = useState(false);
  const [timestamp, setTimestamp] = useState('');
  const [showInfo, setShowInfo] = useState(false);

  // Update CCTV HUD clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimestamp(now.toLocaleString('id-ID', { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="cctv-stream-card">
      <div className="card-header">
        <div className="header-text">
          <div className="icon-container cctv">
          <FaVideo />
          </div>
          <h3 className="card-title">CCTV Monitoring</h3>
          <p className="card-subtitle">Local RTSP camera feed via Django</p>
        </div>
        <div className="header-actions">
          <button className={`icon-btn ${showInfo ? 'active' : ''}`} onClick={() => setShowInfo(!showInfo)} title="Stream Info">
            <FaInfoCircle />
          </button>
          <button 
            className={`icon-btn play-pause-btn ${streamActive ? 'active' : ''}`} 
            onClick={() => setStreamActive(!streamActive)} 
            title={streamActive ? "Stop Stream" : "Start Stream"}
          >
            {streamActive ? <FaPause /> : <FaPlay />}
          </button>
        </div>
      </div>

      <div className="cctv-monitor-container">
        {streamActive ? (
          <div className="image-wrapper">
            <img
              src="/api/cctv-stream/"
              alt="Live CCTV stream"
              className="cctv-image"
            />
            {/* HUD Overlay */}
            <div className="cctv-hud">
              <div className="hud-top">
                <span className="hud-badge live">🔴 LIVE</span>
                <span className="hud-badge mode">MJPEG</span>
              </div>
              <div className="hud-bottom">
                <span className="hud-info">CAM 01 - MAIN CH</span>
                <span className="hud-timestamp">{timestamp}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="cctv-placeholder">
            <FaVideoSlash className="placeholder-icon" />
            <p>Stream is Stopped</p>
            <button className="start-btn" onClick={() => setStreamActive(true)}>
              <FaPlay style={{ marginRight: '8px' }} /> Start Stream
            </button>
          </div>
        )}
      </div>

      {showInfo && (
        <div className="cctv-info-panel">
          <h4>Konfigurasi Stream</h4>
          <div className="info-grid">
            <span className="info-label">RTSP Source:</span>
            <span className="info-val">rtsp://admin:BWIJZS@10.10.4.89:554/h264/ch1/main/av_stream</span>
            <span className="info-label">Transcoder:</span>
            <span className="info-val">OpenCV (Django backend)</span>
            <span className="info-label">Vite Proxy:</span>
            <span className="info-val">/api/cctv-stream/ &rarr; http://127.0.0.1:8000</span>
          </div>
        </div>
      )}
    </Card>
  );
};

export default CCTVStreamCard;
