import React from 'react';
import type { SensorReading } from './types';

interface AirQualityGridProps {
  reading: SensorReading;
}

export const AirQualityGrid: React.FC<AirQualityGridProps> = ({ reading }) => {
  return (
    <div className="aqms-aqi-grid-section">
      <h3 className="aqms-section-subtitle uppercase">
        🌾 PARTIKULAT & KUALITAS UDARA
      </h3>
      <div className="aqms-aqi-grid">
        {/* PM2.5 & PM10 Card */}
        <div className="aqms-metric-card glass-card">
          <p className="aqms-metric-title uppercase">
            PARTIKULAT (PM2.5 / PM10)
          </p>
          <div className="aqms-pm-wrapper">
            <div className="aqms-pm-row">
              <div>
                <span className="aqms-metric-value text-primary">{reading.pm25}</span>
                <span className="aqms-metric-unit ml-1">ug/m³</span>
                <p className="aqms-pm-sub">PM2.5</p>
              </div>
              <div className="text-right">
                <span className="aqms-metric-value text-primary">{reading.pm10}</span>
                <span className="aqms-metric-unit ml-1">ug/m³</span>
                <p className="aqms-pm-sub">PM10</p>
              </div>
            </div>
            <div className="aqms-pm-bar-track">
              <div className="aqms-pm-bar-fill-tertiary"></div>
              <div className="aqms-pm-bar-fill-primary"></div>
            </div>
          </div>
        </div>

        {/* Ion Negatif Card */}
        <div className="aqms-metric-card glass-card justify-between">
          <div>
            <p className="aqms-metric-title uppercase">
              ION NEGATIF
            </p>
            <div className="aqms-metric-value-wrap">
              <span className="aqms-metric-value text-tertiary">{reading.negative_ion}</span>
              <span className="aqms-metric-unit">ion/cm³</span>
            </div>
          </div>
          <div className="aqms-card-footer-text text-tertiary">
            <span>✓ Konsentrasi Alami</span>
          </div>
        </div>

        {/* Kebisingan (Noise) Card */}
        <div className="aqms-metric-card glass-card justify-between">
          <div>
            <p className="aqms-metric-title uppercase">
              KEBISINGAN (NOISE)
            </p>
            <div className="aqms-metric-value-wrap">
              <span className="aqms-metric-value text-secondary">{reading.noise ?? 0}</span>
              <span className="aqms-metric-unit">dB</span>
            </div>
          </div>
          <div className="aqms-card-footer-text text-secondary">
            <span>🔊 Tingkat Kebisingan Area</span>
          </div>
        </div>
      </div>
    </div>
  );
};
