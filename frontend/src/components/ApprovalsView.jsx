import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { RefreshCw, CheckCircle2, XCircle, Clock, ShieldCheck, AlertCircle, Play } from 'lucide-react';

export default function ApprovalsView({ onExecuteRotation }) {
  const { role, isAdmin } = useAuth();
  const [approvals, setApprovals] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [rejectingApproval, setRejectingApproval] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [alert, setAlert] = useState(null);

  const fetchApprovals = async () => {
    try {
      setIsLoading(true);
      const data = await apiService.getApprovals();
      setApprovals(data);
    } catch (err) {
      console.error('Failed to fetch approvals:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleApprove = async (approval) => {
    try {
      await apiService.approveRotationRequest(approval.id);
      setAlert({ type: 'success', text: `Rotation request #${approval.id} for credential #${approval.credential_id} APPROVED.` });
      await fetchApprovals();
    } catch (err) {
      setAlert({ type: 'error', text: err.message || 'Approval failed' });
    }
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!rejectingApproval) return;
    try {
      await apiService.rejectRotationRequest(rejectingApproval.id, rejectionReason);
      setAlert({ type: 'success', text: `Rotation request #${rejectingApproval.id} REJECTED.` });
      setRejectingApproval(null);
      setRejectionReason('');
      await fetchApprovals();
    } catch (err) {
      setAlert({ type: 'error', text: err.message || 'Rejection failed' });
    }
  };

  const handleExecute = async (approval) => {
    try {
      const cred = await apiService.getCredentialById(approval.credential_id);
      if (onExecuteRotation) onExecuteRotation(cred);
    } catch {
      if (onExecuteRotation) onExecuteRotation({ id: approval.credential_id, name: `Credential #${approval.credential_id}` });
    }
  };

  const filtered = approvals.filter((a) => {
    if (selectedStatus === 'ALL') return true;
    return a.status.toUpperCase() === selectedStatus.toUpperCase();
  });

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>Rotation Authorization Workflows</h2>
          <p className="view-subtitle">
            Human-in-the-loop authorization pipeline enforcing dual-custody verification before password modification.
          </p>
        </div>
      </div>

      {alert && (
        <div className={`alert-box alert-${alert.type}`}>
          {alert.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{alert.text}</span>
          <button className="alert-close" onClick={() => setAlert(null)}>✕</button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="filter-bar">
        <div className="auth-tabs mb-0">
          {['ALL', 'PENDING', 'APPROVED', 'REJECTED'].map((st) => (
            <button
              key={st}
              className={`auth-tab ${selectedStatus === st ? 'active' : ''}`}
              onClick={() => setSelectedStatus(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Approvals Table */}
      <div className="card table-card">
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Credential ID</th>
                <th>Risk Evaluation</th>
                <th>Impact Score</th>
                <th>Status</th>
                <th>Justification / Reason</th>
                <th>Requested At</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="8" className="text-center py-6">
                    <RefreshCw size={24} className="spinner text-cyan" />
                    <p className="mt-2">Loading authorization workflows...</p>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center py-6 text-muted">
                    No rotation requests found under the selected filter.
                  </td>
                </tr>
              ) : (
                filtered.map((a) => {
                  const isPending = a.status === 'PENDING';
                  const isApproved = a.status === 'APPROVED';

                  return (
                    <tr key={a.id}>
                      <td className="font-mono font-semibold">#{a.id}</td>
                      <td>
                        <span className="font-semibold text-cyan">Credential #{a.credential_id}</span>
                      </td>
                      <td>
                        <span className={`badge badge-risk badge-risk-${(a.risk_level || 'LOW').toLowerCase()}`}>
                          {a.risk_level || 'LOW'} ({a.risk_score !== null ? (a.risk_score * 100).toFixed(0) : '0'})
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-priv badge-priv-${(a.impact_level || 'MEDIUM').toLowerCase()}`}>
                          {a.impact_level || 'MEDIUM'} ({a.impact_score !== null ? (a.impact_score * 100).toFixed(0) : '0'}%)
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-status badge-status-${a.status.toLowerCase()}`}>
                          {a.status}
                        </span>
                      </td>
                      <td>
                        <div className="text-sm max-w-xs truncate" title={a.reason}>
                          {a.reason || 'No justification provided'}
                        </div>
                        {a.rejection_reason && (
                          <div className="text-xs text-danger mt-1">
                            Rejection: {a.rejection_reason}
                          </div>
                        )}
                      </td>
                      <td className="text-xs text-muted">
                        {new Date(a.requested_at).toLocaleString()}
                      </td>
                      <td className="text-right">
                        <div className="action-buttons-group">
                          {isPending && isAdmin && (
                            <>
                              <button
                                className="btn btn-xs btn-success"
                                onClick={() => handleApprove(a)}
                                title="Authorize password rotation"
                              >
                                <CheckCircle2 size={13} />
                                <span>Approve</span>
                              </button>
                              <button
                                className="btn btn-xs btn-danger"
                                onClick={() => setRejectingApproval(a)}
                                title="Reject rotation request"
                              >
                                <XCircle size={13} />
                                <span>Reject</span>
                              </button>
                            </>
                          )}

                          {isApproved && (
                            <button
                              className="btn btn-xs btn-primary"
                              onClick={() => handleExecute(a)}
                              title="Execute 5-step atomic rotation"
                            >
                              <Play size={13} />
                              <span>Execute Rotation</span>
                            </button>
                          )}

                          {!isPending && !isApproved && (
                            <span className="text-xs text-muted">Archived</span>
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

      {/* Reject Reason Modal */}
      {rejectingApproval && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Reject Rotation Authorization #{rejectingApproval.id}</h3>
              <button className="modal-close-btn" onClick={() => setRejectingApproval(null)}>✕</button>
            </div>
            <form onSubmit={handleReject} className="p-4">
              <div className="form-group">
                <label>Rejection Reason / Required Remediation *</label>
                <textarea
                  className="form-control"
                  rows="3"
                  placeholder="Explain why this rotation request cannot be authorized at this time..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  required
                />
              </div>
              <div className="modal-actions mt-4">
                <button type="button" className="btn btn-ghost" onClick={() => setRejectingApproval(null)}>Cancel</button>
                <button type="submit" className="btn btn-danger">Confirm Rejection</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
