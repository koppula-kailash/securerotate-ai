import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Users, Plus, RefreshCw, UserCheck, UserX, Shield, Edit3, Trash2, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function UsersView() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [alert, setAlert] = useState(null);

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const data = await apiService.getUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to fetch users:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleDeactivate = async (user) => {
    if (!window.confirm(`Deactivate user account "${user.username}"?`)) return;
    try {
      await apiService.deactivateUser(user.id);
      setAlert({ type: 'success', text: `User "${user.username}" deactivated successfully.` });
      await fetchUsers();
    } catch (err) {
      setAlert({ type: 'error', text: err.message || 'Deactivation failed' });
    }
  };

  return (
    <div className="view-container">
      <div className="view-header">
        <div>
          <h2>User & Role-Based Access Control (RBAC)</h2>
          <p className="view-subtitle">
            Admin management console for provisioning accounts, assigning security roles, and auditing access.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-primary btn-sm" onClick={() => { setEditingUser(null); setIsModalOpen(true); }}>
            <Plus size={14} />
            <span>Provision User</span>
          </button>
          <button className="btn btn-secondary btn-sm" onClick={fetchUsers} disabled={isLoading}>
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
          </button>
        </div>
      </div>

      {alert && (
        <div className={`alert-box alert-${alert.type} mb-4`}>
          {alert.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span>{alert.text}</span>
          <button className="alert-close" onClick={() => setAlert(null)}>✕</button>
        </div>
      )}

      {/* Users Table */}
      <div className="card table-card">
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>Email Address</th>
                <th>Assigned Role</th>
                <th>Account Status</th>
                <th>Created At</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="7" className="text-center py-6">
                    <RefreshCw size={24} className="spinner text-cyan" />
                    <p className="mt-2">Loading user accounts...</p>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-6 text-muted">
                    No users registered.
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td className="font-mono text-xs">#{u.id}</td>
                    <td className="font-semibold">{u.username}</td>
                    <td className="text-muted text-sm">{u.email}</td>
                    <td>
                      <span className={`role-badge role-${(u.role || 'AUDITOR').toLowerCase()}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-status ${u.is_active ? 'badge-status-active' : 'badge-status-inactive'}`}>
                        {u.is_active ? 'Active' : 'Deactivated'}
                      </span>
                    </td>
                    <td className="text-xs text-muted">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="text-right">
                      <div className="action-buttons-group">
                        <button
                          className="btn-icon"
                          onClick={() => { setEditingUser(u); setIsModalOpen(true); }}
                          title="Edit user details / role"
                        >
                          <Edit3 size={15} />
                        </button>
                        {u.is_active && (
                          <button
                            className="btn-icon btn-icon-danger"
                            onClick={() => handleDeactivate(u)}
                            title="Deactivate user"
                          >
                            <Trash2 size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* User Form Modal */}
      {isModalOpen && (
        <UserFormModal
          isOpen={isModalOpen}
          initialData={editingUser}
          onClose={() => { setIsModalOpen(false); setEditingUser(null); }}
          onSuccess={() => {
            setIsModalOpen(false);
            setEditingUser(null);
            fetchUsers();
            setAlert({ type: 'success', text: editingUser ? 'User updated successfully' : 'New user created successfully' });
          }}
        />
      )}
    </div>
  );
}

function UserFormModal({ isOpen, initialData, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    username: initialData?.username || '',
    email: initialData?.email || '',
    password: '',
    role: initialData?.role || 'AUDITOR',
    is_active: initialData?.is_active !== undefined ? initialData.is_active : true,
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (initialData) {
        const payload = { ...formData };
        if (!payload.password) delete payload.password;
        await apiService.updateUser(initialData.id, payload);
      } else {
        if (!formData.password) throw new Error('Password is required for new accounts');
        await apiService.createUser(formData);
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
      <div className="modal-card">
        <div className="modal-header">
          <h3>{initialData ? `Edit User: ${initialData.username}` : 'Provision New User'}</h3>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {error && (
          <div className="alert-box alert-error mx-4 mt-4">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-4">
          <div className="form-group">
            <label>Username *</label>
            <input
              type="text"
              className="form-control"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>Email Address *</label>
            <input
              type="email"
              className="form-control"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <label>{initialData ? 'New Password (leave blank to retain current)' : 'Password *'}</label>
            <input
              type="password"
              className="form-control"
              placeholder="••••••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required={!initialData}
            />
          </div>

          <div className="form-group">
            <label>Role Assignment *</label>
            <select
              className="form-control"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            >
              <option value="AUDITOR">Auditor (Read Only)</option>
              <option value="DEVOPS">DevOps (Rotate / Manage Credentials)</option>
              <option value="ADMIN">Admin (Full Access & User Management)</option>
            </select>
          </div>

          {initialData && (
            <div className="form-group">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
                <span>Account Active Status</span>
              </label>
            </div>
          )}

          <div className="modal-actions mt-4">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              {isLoading ? 'Saving...' : initialData ? 'Update User' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
