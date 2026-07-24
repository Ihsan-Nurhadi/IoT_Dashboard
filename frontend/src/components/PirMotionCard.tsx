import React, { useState, useEffect } from 'react';
import './PirMotionCard.css';
import { PiSiren } from 'react-icons/pi';

interface MotionStatus {
  status: string;
  last_updated: string;
}

const PirMotionCard: React.FC = () => {
  const [sensors, setSensors] = useState<MotionStatus[]>([
    { status: 'Standby', last_updated: '-' },
    { status: 'Standby', last_updated: '-' },
    { status: 'Standby', last_updated: '-' },
    { status: 'Standby', last_updated: '-' }
  ]);
  const [latestActivity, setLatestActivity] = useState<string>('-');
  const [hasAnyDetection, setHasAnyDetection] = useState<boolean>(false);

  const fetchSensors = async () => {
    try {
      const endpoints = [
        '/api/get-motion1-status/',
        '/api/get-motion2-status/',
        '/api/get-motion3-status/',
        '/api/get-motion4-status/'
      ];

      const results = await Promise.all(
        endpoints.map(ep => fetch(ep).then(res => res.ok ? res.json() : { status: 'Standby', last_updated: '-' }))
      );

      setSensors(results);

      const isAnyDetected = results.some(s => s.status?.toLowerCase() === 'detected');
      setHasAnyDetection(isAnyDetected);

      // Find the most recent timestamp among active detections
      const validTimes = results
        .map(s => s.last_updated)
        .filter(t => t && t !== '-');
      
      if (validTimes.length > 0) {
        setLatestActivity(validTimes[0]);
      }
    } catch (err) {
      console.error("Failed to fetch PIR sensors status:", err);
    }
  };

  useEffect(() => {
    fetchSensors();
    const interval = setInterval(fetchSensors, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="pir-motion-card">
      <div className="pir-card-header">
        <div className="pir-header-left">
          <PiSiren className="pir-header-icon" />
          <span className="pir-header-title">PIR MOTION</span>
        </div>
        <div className="pir-header-right">
          <span className={`pir-status-badge ${hasAnyDetection ? 'active' : 'standby'}`}>
            {hasAnyDetection ? 'Deteksi' : 'Standby'}
          </span>
        </div>
      </div>

      <div className="pir-card-body">
        {/* Animated Radar Scanner */}
        <div className="radar-scanner-container">
          <div className="radar-screen">
            <div className="radar-sweep"></div>
            <div className="radar-ring ring-1"></div>
            <div className="radar-ring ring-2"></div>
            <div className="radar-ring ring-3"></div>
            <div className="radar-crosshair-h"></div>
            <div className="radar-crosshair-v"></div>
            
            {/* 4 Radar Channel Target Dots */}
            {sensors.map((s, idx) => {
              const isDetected = s.status?.toLowerCase() === 'detected';
              return (
                <div 
                  key={idx} 
                  className={`radar-target target-${idx} ${isDetected ? 'detected' : ''}`}
                  title={`Saluran ${idx}: ${s.status}`}
                >
                  <span className="target-num">{idx}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Channels Status List */}
        <div className="pir-channels-list">
          <div className="list-title">SALURAN</div>
          {sensors.map((s, idx) => {
            const isDetected = s.status?.toLowerCase() === 'detected';
            return (
              <div key={idx} className="channel-item">
                <div className="channel-info">
                  <span className={`channel-dot ${isDetected ? 'detected' : ''}`}></span>
                  <span className="channel-name">Saluran {idx}</span>
                </div>
                <span className={`channel-status-pill ${isDetected ? 'detected' : 'standby'}`}>
                  {isDetected ? 'Deteksi' : 'Standby'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="pir-card-footer">
        Aktivitas terakhir: {latestActivity}
      </div>
    </div>
  );
};

export default PirMotionCard;
