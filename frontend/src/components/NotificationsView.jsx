import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Bell, RefreshCw, AlertTriangle, AlertOctagon, Info, CheckCircle2, Clock, Mail } from 'lucide-react';
import { formatExactTimeSlot } from '../utils/timeFormatter';

export default function NotificationsView() {
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);

  const fetchNotifications = async () => {
    try {
      setIsLoading(true);
      const data = await apiService.getNotifications();
      setNotifications(data);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleRunScan = async () => {
    try {
      setIsScanning(true);
      setScanResult(null);
      const res = await apiService.triggerExpiryScan();
      setScanResult({
        type: 'success',
        text: `7-Day Expiry Scan Complete: Evaluated ${res.checked_credentials} credentials and created ${res.notifications_created} notifications.`,
      });
      await fetchNotifications();
    } catch (err) {
      setScanResult({ type: 'error', text: err.message || 'Scan execution failed' });
    } finally {
      setIsScanning(false);
    }
  };

  const getAlertIcon = (type) => {
    switch (type) {
      case 'CRITICAL_WARNING':
      case 'EXPIRED':
      case 'ROTATION_FAILED':
        return <AlertOctagon className="text-danger" size={20} />;
      case 'HIGH_RISK_WARNING':
        return <AlertTriangle className="text-critical" size={20} />;
      case 'ROTATION_SUCCESS':
        return <CheckCircle2 className="text-success" size={20} />;
      case 'EXPIRY_WARNING':
        return <Clock className="text-warning" size={20} />;
      default:
        return <Info className="text-cyan" size={20} />;
    }
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Alert Notifications & Expiry Radar</h2>
          <p className="view-subtitle">
            Automated notification feed delivering instant rotation alerts and expiry warnings to registered owner mailboxes.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-primary btn-sm" onClick={handleRunScan} disabled={isScanning}>
            <Bell size={14} className={isScanning ? 'spinner' : ''} />
            <span>{isScanning ? 'Scanning DBs...' : 'Scan 7-Day Expiries Now'}</span>
          </button>
          <button className="btn btn-secondary btn-sm" onClick={fetchNotifications} disabled={isLoading}>
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
          </button>
        </div>
      </div>

      {scanResult && (
        <div className={`alert-box alert-${scanResult.type} mb-4`}>
          {scanResult.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span>{scanResult.text}</span>
          <button className="alert-close" onClick={() => setScanResult(null)}>✕</button>
        </div>
      )}

      {/* Notifications List */}
      <div className="notifications-container">
        {isLoading ? (
          <div className="loading-container">
            <RefreshCw size={24} className="spinner text-cyan" />
            <p>Loading notification feed...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="card empty-card text-center py-10">
            <Bell size={36} className="text-muted mx-auto mb-2" />
            <h3>No Active Alerts</h3>
            <p className="text-muted text-sm">
              All credentials are currently within safe thresholds, or run an on-demand scan using the button above.
            </p>
          </div>
        ) : (
          <div className="notifications-grid">
            {notifications.map((n) => {
              const ts = formatExactTimeSlot(n.sent_at || n.created_at);
              return (
                <div key={n.id} className="notification-card">
                  <div className="notification-icon-wrap">
                    {getAlertIcon(n.notification_type)}
                  </div>
                  <div className="notification-content">
                    <div className="notification-header">
                      <h4 className="notification-title">{n.title}</h4>
                      <span className={`badge badge-risk badge-risk-${(n.risk_level || 'MEDIUM').toLowerCase()}`}>
                        {n.risk_level || 'INFO'}
                      </span>
                    </div>
                    <p className="notification-msg">{n.message}</p>
                    <div className="notification-meta">
                      <span className="flex items-center gap-1 text-cyan-400">
                        <Mail size={12} />
                        <span>Recipient: <strong>{n.recipient}</strong></span>
                      </span>
                      <span>Status: <strong className="text-success">{n.status}</strong></span>
                      <span className="flex items-center gap-1 font-mono text-[11px]">
                        <Clock size={11} className="text-cyan" />
                        <span>{ts.date} {ts.time}</span>
                        {ts.relative && <span className="text-muted">({ts.relative})</span>}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
