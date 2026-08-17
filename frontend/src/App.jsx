import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';
import DashboardView from './components/DashboardView';
import CredentialsView from './components/CredentialsView';
import ApprovalsView from './components/ApprovalsView';
import NotificationsView from './components/NotificationsView';
import AuditView from './components/AuditView';
import UsersView from './components/UsersView';
import RotationModal from './components/RotationModal';
import { Shield, Lock, KeyRound, CheckCircle2, ArrowRight } from 'lucide-react';

function AppContent() {
  const { isAuthenticated, isLoading, role } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [rotationTargetCred, setRotationTargetCred] = useState(null);
  const [isRotationModalOpen, setIsRotationModalOpen] = useState(false);

  const [refreshCounter, setRefreshCounter] = useState(0);

  const handleOpenRotation = (cred) => {
    setRotationTargetCred(cred);
    setIsRotationModalOpen(true);
  };

  const handleRotationSuccess = () => {
    setRefreshCounter((prev) => prev + 1);
  };

  if (isLoading) {
    return (
      <div className="full-screen-loader">
        <div className="brand-icon pulse">
          <Shield size={36} className="text-cyan" />
        </div>
        <h3 className="mt-4">Initializing SecureRotate AI...</h3>
        <p className="text-muted text-sm">Authenticating encrypted token session</p>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="main-content">
        {!isAuthenticated ? (
          /* Unauthenticated Landing / Call to Action */
          <div className="unauth-landing">
            <div className="landing-card">
              <div className="landing-shield">
                <Shield size={48} className="text-cyan" />
              </div>
              <h1>SecureRotate<span className="text-cyan">.AI</span></h1>
              <p className="landing-lead">
                Enterprise Autonomous Database Credential Vault, AI Risk Prediction, and Zero-Downtime Atomic Rotation System.
              </p>

              <div className="feature-badges">
                <span className="feature-pill">🔐 Fernet 256-bit Authenticated Vault</span>
                <span className="feature-pill">⚡ 5-Step Zero-Downtime Rotation</span>
                <span className="feature-pill">🛡️ Strict Role-Based Access Control</span>
                <span className="feature-pill">🤖 AI Expiry & Downtime Risk Engine</span>
              </div>

              <div className="landing-actions mt-8">
                <button
                  className="btn btn-primary btn-lg"
                  onClick={() => setIsAuthModalOpen(true)}
                >
                  <KeyRound size={18} />
                  <span>Access Secure Vault</span>
                  <ArrowRight size={16} />
                </button>
              </div>

              <div className="landing-demo-hint">
                <span>Demo Accounts Available:</span>
                <code>Admin (Admin123!)</code> • <code>DevOps (Devops123!)</code> • <code>Auditor (Auditor123!)</code>
              </div>
            </div>
          </div>
        ) : (
          /* Authenticated Tab Views */
          <div className="tab-view-wrapper">
            {activeTab === 'dashboard' && (
              <DashboardView
                key={`dash-${refreshCounter}`}
                onNavigate={(tab) => setActiveTab(tab)}
                onOpenAddCredential={() => setActiveTab('credentials')}
                onTriggerRotation={handleOpenRotation}
                onRefreshData={handleRotationSuccess}
              />
            )}

            {activeTab === 'credentials' && (
              <CredentialsView
                key={`cred-${refreshCounter}`}
                onTriggerRotation={handleOpenRotation}
                onRefreshData={handleRotationSuccess}
              />
            )}

            {activeTab === 'approvals' && (
              <ApprovalsView
                key={`appr-${refreshCounter}`}
                onExecuteRotation={handleOpenRotation}
              />
            )}

            {activeTab === 'notifications' && (
              <NotificationsView key={`notif-${refreshCounter}`} />
            )}

            {activeTab === 'audit' && (
              <AuditView key={`audit-${refreshCounter}`} />
            )}

            {activeTab === 'users' && role === 'ADMIN' && (
              <UsersView key={`users-${refreshCounter}`} />
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <span>🛡️ SecureRotate AI • Enterprise Zero-Downtime Credential Vault</span>
          <span className="footer-status">🔒 Cryptographically Verified • Argon2 & Fernet Authenticated</span>
        </div>
      </footer>

      {/* Global Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      {/* Global 5-Step Rotation Execution Modal */}
      {isRotationModalOpen && (
        <RotationModal
          credential={rotationTargetCred}
          isOpen={isRotationModalOpen}
          onClose={() => setIsRotationModalOpen(false)}
          onSuccess={handleRotationSuccess}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
