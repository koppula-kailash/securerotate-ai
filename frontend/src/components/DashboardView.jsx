import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import {
  Shield,
  Database,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Clock,
  RefreshCw,
  Zap,
  Bell,
  ArrowRight,
  ShieldCheck,
  RotateCw,
  Cpu,
  Mail,
  Sparkles,
  Check
} from 'lucide-react';
import { formatExactTimeSlot } from '../utils/timeFormatter';

export default function DashboardView({ onNavigate, onOpenAddCredential, onTriggerRotation, onRefreshData }) {
  const { user, role, canManageCredentials } = useAuth();
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const fetchStats = async (showLoading = true) => {
    try {
      if (showLoading && !stats) setIsLoading(true);
      const data = await apiService.getDashboardStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load dashboard stats:', err);
    } finally {
      if (showLoading) setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats(true);
    const interval = setInterval(() => {
      fetchStats(false);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSeedData = async (force = false) => {
    try {
      setIsSeeding(true);
      setActionMessage(null);
      const res = await apiService.seedDemoData(force);
      setActionMessage({ type: 'success', text: res.message || 'Demo databases populated successfully!' });
      await fetchStats(false);
      if (onRefreshData) onRefreshData();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to seed demo data' });
    } finally {
      setIsSeeding(false);
    }
  };

  const handleTriggerScan = async () => {
    try {
      setIsScanning(true);
      setActionMessage(null);
      const res = await apiService.triggerExpiryScan();
      setActionMessage({
        type: 'success',
        text: `Expiry Radar Scan complete: ${res.checked_credentials} credentials evaluated, ${res.notifications_created} alerts generated/auto-rotated.`,
      });
      await fetchStats(false);
      if (onRefreshData) onRefreshData();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to execute expiry scan' });
    } finally {
      setIsScanning(false);
    }
  };

  if (isLoading && !stats) {
    return (
      <div className="loading-container">
        <RefreshCw className="spinner text-cyan" size={32} />
        <p>Loading security telemetry & credential state...</p>
      </div>
    );
  }

  const total = stats?.total_databases || 0;
  const healthy = stats?.healthy || 0;
  const warning = stats?.warning || 0;
  const critical = stats?.critical || 0;
  const expired = stats?.expired || 0;
  const autoRotationCount = stats?.auto_rotation_count || 0;
  const upcomingRotations = stats?.upcoming_rotations || [];

  return (
    <div className="dashboard-container">
      {/* Welcome Banner */}
      <div className="dashboard-hero">
        <div className="hero-content">
          <h2>Welcome back, <span className="text-cyan">{user?.username}</span></h2>
          <p className="hero-description">
            Continuous AI-driven database credential monitoring, risk assessment, and zero-downtime automated rotation pipeline.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <div className="hero-role-pill">
              <ShieldCheck size={15} />
              <span>Active Session Role: <strong>{role}</strong></span>
            </div>
            <div className="hero-role-pill bg-cyan-950/60 border-cyan-700/60 text-cyan-300">
              <Cpu size={15} className="text-cyan-400" />
              <span>Auto-Rotation Active: <strong>{autoRotationCount} DBs</strong></span>
            </div>
          </div>
        </div>

        {/* Quick Actions Bar */}
        <div className="hero-actions">
          {canManageCredentials && (
            <button
              className="btn btn-primary"
              onClick={onOpenAddCredential}
            >
              <Database size={16} />
              <span>+ Add Database Credential</span>
            </button>
          )}

          <button
            className="btn btn-secondary"
            onClick={handleTriggerScan}
            disabled={isScanning}
          >
            <Bell size={16} />
            <span>{isScanning ? 'Scanning & Auto-Rotating...' : 'Run Expiry Scan'}</span>
          </button>

          {total === 0 && (
            <button
              className="btn btn-outline"
              onClick={() => handleSeedData(false)}
              disabled={isSeeding}
            >
              <Zap size={16} />
              <span>{isSeeding ? 'Populating...' : 'Seed 24 Demo DBs'}</span>
            </button>
          )}
        </div>
      </div>

      {actionMessage && (
        <div className={`alert-box alert-${actionMessage.type} flex items-center justify-between`}>
          <div className="flex items-center gap-2">
            {actionMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{actionMessage.text}</span>
          </div>
          <button className="alert-close" onClick={() => setActionMessage(null)}>✕</button>
        </div>
      )}

      {/* Metrics Cards Grid */}
      <div className="metrics-grid">
        <div className="metric-card metric-total" onClick={() => onNavigate('credentials')}>
          <div className="metric-header">
            <span className="metric-label">Managed Databases</span>
            <Database size={20} className="metric-icon" />
          </div>
          <div className="metric-value">{total}</div>
          <div className="metric-footer">
            <span>Across Environments</span>
            <ArrowRight size={14} />
          </div>
        </div>

        <div className="metric-card metric-healthy" onClick={() => onNavigate('credentials')}>
          <div className="metric-header">
            <span className="metric-label">Healthy (&gt;7 Days)</span>
            <CheckCircle2 size={20} className="metric-icon" />
          </div>
          <div className="metric-value">{healthy}</div>
          <div className="metric-footer">
            <span>Compliant credentials</span>
            <span className="metric-pct">{total ? Math.round((healthy / total) * 100) : 0}%</span>
          </div>
        </div>

        <div className="metric-card metric-warning" onClick={() => onNavigate('credentials')}>
          <div className="metric-header">
            <span className="metric-label">Warning (4-7 Days)</span>
            <Clock size={20} className="metric-icon" />
          </div>
          <div className="metric-value">{warning}</div>
          <div className="metric-footer">
            <span>Schedule rotation</span>
            <span className="metric-pct">{total ? Math.round((warning / total) * 100) : 0}%</span>
          </div>
        </div>

        <div className="metric-card metric-critical" onClick={() => onNavigate('credentials')}>
          <div className="metric-header">
            <span className="metric-label">Critical (1-3 Days)</span>
            <AlertTriangle size={20} className="metric-icon" />
          </div>
          <div className="metric-value">{critical}</div>
          <div className="metric-footer">
            <span>Urgent attention</span>
            <span className="metric-pct">{total ? Math.round((critical / total) * 100) : 0}%</span>
          </div>
        </div>

        <div className="metric-card metric-expired" onClick={() => onNavigate('credentials')}>
          <div className="metric-header">
            <span className="metric-label">Expired</span>
            <AlertOctagon size={20} className="metric-icon" />
          </div>
          <div className="metric-value">{expired}</div>
          <div className="metric-footer">
            <span>Rotation required</span>
            <span className="metric-pct">{total ? Math.round((expired / total) * 100) : 0}%</span>
          </div>
        </div>
      </div>

      {/* Urgent Rotation Radar Queue */}
      {upcomingRotations.length > 0 && (
        <div className="card mb-4 border border-amber-500/30 bg-slate-900/90">
          <div className="card-header flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-400" />
              <h3 className="font-semibold text-white">Urgent Rotation Queue ({upcomingRotations.length})</h3>
            </div>
            <span className="text-xs text-muted">Direct Actionable Rotation Pipeline</span>
          </div>
          <div className="p-3">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {upcomingRotations.map((item) => (
                <div key={item.id} className="p-3 bg-slate-950/80 rounded-lg border border-slate-800 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <strong className="text-sm text-cyan-300 font-semibold">{item.name}</strong>
                      <span className={`text-[11px] px-2 py-0.5 rounded font-bold ${item.days_remaining === 0 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : item.days_remaining <= 3 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-yellow-500/20 text-yellow-300'}`}>
                        {item.days_remaining === 0 ? 'EXPIRED' : `${item.days_remaining}d Left`}
                      </span>
                    </div>
                    <div className="text-xs text-muted mb-1">
                      {item.database_type} • {item.environment} • <span className="font-mono">{item.host}</span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                      <Mail size={11} className="text-cyan-400" />
                      <span>{item.owner_email}</span>
                    </div>
                  </div>

                  <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-[10px] text-muted">
                      {item.auto_rotation_enabled ? '🤖 Auto-Rotate ON' : 'Manual Rotation'}
                    </span>
                    {canManageCredentials && onTriggerRotation && (
                      <button
                        className="btn btn-xs btn-primary"
                        onClick={() => onTriggerRotation(item)}
                      >
                        <RotateCw size={12} />
                        <span>Rotate Password</span>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Grid of Telemetry & Activity */}
      <div className="dashboard-grid-2">
        {/* Expiry Health Distribution Bar */}
        <div className="card telemetry-card">
          <div className="card-header">
            <h3>Database Credential Health Distribution</h3>
            <span className="badge badge-info">{total} Endpoints</span>
          </div>
          <div className="card-body">
            <div className="distribution-bar-wrapper">
              <div className="distribution-bar">
                <div
                  className="bar-segment bar-healthy"
                  style={{ width: `${total ? (healthy / total) * 100 : 0}%` }}
                  title={`Healthy: ${healthy}`}
                />
                <div
                  className="bar-segment bar-warning"
                  style={{ width: `${total ? (warning / total) * 100 : 0}%` }}
                  title={`Warning: ${warning}`}
                />
                <div
                  className="bar-segment bar-critical"
                  style={{ width: `${total ? (critical / total) * 100 : 0}%` }}
                  title={`Critical: ${critical}`}
                />
                <div
                  className="bar-segment bar-expired"
                  style={{ width: `${total ? (expired / total) * 100 : 0}%` }}
                  title={`Expired: ${expired}`}
                />
              </div>
            </div>

            <div className="distribution-legend">
              <div className="legend-item"><span className="dot dot-healthy"></span> Healthy ({healthy})</div>
              <div className="legend-item"><span className="dot dot-warning"></span> Warning ({warning})</div>
              <div className="legend-item"><span className="dot dot-critical"></span> Critical ({critical})</div>
              <div className="legend-item"><span className="dot dot-expired"></span> Expired ({expired})</div>
            </div>

            <div className="system-health-banner mt-3">
              <h4>System Operational Posture</h4>
              <p>
                {expired > 0
                  ? '⚠️ Critical expired credentials detected. Immediate rotation required to prevent service disruption.'
                  : critical > 0
                  ? '⚡ Credentials approaching expiration within 72 hours. Trigger authorization and rotation sequence.'
                  : '✅ All database credentials within compliant lifecycle thresholds.'}
              </p>
            </div>
          </div>
        </div>

        {/* Recent Audit Log Feed */}
        <div className="card activity-card">
          <div className="card-header">
            <h3>Recent Security Audit Activity</h3>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('audit')}>
              View All Logs
            </button>
          </div>
          <div className="card-body p-0">
            {stats?.recent_activity?.length > 0 ? (
              <div className="activity-list">
                {stats.recent_activity.slice(0, 6).map((item) => {
                  const ts = formatExactTimeSlot(item.timestamp);
                  return (
                    <div key={item.id} className="activity-row">
                      <div className={`activity-status-dot dot-${(item.status || 'SUCCESS').toLowerCase()}`} />
                      <div className="activity-info">
                        <div className="activity-title">
                          <span className="activity-event">{item.event_type}</span>
                          <span className="activity-time flex items-center gap-1 font-mono text-[11px]">
                            <Clock size={11} className="text-cyan" />
                            <span>{ts.time}</span>
                            {ts.slot && <span className="text-[10px] text-cyan-300">({ts.slot})</span>}
                          </span>
                        </div>
                        <div className="activity-details">{item.details}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <p>No audit events recorded yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
