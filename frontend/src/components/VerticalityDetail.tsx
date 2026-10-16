import React from 'react';
import { useParams } from 'react-router-dom';
import HeroCard from './ui/HeroCard';
import TelemetrySection from './ui/TelemetrySection';
import TrendAnalysis from './ui/TrendAnalysis';
import HistoryTable from './ui/HistoryTable';
import FatigueMatrixCard from './FatigueMatrixCard';
import { useSensorData } from '../hooks/useSensorData';
import { useSitesStatus } from '../hooks/useSitesStatus';
import { useSites } from '../hooks/useSites';
import './VerticalityDetail.css';


const VerticalityDetail: React.FC = () => {
  const { deviceId } = useParams<{ deviceId: string }>();
  const activeDeviceId = deviceId || 'E32_VER_WEES';

  const { sites: dbSites, loading: sitesLoading } = useSites();
  const isWeesOrWs = (c?: string) => c === 'E32_VER_WS' || c === 'E32_VER_WEES' || c === '20TS10B1529';
  const site = dbSites.find(s => s.code === activeDeviceId || (isWeesOrWs(activeDeviceId) && isWeesOrWs(s.code)));

  const { latest, history } = useSensorData(5000, activeDeviceId);
  const liveStatuses = useSitesStatus(15000);
  const deviceStatus = liveStatuses.find(s => s.device_id === activeDeviceId || (isWeesOrWs(activeDeviceId) && isWeesOrWs(s.device_id)));
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
      <FatigueMatrixCard />
      <TelemetrySection latest={latest} isConnected={isConnected} site={site} />
      <TrendAnalysis history={history} />
      <HistoryTable history={history} />
    </div>
  );
};

export default VerticalityDetail;
