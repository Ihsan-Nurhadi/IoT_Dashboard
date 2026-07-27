import React from 'react';

interface HeroCompassCardProps {
  windSpeed: number; // m/s
  windHeading: number; // degrees
}

export const HeroCompassCard: React.FC<HeroCompassCardProps> = ({
  windSpeed,
  windHeading,
}) => {
  const getWindDirectionText = (heading: number) => {
    if (heading >= 337.5 || heading < 22.5) return 'Utara (N)';
    if (heading >= 22.5 && heading < 67.5) return 'Timur Laut (NE)';
    if (heading >= 67.5 && heading < 112.5) return 'Timur (E)';
    if (heading >= 112.5 && heading < 157.5) return 'Tenggara (SE)';
    if (heading >= 157.5 && heading < 202.5) return 'Selatan (S)';
    if (heading >= 202.5 && heading < 247.5) return 'Barat Daya (SW)';
    if (heading >= 247.5 && heading < 292.5) return 'Barat (W)';
    return 'Barat Laut (NW)';
  };

  const directionText = getWindDirectionText(windHeading);
  const speedPercentage = Math.min(100, (windSpeed / 5.0) * 100);

  return (
    <div className="aqms-hero-card glass-card">
      <div className="aqms-hero-left">
        <h2 className="aqms-section-subtitle uppercase">
          ⚠️ PARAMETER KESELAMATAN KRITIS
        </h2>
        <div className="aqms-hero-metrics">
          <div className="aqms-hero-metric-box">
            <p className="aqms-hero-metric-title">Kecepatan Angin</p>
            <div className="aqms-hero-value-wrap">
              <span className="aqms-hero-value text-primary">{windSpeed.toFixed(2)}</span>
              <span className="aqms-hero-unit">m/s</span>
            </div>
            <div className="aqms-progress-track">
              <div
                className="aqms-progress-fill"
                style={{ width: `${speedPercentage}%` }}
              ></div>
            </div>
          </div>

          <div className="aqms-hero-metric-box">
            <p className="aqms-hero-metric-title">Arah Angin</p>
            <div className="aqms-hero-compass-text-wrap">
              <span className="aqms-compass-icon">🧭</span>
              <span className="aqms-compass-direction">{directionText}</span>
            </div>
            <p className="aqms-compass-heading">
              Heading: {windHeading.toFixed(1)}° True
            </p>
          </div>
        </div>
      </div>

      <div className="aqms-hero-right">
        <div className="aqms-compass-circle">
          <div className="aqms-compass-labels">
            <div className="aqms-compass-label top">N</div>
            <div className="aqms-compass-label right">E</div>
            <div className="aqms-compass-label bottom">S</div>
            <div className="aqms-compass-label left">W</div>
          </div>
          <div
            className="aqms-compass-arrow"
            style={{ transform: `rotate(${windHeading}deg)` }}
          ></div>
          <div className="aqms-compass-center">
            <span className="aqms-center-icon">💨</span>
          </div>
        </div>
      </div>
    </div>
  );
};
