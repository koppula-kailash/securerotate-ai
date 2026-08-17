import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { FileText, RefreshCw, Search, Filter, ShieldCheck, CheckCircle2, AlertCircle, Clock, Calendar } from 'lucide-react';
import { formatExactTimeSlot } from '../utils/timeFormatter';

export default function AuditView() {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState('ALL');

  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      const data = await apiService.getAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const eventTypes = ['ALL', 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'USER_REGISTERED', 'CREDENTIAL_CREATED', 'CREDENTIAL_UPDATED', 'CREDENTIAL_DELETED', 'ROTATION_SUCCESS', 'ROTATION_FAILED', 'NOTIFICATION_SENT', 'VERIFICATION_PASSED', 'VERIFICATION_FAILED', 'ROLLBACK_EXECUTED'];

  const filtered = logs.filter((log) => {
    const matchesSearch =
      (log.details || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.event_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.action || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesEvent = selectedEvent === 'ALL' || log.event_type === selectedEvent;

    return matchesSearch && matchesEvent;
  });

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Security Audit Trail & Compliance Log</h2>
          <p className="view-subtitle">
            Immutable application-layer security log tracking authentication events, vault changes, and exact rotation time slots.
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchLogs} disabled={isLoading}>
          <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
          <span>Refresh Logs</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search audit trail by event type, action, or details..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <Filter size={15} className="text-muted" />
          <select
            value={selectedEvent}
            onChange={(e) => setSelectedEvent(e.target.value)}
            className="filter-select"
          >
            {eventTypes.map((et) => (
              <option key={et} value={et}>{et === 'ALL' ? 'All Event Types' : et}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="card table-card">
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Log ID</th>
                <th>Exact Time Slot</th>
                <th>Event Type</th>
                <th>Action</th>
                <th>Status</th>
                <th>Credential / Context</th>
                <th>Event Details</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="7" className="text-center py-6">
                    <RefreshCw size={24} className="spinner text-cyan" />
                    <p className="mt-2">Loading immutable audit logs...</p>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-6 text-muted">
                    No audit records found matching the query.
                  </td>
                </tr>
              ) : (
                filtered.map((log) => {
                  const timeSlot = formatExactTimeSlot(log.timestamp || log.created_at);
                  const isSuccess = log.status === 'SUCCESS';
                  return (
                    <tr key={log.id}>
                      <td className="font-mono text-xs">#{log.id}</td>
                      <td>
                        <div className="flex flex-col gap-0.5">
                          <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-slate-200">
                            <Clock size={12} className="text-cyan" />
                            <span>{timeSlot.time}</span>
                            {timeSlot.slot && (
                              <span className="text-[10px] bg-cyan-950 text-cyan-300 px-1.5 py-0.2 rounded border border-cyan-800 font-mono">
                                Slot {timeSlot.slot}
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-muted flex items-center gap-2">
                            <span className="flex items-center gap-1">
                              <Calendar size={10} />
                              <span>{timeSlot.date}</span>
                            </span>
                            {timeSlot.relative && (
                              <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded border border-slate-700">
                                {timeSlot.relative}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="font-semibold text-xs text-cyan">{log.event_type}</span>
                      </td>
                      <td>
                        <span className="badge badge-outline text-xs">{log.action}</span>
                      </td>
                      <td>
                        <span className={`badge badge-status badge-status-${(log.status || 'SUCCESS').toLowerCase()}`}>
                          {log.status}
                        </span>
                      </td>
                      <td>
                        {log.credential_id ? (
                          <span className="text-xs font-mono">Cred #{log.credential_id}</span>
                        ) : (
                          <span className="text-xs text-muted">System / Auth</span>
                        )}
                      </td>
                      <td>
                        <div className="text-xs max-w-md break-words">{log.details}</div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
