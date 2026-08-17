import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Lock, Mail, User, Key, AlertCircle, CheckCircle2, X, Eye, EyeOff } from 'lucide-react';

export default function AuthModal({ isOpen, onClose }) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('AUDITOR');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setIsLoading(true);

    try {
      if (mode === 'login') {
        await login(username || email, password);
        onClose();
      } else {
        await register(username, email, password, role);
        setSuccessMsg('Account created successfully! Logging you in...');
        setTimeout(() => {
          onClose();
        }, 1000);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoFill = (demoRole) => {
    const creds = {
      ADMIN: { u: 'admin', p: 'Admin123!' },
      DEVOPS: { u: 'devops', p: 'Devops123!' },
      AUDITOR: { u: 'auditor', p: 'Auditor123!' },
    };
    const c = creds[demoRole];
    if (c) {
      setMode('login');
      setUsername(c.u);
      setPassword(c.p);
      setError('');
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card auth-modal">
        <div className="modal-header">
          <div className="auth-brand">
            <div className="auth-brand-icon">
              <Shield size={24} className="text-cyan" />
            </div>
            <div>
              <h3>{mode === 'login' ? 'Sign In to SecureRotate' : 'Create an Account'}</h3>
              <p className="modal-subtitle">Enterprise RBAC & Authenticated Vault Access</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Demo Quick-Fill Buttons */}
        <div className="demo-credentials-banner">
          <div className="demo-title">⚡ Instant Demo Sign-In:</div>
          <div className="demo-buttons">
            <button
              type="button"
              className="btn btn-outline-admin btn-xs"
              onClick={() => handleDemoFill('ADMIN')}
            >
              👑 Admin (Admin123!)
            </button>
            <button
              type="button"
              className="btn btn-outline-devops btn-xs"
              onClick={() => handleDemoFill('DEVOPS')}
            >
              🛠️ DevOps (Devops123!)
            </button>
            <button
              type="button"
              className="btn btn-outline-auditor btn-xs"
              onClick={() => handleDemoFill('AUDITOR')}
            >
              🔍 Auditor (Auditor123!)
            </button>
          </div>
        </div>

        {/* Auth Mode Toggle */}
        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError(''); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError(''); }}
          >
            Register Account
          </button>
        </div>

        {error && (
          <div className="alert-box alert-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="alert-box alert-success">
            <CheckCircle2 size={16} />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label>Username / Email</label>
            <div className="input-with-icon">
              <User size={16} className="input-icon" />
              <input
                type="text"
                placeholder={mode === 'login' ? 'admin or admin@securerotate.local' : 'Enter username'}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
            </div>
          </div>

          {mode === 'register' && (
            <>
              <div className="form-group">
                <label>Email Address</label>
                <div className="input-with-icon">
                  <Mail size={16} className="input-icon" />
                  <input
                    type="email"
                    placeholder="user@securerotate.local"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Initial Role Assignment</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="form-control"
                >
                  <option value="AUDITOR">Auditor (Read-Only & Compliance)</option>
                  <option value="DEVOPS">DevOps (Credential & Rotation Management)</option>
                  <option value="ADMIN">Admin (Full Administrative Access)</option>
                </select>
              </div>
            </>
          )}

          <div className="form-group">
            <label>Password</label>
            <div className="input-with-icon">
              <Lock size={16} className="input-icon" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="input-action-btn"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {mode === 'register' && (
              <p className="input-hint">Minimum 6 characters with secure Argon2 hashing.</p>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block btn-lg"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="spinner-text">Authenticating...</span>
            ) : mode === 'login' ? (
              <>
                <Key size={16} />
                <span>Sign In Securely</span>
              </>
            ) : (
              <>
                <Shield size={16} />
                <span>Create Verified Account</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
