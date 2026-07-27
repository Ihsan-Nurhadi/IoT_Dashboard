import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  unit: string;
  icon: string;
  colorClass?: string; // 'tertiary' | 'primary' | 'secondary' | 'error'
  badgeText?: string;
  history?: number[];
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  icon,
  colorClass = 'primary',
  badgeText,
  history = [10, 12, 11, 15, 14, 13, 16, 15, 17, 16],
}) => {
  const getColorHex = (cls: string) => {
    switch (cls) {
      case 'tertiary':
        return '#22c55e'; // Green
      case 'secondary':
        return '#f59e0b'; // Yellow
      case 'error':
        return '#ef4444'; // Red
      case 'primary':
      default:
        return '#3b82f6'; // Blue
    }
  };

  const colorHex = getColorHex(colorClass);

  const generateSparklineD = (points: number[]) => {
    const width = 100;
    const height = 20;
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;

    let d = `M 0,${height - ((points[0] - min) / range) * height}`;
    for (let i = 1; i < points.length; i++) {
      const x = (i / (points.length - 1)) * width;
      const y = height - ((points[i] - min) / range) * height;
      d += ` L ${x},${y}`;
    }
    return d;
  };

  return (
    <div className="aqms-metric-card glass-card">
      <div className="aqms-metric-header">
        <span className="aqms-metric-icon" style={{ color: colorHex }}>
          {icon}
        </span>
        {badgeText && (
          <span
            className="aqms-metric-badge"
            style={{ color: colorHex, backgroundColor: `${colorHex}15` }}
          >
            {badgeText}
          </span>
        )}
      </div>
      <p className="aqms-metric-title">{title}</p>
      <div className="aqms-metric-value-wrap">
        <span className="aqms-metric-value">{value}</span>
        <span className="aqms-metric-unit">{unit}</span>
      </div>

      <svg
        className="aqms-sparkline-svg"
        viewBox="0 0 100 20"
        style={{ stroke: colorHex }}
      >
        <path d={generateSparklineD(history)}></path>
      </svg>
    </div>
  );
};
