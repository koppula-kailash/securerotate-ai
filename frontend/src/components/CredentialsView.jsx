import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { Database, Plus, Search, Filter, Key, RefreshCw, AlertTriangle, ShieldCheck, Trash2, Edit3, Eye, Clock, CheckCircle2, RotateCw } from 'lucide-react';

export default function CredentialsView({ onTriggerRotation, onRefreshData }) {
  const { role, canManageCredentials, isAdmin } = useAuth();
  const [credentials, setCredentials] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEnv, setSelectedEnv] = useState('ALL');
  const [selectedRisk, setSelectedRisk] = useState('ALL');

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingCred, setEditingCred] = useState(null);
  const [detailCred, setDetailCred] = useState(null);
  const [rotationCred, setRotationCred] = useState(null);
  const [rotationReason, setRotationReason] = useState('');
  const [actionAlert, setActionAlert] = useState(null);

  const fetchCredentials = async () => {
    try {
      setIsLoading(true);
      const data = await apiService.getCredentials();
      setCredentials(data);
    } catch (err) {
      console.error('Failed to fetch credentials:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCredentials();
  }, []);

  const handleDelete = async (cred) => {
    if (!window.confirm(`Are you sure you want to delete credential "${cred.name}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await apiService.deleteCredential(cred.id);
      setActionAlert({ type: 'success', text: `Credential "${cred.name}" deleted successfully.` });
      await fetchCredentials();
      if (onRefreshData) onRefreshData();
    } catch (err) {
      setActionAlert({ type: 'error', text: err.message || 'Failed to delete credential' });
    }
  };

  const handleRequestRotation = async (e) => {
    e.preventDefault();
    if (!rotationCred) return;
    try {
      await apiService.createRotationRequest(rotationCred.id, rotationReason);
      setActionAlert({
        type: 'success',
        text: `Rotation approval request submitted for "${rotationCred.name}". Admin authorization pending.`,
      });
      setRotationCred(null);
      setRotationReason('');
    } catch (err) {
      setActionAlert({ type: 'error', text: err.message || 'Failed to request rotation' });
    }
  };

  // Filtered credentials list
  const filtered = credentials.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.host.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.username.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesEnv = selectedEnv === 'ALL' || c.environment.toUpperCase() === selectedEnv.toUpperCase();
    const matchesRisk = selectedRisk === 'ALL' || (c.risk_level || 'LOW').toUpperCase() === selectedRisk.toUpperCase();

    return matchesSearch && matchesEnv && matchesRisk;
  });

  const getDaysRemaining = (expiresAt) => {
    if (!expiresAt) return null;
    let str = String(expiresAt);
    if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-')) {
      str = str + 'Z';
    }
    const exp = new Date(str);
    if (isNaN(exp.getTime())) return null;
    const now = new Date();
    const diffMs = exp.getTime() - now.getTime();
    if (diffMs <= 0) return 0;
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  return (
    <div className="view-container">
      {/* Header */}
      <div className="view-header">
        <div>
          <h2>Database Credential Vault</h2>
          <p className="view-subtitle">
            Authenticated vault with Fernet 256-bit encryption, live risk scoring, and zero-downtime rotation.
          </p>
        </div>
        {canManageCredentials && (
          <button
            className="btn btn-primary"
            onClick={() => { setEditingCred(null); setIsCreateModalOpen(true); }}
          >
            <Plus size={16} />
            <span>Add Database Credential</span>
          </button>
        )}
      </div>

      {actionAlert && (
        <div className={`alert-box alert-${actionAlert.type}`}>
          {actionAlert.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span>{actionAlert.text}</span>
          <button className="alert-close" onClick={() => setActionAlert(null)}>✕</button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            placeholder="Search credentials by database name, host, or user..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-group">
          <Filter size={15} className="text-muted" />
          <select value={selectedEnv} onChange={(e) => setSelectedEnv(e.target.value)} className="filter-select">
            <option value="ALL">All Environments</option>
            <option value="PRODUCTION">Production</option>
            <option value="STAGING">Staging</option>
            <option value="DEVELOPMENT">Development</option>
            <option value="TESTING">Testing</option>
          </select>

          <select value={selectedRisk} onChange={(e) => setSelectedRisk(e.target.value)} className="filter-select">
            <option value="ALL">All Risk Levels</option>
            <option value="LOW">Low Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="HIGH">High Risk</option>
            <option value="CRITICAL">Critical Risk</option>
          </select>
        </div>
      </div>

      {/* Credentials Table */}
      <div className="card table-card">
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Database & Engine</th>
                <th>Host & Endpoint</th>
                <th>Environment</th>
                <th>Privilege</th>
                <th>Expiry Proximity</th>
                <th>Risk Score</th>
                <th>Status</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="8" className="text-center py-6">
                    <RefreshCw size={24} className="spinner text-cyan" />
                    <p className="mt-2">Loading database vault records...</p>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-6 text-muted">
                    No database credentials matched your filters.
                  </td>
                </tr>
              ) : (
                filtered.map((c) => {
                  const days = getDaysRemaining(c.expires_at);
                  const riskLvl = (c.risk_level || 'LOW').toUpperCase();

                  return (
                    <tr key={c.id}>
                      {/* Name & DB Type */}
                      <td>
                        <div className="db-name-cell">
                          <div className="db-icon-wrap">
                            <Database size={16} className="text-cyan" />
                          </div>
                          <div>
                            <div className="font-semibold">{c.name}</div>
                            <div className="text-xs text-muted">{c.database_type} • {c.database_name}</div>
                          </div>
                        </div>
                      </td>

                      {/* Host & Port */}
                      <td>
                        <div className="text-sm font-mono">{c.host}:{c.port}</div>
                        <div className="text-xs text-muted">User: <strong className="text-slate-300">{c.username}</strong></div>
                        {c.owner_email && (
                          <div className="text-[11px] text-cyan-400 font-mono mt-0.5 flex items-center gap-1">
                            <span>📧 {c.owner_email}</span>
                          </div>
                        )}
                      </td>

                      {/* Environment */}
                      <td>
                        <span className={`badge badge-env badge-env-${c.environment.toLowerCase()}`}>
                          {c.environment}
                        </span>
                      </td>

                      {/* Privilege */}
                      <td>
                        <span className={`badge badge-priv badge-priv-${c.privilege_level.toLowerCase()}`}>
                          {c.privilege_level}
                        </span>
                      </td>

                      {/* Expiry */}
                      <td>
                        {days !== null ? (
                          <div className="expiry-cell">
                            <Clock size={13} className="text-muted" />
                            <span className={days <= 0 ? 'text-danger font-bold' : days <= 3 ? 'text-critical font-bold' : days <= 7 ? 'text-warning font-semibold' : 'text-success'}>
                              {days <= 0 ? 'Expired' : `${days} days`}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-muted">No expiry</span>
                        )}
                      </td>

                      {/* Risk Score & Level */}
                      <td>
                        <div className="risk-pill-wrapper">
                          <span className={`badge badge-risk badge-risk-${riskLvl.toLowerCase()}`}>
                            {riskLvl} ({c.risk_score !== null ? (c.risk_score * 100).toFixed(0) : 'N/A'})
                          </span>
                        </div>
                      </td>

                      {/* Status */}
                      <td>
                        <span className={`badge badge-status badge-status-${c.status.toLowerCase()}`}>
                          {c.status}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="text-right">
                        <div className="action-buttons-group">
                          {/* Details */}
                          <button
                            className="btn-icon"
                            onClick={() => setDetailCred(c)}
                            title="View impact & dependencies"
                          >
                            <Eye size={15} />
                          </button>

                          {/* Request Rotation / Rotate */}
                          {canManageCredentials && (
                            <button
                              className="btn-icon btn-icon-cyan"
                              onClick={() => onTriggerRotation ? onTriggerRotation(c) : setRotationCred(c)}
                              title="Trigger / Request Password Rotation"
                            >
                              <RotateCw size={15} />
                            </button>
                          )}

                          {/* Edit */}
                          {canManageCredentials && (
                            <button
                              className="btn-icon"
                              onClick={() => { setEditingCred(c); setIsCreateModalOpen(true); }}
                              title="Edit parameters"
                            >
                              <Edit3 size={15} />
                            </button>
                          )}

                          {/* Delete (Admin Only) */}
                          {isAdmin && (
                            <button
                              className="btn-icon btn-icon-danger"
                              onClick={() => handleDelete(c)}
                              title="Delete database record"
                            >
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create / Edit Credential Modal */}
      {isCreateModalOpen && (
        <CredentialFormModal
          isOpen={isCreateModalOpen}
          initialData={editingCred}
          onClose={() => { setIsCreateModalOpen(false); setEditingCred(null); }}
          onSuccess={() => {
            setIsCreateModalOpen(false);
            setEditingCred(null);
            fetchCredentials();
            if (onRefreshData) onRefreshData();
            setActionAlert({ type: 'success', text: editingCred ? 'Credential updated successfully' : 'New database credential registered successfully' });
          }}
        />
      )}

      {/* Rotation Request Modal */}
      {rotationCred && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Request Rotation Authorization</h3>
              <button className="modal-close-btn" onClick={() => setRotationCred(null)}>✕</button>
            </div>
            <form onSubmit={handleRequestRotation} className="p-4">
              <p className="text-sm text-muted mb-4">
                Submitting a formal rotation authorization request for <strong>{rotationCred.name}</strong> ({rotationCred.environment}).
              </p>
              <div className="form-group">
                <label>Rotation Justification / Reason *</label>
                <textarea
                  className="form-control"
                  rows="3"
                  placeholder="e.g., Scheduled 90-day security policy compliance rotation or emergency leak remediation."
                  value={rotationReason}
                  onChange={(e) => setRotationReason(e.target.value)}
                  required
                />
              </div>
              <div className="modal-actions mt-4">
                <button type="button" className="btn btn-ghost" onClick={() => setRotationCred(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary">
                  <ShieldCheck size={16} />
                  <span>Submit for Lead Authorization</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Detail Drawer Modal */}
      {detailCred && (
        <CredentialDetailModal
          credential={detailCred}
          onClose={() => setDetailCred(null)}
        />
      )}
    </div>
  );
}

// Modal subcomponent for creating/editing credential
function CredentialFormModal({ isOpen, initialData, onClose, onSuccess }) {
  const { user } = useAuth();
  
  // Calculate default 90 days date string (YYYY-MM-DD)
  const getDefaultExpiry = (days = 90) => {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString().substring(0, 10);
  };

  const [formData, setFormData] = useState({
    name: initialData?.name || '',
    database_type: initialData?.database_type || 'MySQL',
    host: initialData?.host || '127.0.0.1',
    port: initialData?.port || 3306,
    database_name: initialData?.database_name || '',
    username: initialData?.username || '',
    password: '',
    environment: initialData?.environment || 'Production',
    privilege_level: initialData?.privilege_level || 'HIGH',
    expires_at: initialData?.expires_at ? initialData.expires_at.substring(0, 10) : getDefaultExpiry(90),
    auto_rotation_enabled: initialData?.auto_rotation_enabled || false,
    owner_email: initialData?.owner_email || user?.email || '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const setExpiryDays = (days) => {
    setFormData({ ...formData, expires_at: getDefaultExpiry(days) });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (!formData.owner_email || !formData.owner_email.trim()) {
        throw new Error('Please provide a valid user/owner email address to receive rotation notifications.');
      }

      if (!formData.expires_at) {
        throw new Error('Please select or specify a credential expiration date.');
      }

      const expiryDateStr = formData.expires_at.includes('T')
        ? formData.expires_at
        : `${formData.expires_at}T23:59:59Z`;

      const payload = {
        ...formData,
        port: parseInt(formData.port, 10),
        expires_at: new Date(expiryDateStr).toISOString(),
      };

      if (!initialData && !formData.password) {
        throw new Error('Password is required when registering a new database credential.');
      }

      if (initialData) {
        if (!payload.password) delete payload.password;
        await apiService.updateCredential(initialData.id, payload);
      } else {
        await apiService.createCredential(payload);
      }
      onSuccess();
    } catch (err) {
      setError(err.message || 'Operation failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card modal-card-lg">
        <div className="modal-header">
          <h3>{initialData ? `Edit Credential: ${initialData.name}` : 'Register Target Database Credential'}</h3>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {error && (
          <div className="alert-box alert-error mx-4 mt-4">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-4 grid-form">
          <div className="form-group">
            <label>Credential Identifier Name *</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g., Payment Gateway DB"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Database Engine *</label>
            <select
              className="form-control"
              value={formData.database_type}
              onChange={(e) => setFormData({ ...formData, database_type: e.target.value })}
            >
              <option value="MySQL">MySQL (aiomysql)</option>
              <option value="PostgreSQL">PostgreSQL</option>
              <option value="MongoDB">MongoDB</option>
            </select>
          </div>

          <div className="form-group">
            <label>Host / IP Address *</label>
            <input
              type="text"
              className="form-control"
              placeholder="127.0.0.1 or db.internal.local"
              value={formData.host}
              onChange={(e) => setFormData({ ...formData, host: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Port *</label>
            <input
              type="number"
              className="form-control"
              value={formData.port}
              onChange={(e) => setFormData({ ...formData, port: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Database Schema Name *</label>
            <input
              type="text"
              className="form-control"
              placeholder="production_payments"
              value={formData.database_name}
              onChange={(e) => setFormData({ ...formData, database_name: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>DB Username *</label>
            <input
              type="text"
              className="form-control"
              placeholder="db_service_user"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>{initialData ? 'New Password (leave blank to keep current)' : 'Password *'}</label>
            <input
              type="password"
              className="form-control"
              placeholder="••••••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required={!initialData}
            />
            <span className="text-xs text-muted">Secured with Fernet URL-safe base64 authenticated encryption</span>
          </div>

          <div className="form-group">
            <label>User / Owner Email for Notifications *</label>
            <input
              type="email"
              className="form-control"
              placeholder="e.g. user@enterprise.io or your email"
              value={formData.owner_email}
              onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
              required
            />
            <span className="text-xs text-muted">Rotation alerts and post-rotation confirmations are sent to this address</span>
          </div>

          <div className="form-group">
            <label>Deployment Environment *</label>
            <select
              className="form-control"
              value={formData.environment}
              onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
            >
              <option value="Production">Production</option>
              <option value="Staging">Staging</option>
              <option value="Development">Development</option>
              <option value="Testing">Testing</option>
            </select>
          </div>

          <div className="form-group">
            <label>Privilege Level *</label>
            <select
              className="form-control"
              value={formData.privilege_level}
              onChange={(e) => setFormData({ ...formData, privilege_level: e.target.value })}
            >
              <option value="LOW">LOW (Read-Only / Reporting)</option>
              <option value="MEDIUM">MEDIUM (Read / Write Application)</option>
              <option value="HIGH">HIGH (Schema Alteration / Migrations)</option>
              <option value="ADMIN">ADMIN (Superuser / Full DBA)</option>
            </select>
          </div>

          <div className="form-group col-span-2">
            <div className="flex items-center justify-between mb-1">
              <label className="mb-0">Credential Expiry Date *</label>
              <div className="flex gap-1">
                <button type="button" className="btn btn-xs btn-outline" onClick={() => setExpiryDays(30)}>+30 Days</button>
                <button type="button" className="btn btn-xs btn-outline" onClick={() => setExpiryDays(60)}>+60 Days</button>
                <button type="button" className="btn btn-xs btn-outline" onClick={() => setExpiryDays(90)}>+90 Days</button>
                <button type="button" className="btn btn-xs btn-outline" onClick={() => setExpiryDays(180)}>+180 Days</button>
                <button type="button" className="btn btn-xs btn-outline" onClick={() => setExpiryDays(365)}>+1 Year</button>
              </div>
            </div>
            <input
              type="date"
              className="form-control"
              value={formData.expires_at}
              onChange={(e) => setFormData({ ...formData, expires_at: e.target.value })}
              required
            />
            <span className="text-xs text-muted">Defines rotation lifecycle thresholds and triggers automated expiry radar</span>
          </div>

          <div className="form-group col-span-2 p-3 bg-slate-900/60 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="font-semibold text-sm text-cyan-400">🤖 Enable AI Auto-Rotation</div>
              <div className="text-xs text-muted">Automatically rotates and verifies password when credential enters critical expiry (≤ 1 day).</div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={formData.auto_rotation_enabled}
                onChange={(e) => setFormData({ ...formData, auto_rotation_enabled: e.target.checked })}
              />
              <span className="slider round"></span>
            </label>
          </div>

          <div className="modal-actions col-span-2 mt-4">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              {isLoading ? 'Saving...' : initialData ? 'Update Credential' : 'Save & Encrypt Credential'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Modal subcomponent for viewing credential dependencies & impact
function CredentialDetailModal({ credential, onClose }) {
  const [impact, setImpact] = useState(null);
  const [dependencies, setDependencies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [imp, deps] = await Promise.all([
          apiService.getCredentialImpact(credential.id).catch(() => null),
          apiService.getCredentialDependencies(credential.id).catch(() => []),
        ]);
        setImpact(imp);
        setDependencies(deps || []);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [credential]);

  return (
    <div className="modal-backdrop">
      <div className="modal-card modal-card-lg">
        <div className="modal-header">
          <div>
            <h3>Security & Dependency Telemetry: {credential.name}</h3>
            <p className="text-xs text-muted">{credential.host}:{credential.port} • {credential.database_name}</p>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="p-4">
          <div className="grid-2-col mb-4">
            <div className="stat-box">
              <span className="stat-label">Risk Evaluation</span>
              <div className="stat-val text-cyan">
                {credential.risk_level || 'LOW'} ({credential.risk_score !== null ? (credential.risk_score * 100).toFixed(0) : 'N/A'}/100)
              </div>
            </div>
            <div className="stat-box">
              <span className="stat-label">Impact Severity</span>
              <div className="stat-val text-warning">
                {impact?.overall_impact_level || 'LOW'} ({impact?.maximum_impact_score !== undefined ? (impact.maximum_impact_score * 100).toFixed(0) : '0'}%)
              </div>
            </div>
          </div>

          <h4 className="font-semibold mb-2">Downstream Dependent Services ({dependencies.length})</h4>
          {loading ? (
            <p className="text-muted">Analyzing downstream services...</p>
          ) : dependencies.length === 0 ? (
            <p className="text-muted text-sm">No direct downstream microservices mapped to this database credential.</p>
          ) : (
            <div className="dependencies-list">
              {dependencies.map((d) => (
                <div key={d.id} className="dependency-item">
                  <div>
                    <div className="font-medium text-sm">{d.service_name}</div>
                    <div className="text-xs text-muted">{d.service_type} • {d.environment}</div>
                  </div>
                  <span className={`badge badge-priv badge-priv-${d.criticality.toLowerCase()}`}>
                    {d.criticality} ({(d.impact_score * 100).toFixed(0)}%)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
