import React, { useState, useEffect } from 'react';
import Card from './Card';
import { FaVideo, FaVideoSlash, FaPlay, FaPause } from 'react-icons/fa';
import './CCTVStreamCard.css';

interface CCTVStreamCardProps {
  streamId?: string;
  cameraName?: string;
  subTitle?: string;
}

const CCTVStreamCard: React.FC<CCTVStreamCardProps> = ({
  streamId = 'cctv',
  cameraName = 'CAM 01 - MAIN CH',
  subTitle = 'Local RTSP camera feed via Django'
}) => {
  const [streamActive, setStreamActive] = useState(false);
  const [timestamp, setTimestamp] = useState('');

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
          <h3 className="card-title">{cameraName}</h3>
          <p className="card-subtitle">{subTitle}</p>
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
            <iframe
              src={`/go2rtc/stream.html?src=${streamId}&mode=webrtc`}
              title={`Live CCTV Stream - ${cameraName}`}
              className="cctv-image"
              style={{ border: 'none', width: '100%', height: '100%' }}
              allow="autoplay; fullscreen"
            />
            {/* HUD Overlay */}
            <div className="cctv-hud">
              <div className="hud-top">
                <span className="hud-badge live">🔴 LIVE</span>
                <span className="hud-badge mode">WebRTC/MSE</span>
              </div>
              <div className="hud-bottom">
                <span className="hud-info">{cameraName}</span>
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
