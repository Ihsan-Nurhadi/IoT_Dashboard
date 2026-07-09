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
    </Card>
  );
};

export default CCTVStreamCard;
