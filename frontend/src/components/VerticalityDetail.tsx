import React from 'react';
import { useParams } from 'react-router-dom';
import HeroCard from './ui/HeroCard';
import TelemetrySection from './ui/TelemetrySection';
import TrendAnalysis from './ui/TrendAnalysis';
import HistoryTable from './ui/HistoryTable';
import { useSensorData } from '../hooks/useSensorData';
import { useSitesStatus } from '../hooks/useSitesStatus';
import { useSites } from '../hooks/useSites';
import './VerticalityDetail.css';


const VerticalityDetail: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const activeDeviceId = deviceId || 'E32_VER_WS';

  const { sites: dbSites, loading: sitesLoading } = useSites();
  const site = dbSites.find(s => s.code === activeDeviceId);

  const { latest, history } = useSensorData(5000, activeDeviceId);
  const liveStatuses = useSitesStatus(15000);
  const deviceStatus = liveStatuses.find(s => s.device_id === activeDeviceId);
  const isConnected = deviceStatus ? deviceStatus.live_status === 'online' : false;

  if (sitesLoading) {
    return (
      <div style={{
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--background)',
      }}>
        <div style={{
          width: '40px', height: '40px',
          border: '3px solid rgba(59, 130, 246, 0.2)',
          borderTop: '3px solid var(--accent-blue)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }} />
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <HeroCard latest={latest} isConnected={isConnected} site={site} deviceId={activeDeviceId} />
      <TelemetrySection latest={latest} isConnected={isConnected} site={site} />
      <TrendAnalysis history={history} />
      <HistoryTable history={history} />
    </div>
  );
};

export default VerticalityDetail;
