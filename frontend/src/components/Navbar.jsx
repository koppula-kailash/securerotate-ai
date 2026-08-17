import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, User, LogOut, KeyRound, CheckCircle2, AlertTriangle, Users, Bell, FileText, RefreshCw } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, onOpenAuthModal, systemStatus = 'HEALTHY' }) {
  const { user, role, isAuthenticated, logout, switchDemoRole } = useAuth();

  const getStatusBadge = () => {
    switch (systemStatus) {
      case 'CRITICAL':
        return <span className="badge badge-critical"><AlertTriangle size={13} /> CRITICAL AT RISK</span>;
      case 'WARNING':
        return <span className="badge badge-warning"><AlertTriangle size={13} /> EXPIRIES PENDING</span>;
      default:
        return <span className="badge badge-healthy"><CheckCircle2 size={13} /> ALL SYSTEMS OPERATIONAL</span>;
    }
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Shield },
    { id: 'credentials', label: 'Vault & DBs', icon: KeyRound },
    { id: 'approvals', label: 'Approvals', icon: RefreshCw },
    { id: 'notifications', label: 'Alerts', icon: Bell },
    { id: 'audit', label: 'Audit Trail', icon: FileText },
  ];

  if (role === 'ADMIN') {
    navItems.push({ id: 'users', label: 'Users & RBAC', icon: Users });
  }

  return (
    <header className="navbar">
      <div className="navbar-container">
        {/* Brand */}
        <div className="navbar-brand" onClick={() => setActiveTab('dashboard')}>
          <div className="brand-icon">
            <Shield size={22} className="text-cyan" />
          </div>
          <div>
            <span className="brand-title">SecureRotate<span className="text-cyan">.AI</span></span>
            <div className="brand-subtitle">Autonomous Credential Vault & Zero-Downtime Rotation</div>
          </div>
        </div>

        {/* System Health Badge */}
        <div className="nav-status-wrapper">
          {getStatusBadge()}
        </div>

        {/* Navigation Tabs */}
        {isAuthenticated && (
          <nav className="navbar-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  className={`nav-link ${isActive ? 'active' : ''}`}
                  onClick={() => setActiveTab(item.id)}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        )}

        {/* User / Auth Controls */}
        <div className="navbar-actions">
          {isAuthenticated ? (
            <div className="user-profile-widget">
              {/* Quick demo role switcher */}
              <div className="role-switcher">
                <span className="role-switcher-label">Demo Role:</span>
                <select
                  value={role}
                  onChange={(e) => switchDemoRole(e.target.value)}
                  className="role-select"
                  title="Switch between demo accounts for RBAC evaluation"
                >
                  <option value="ADMIN">Admin (Full Access)</option>
                  <option value="DEVOPS">DevOps (Rotate/Add)</option>
                  <option value="AUDITOR">Auditor (Read Only)</option>
                </select>
              </div>

              {/* User Pill */}
              <div className="user-pill">
                <User size={15} className="text-cyan" />
                <span className="user-name">{user.username}</span>
                <span className={`role-badge role-${role.toLowerCase()}`}>{role}</span>
              </div>

              {/* Logout */}
              <button
                className="btn btn-ghost btn-sm"
                onClick={logout}
                title="Sign out of current session"
              >
                <LogOut size={15} />
                <span>Logout</span>
              </button>
            </div>
          ) : (
            <button className="btn btn-primary btn-sm" onClick={onOpenAuthModal}>
              <User size={15} />
              <span>Sign In / Register</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
