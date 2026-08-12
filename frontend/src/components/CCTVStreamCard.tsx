import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { FaCamera, FaPlay, FaRegFileVideo, FaSpinner } from 'react-icons/fa';
import './CCTVStreamCard.css';

interface CCTVStreamCardProps {
  streamId?: string;
  cameraName?: string;
  subTitle?: string;
  fallbackPhotoUrl?: string;
  onVerifyResult?: (result: any) => void;
}

const CCTVStreamCard: React.FC<CCTVStreamCardProps> = ({
  streamId = 'cctv',
  cameraName = 'Kamera #1',
  subTitle = '',
  fallbackPhotoUrl,
  onVerifyResult
}) => {
  const [photoUrl, setPhotoUrl] = useState<string | null>(fallbackPhotoUrl || null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [timestamp, setTimestamp] = useState<string>('-');
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingType, setLoadingType] = useState<'photo' | 'video' | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [showVideoModal, setShowVideoModal] = useState<boolean>(false);
  const [showPhotoModal, setShowPhotoModal] = useState<boolean>(false);

  // Fetch the latest captured photo/video on mount
  useEffect(() => {
    const fetchLatest = async () => {
      try {
        const res = await fetch('/api/cctv/latest/');
        if (res.ok) {
          const data = await res.json();
          const camData = data[streamId];
          if (camData) {
            setPhotoUrl(camData.photo_url);
            setVideoUrl(camData.video_url);
            setTimestamp(camData.formatted_time || '-');
          }
        }
      } catch (err) {
        console.error("Failed to fetch latest cctv metadata:", err);
      }
    };
    fetchLatest();
  }, [streamId]);

  const handleCapturePhoto = async () => {
    if (loading) return;
    setLoading(true);
    setLoadingType('photo');
    setProgress(0);

    const duration = 1500;
    const intervalTime = 100;
    const steps = duration / intervalTime;
    let currentStep = 0;

    const progInterval = setInterval(() => {
      currentStep++;
      const percent = Math.min((currentStep / steps) * 100, 95);
      setProgress(Math.round(percent));
    }, intervalTime);

    try {
      const res = await fetch(`/api/cctv/capture-photo/?src=${streamId}`, {
        method: 'POST'
      });
      clearInterval(progInterval);
      if (res.ok) {
        const data = await res.json();
        setProgress(100);
        setTimeout(() => {
          setPhotoUrl(data.url);
          setVideoUrl(null); // Clear previous video since photo is now the latest capture
          setTimestamp(data.formatted_time);
          setLoading(false);
          setLoadingType(null);
          if (onVerifyResult && data.antenna_check) {
            onVerifyResult(data.antenna_check);
          }
        }, 300);
      } else {
        alert("Failed to capture photo");
        setLoading(false);
        setLoadingType(null);
      }
    } catch (err) {
      clearInterval(progInterval);
      console.error(err);
      alert("Error capturing photo");
      setLoading(false);
      setLoadingType(null);
    }
  };

  const handleCaptureVideo = async () => {
    if (loading) return;
    setLoading(true);
    setLoadingType('video');
    setProgress(0);

    const duration = 10000;
    const intervalTime = 100;
    const steps = duration / intervalTime;
    let currentStep = 0;

    const progInterval = setInterval(() => {
      currentStep++;
      const percent = Math.min((currentStep / steps) * 100, 98);
      setProgress(Math.round(percent));
    }, intervalTime);

    try {
      const res = await fetch(`/api/cctv/capture-video/?src=${streamId}`, {
        method: 'POST'
      });
      clearInterval(progInterval);
      if (res.ok) {
        const data = await res.json();
        setProgress(100);
        setTimeout(() => {
          setVideoUrl(data.url);
          if (data.photo_url) {
            setPhotoUrl(data.photo_url); // Update thumbnail to the video's companion photo
          }
          setTimestamp(data.formatted_time);
          setLoading(false);
          setLoadingType(null);
        }, 300);
      } else {
        alert("Failed to capture video");
        setLoading(false);
        setLoadingType(null);
      }
    } catch (err) {
      clearInterval(progInterval);
      console.error(err);
      alert("Error capturing video");
      setLoading(false);
      setLoadingType(null);
    }
  };

  return (
    <div className="cctv-panel">
      <div className="cctv-monitor-container">
        {/* Bounding Box Image or Video placeholder */}
        {photoUrl && !loading ? (
          <div className="image-wrapper">
            <img 
              src={`${photoUrl}?t=${new Date().getTime()}`} 
              alt={cameraName} 
              className="cctv-image clickable"
              onClick={() => setShowPhotoModal(true)}
              style={{ cursor: 'pointer' }}
              title="Click to view fullscreen"
            />
            {videoUrl && (
              <button 
                className="play-overlay-btn" 
                onClick={() => setShowVideoModal(true)}
                title="Play latest recorded video"
              >
                <FaPlay />
              </button>
            )}
          </div>
        ) : (
          !loading && (
            <div className="cctv-placeholder">
              <FaRegFileVideo className="placeholder-icon" />
              <p>Belum ada rekaman/foto</p>
            </div>
          )
        )}

        {/* Loading Overlay */}
        {loading && (
          <div className="cctv-loading-overlay">
            <FaSpinner className="spinner-icon spinning" />
            <span className="loading-text">{loadingType === 'photo' ? 'Foto...' : 'Video...'}</span>
            <div className="progress-bar-container">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
            </div>
          </div>
        )}

        {/* Floating Action Buttons */}
        <div className="cctv-floating-actions">
          <button 
            className="floating-btn" 
            onClick={handleCapturePhoto} 
            disabled={loading}
            title="Ambil Foto"
          >
            <FaCamera />
          </button>
          <button 
            className="floating-btn" 
            onClick={handleCaptureVideo} 
            disabled={loading}
            title="Ambil Video (10 Detik)"
          >
            <FaPlay />
          </button>
        </div>

        {/* Bottom HUD */}
        <div className="cctv-hud-bottom">
          <div className="hud-left">
            <span className="status-dot online"></span>
            <span className="camera-label">{cameraName}</span>
          </div>
          <div className="hud-right">
            <span className="timestamp-label">{timestamp}</span>
          </div>
        </div>
      </div>

      {/* Video Modal Player */}
      {showVideoModal && videoUrl && createPortal(
        <div className="video-modal-overlay" onClick={() => setShowVideoModal(false)}>
          <div className="video-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setShowVideoModal(false)}>×</button>
            <h3 className="modal-title">Live Video - {cameraName}</h3>
            <video src={`${videoUrl}?t=${new Date().getTime()}`} controls autoPlay className="modal-video" />
          </div>
        </div>,
        document.body
      )}

      {/* Fullscreen Photo Modal */}
      {showPhotoModal && photoUrl && createPortal(
        <div className="video-modal-overlay" onClick={() => setShowPhotoModal(false)}>
          <div className="video-modal-content image-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal-btn" onClick={() => setShowPhotoModal(false)}>×</button>
            <h3 className="modal-title">{cameraName} - Fullscreen View</h3>
            <img src={photoUrl} alt={cameraName} className="modal-image-fullscreen" />
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default CCTVStreamCard;
