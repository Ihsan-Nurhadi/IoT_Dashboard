import React, { useState, useEffect } from 'react';
import './PirMotionCard.css';
import { PiSiren } from 'react-icons/pi';
import { FaExclamationTriangle, FaUnlink } from 'react-icons/fa';

interface MotionStatus {
  status: string;
  last_updated: string;
}

interface PirAlarmStatus {
  is_alarm: boolean;
  is_disconnected: boolean;
  cable_status: string;
  last_updated: string;
  alert_title: string | null;
  alert_time: string | null;
}

const PirMotionCard: React.FC = () => {
  const [sensors, setSensors] = useState<MotionStatus[]>([
    { status: 'Standby', last_updated: '-' },
    { status: 'Standby', last_updated: '-' },
    { status: 'Standby', last_updated: '-' }
  ]);
  const [latestActivity, setLatestActivity] = useState<string>('-');
  const [hasAnyDetection, setHasAnyDetection] = useState<boolean>(false);
  const [alarmStatus, setAlarmStatus] = useState<PirAlarmStatus>({
    is_alarm: false,
    is_disconnected: false,
    cable_status: 'CONNECTED',
    last_updated: '-',
    alert_title: null,
    alert_time: null
  });

  const fetchSensors = async () => {
    try {
      const endpoints = [
        '/api/get-motion1-status/',
        '/api/get-motion2-status/',
        '/api/get-motion3-status/'
      ];

      const [resSensors, resAlarm] = await Promise.all([
        Promise.all(endpoints.map(ep => fetch(ep).then(res => res.ok ? res.json() : { status: 'Standby', last_updated: '-' }))),
        fetch('/api/pir-alarm-status/').then(res => res.ok ? res.json() : null).catch(() => null)
      ]);

      setSensors(resSensors);

      if (resAlarm) {
        setAlarmStatus(resAlarm);
      }

      const isAnyDetected = resSensors.some(s => s.status?.toLowerCase() === 'detected');
      setHasAnyDetection(isAnyDetected);

      // Find the most recent timestamp among active detections
      const validTimes = resSensors
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
          <PiSiren className={`pir-header-icon ${alarmStatus.is_disconnected ? 'alarm-icon' : ''}`} />
          <span className="pir-header-title">PIR MOTION (WHITEBOX)</span>
        </div>
        <div className="pir-header-right">
          {alarmStatus.is_disconnected ? (
            <span className="pir-status-badge alarm-badge">
              <FaUnlink className="badge-icon-spin" /> KABEL DICABUT (ALARM)
            </span>
          ) : (
            <span className={`pir-status-badge ${hasAnyDetection ? 'active' : 'standby'}`}>
              {hasAnyDetection ? 'Deteksi' : 'Standby'}
            </span>
          )}
        </div>
      </div>

      {/* Emergency Alarm Banner for Disconnected Cable */}
      {alarmStatus.is_disconnected && (
        <div className="pir-alarm-alert-banner">
          <div className="alarm-banner-left">
            <FaExclamationTriangle className="alarm-blink-icon" />
            <div>
              <div className="alarm-banner-title">PERINGATAN: KABEL SENSOR TERPUTUS (0, 0, 0)</div>
              <div className="alarm-banner-desc">
                Seluruh saluran PIR bernilai 0. Sirine Rotary Beacon diaktifkan. Periksa koneksi kabel fisik sensor ke Whitebox.
              </div>
            </div>
          </div>
          {alarmStatus.alert_time && (
            <span className="alarm-banner-time">Waktu: {alarmStatus.alert_time}</span>
          )}
        </div>
      )}

      <div className="pir-card-body">
        {/* Animated Radar Scanner */}
        <div className="radar-scanner-container">
          <div className={`radar-screen ${alarmStatus.is_disconnected ? 'alarm-mode' : ''}`}>
            <div className="radar-sweep"></div>
            <div className="radar-ring ring-1"></div>
            <div className="radar-ring ring-2"></div>
            <div className="radar-ring ring-3"></div>
            <div className="radar-crosshair-h"></div>
            <div className="radar-crosshair-v"></div>
            
            {/* 3 Radar Channel Target Dots */}
            {sensors.map((s, idx) => {
              const isDetected = s.status?.toLowerCase() === 'detected';
              const isCableCut = alarmStatus.is_disconnected;
              const channelNum = idx + 1;
              return (
                <div 
                  key={idx} 
                  className={`radar-target target-${idx} ${isDetected ? 'detected' : ''} ${isCableCut ? 'cable-cut' : ''}`}
                  title={`Saluran ${channelNum}: ${isCableCut ? 'Terputus (0)' : s.status}`}
                >
                  <span className="target-num">{channelNum}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Channels Status List */}
        <div className="pir-channels-list">
          <div className="list-title">SALURAN WHITEBOX</div>
          {sensors.map((s, idx) => {
            const isDetected = s.status?.toLowerCase() === 'detected';
            const isCableCut = alarmStatus.is_disconnected;
            const channelNum = idx + 1;
            return (
              <div key={idx} className={`channel-item ${isCableCut ? 'channel-cut' : ''}`}>
                <div className="channel-info">
                  <span className={`channel-dot ${isDetected ? 'detected' : ''} ${isCableCut ? 'cable-cut' : ''}`}></span>
                  <span className="channel-name">Saluran {channelNum}</span>
                </div>
                {isCableCut ? (
                  <span className="channel-status-pill disconnected">
                    Terputus (0)
                  </span>
                ) : (
                  <span className={`channel-status-pill ${isDetected ? 'detected' : 'standby'}`}>
                    {isDetected ? 'Deteksi' : 'Standby'}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="pir-card-footer">
        {alarmStatus.is_disconnected ? (
          <span className="footer-alarm-text">
            ⚠️ Status Sistem: Terdeteksi Pemutusan Kabel (PIR s=[0,0,0]) | Sirine Rotary Aktif
          </span>
        ) : (
          <span>Aktivitas terakhir: {latestActivity}</span>
        )}
      </div>
    </div>
  );
};

export default PirMotionCard;
