/**
 * SecureRotate AI - Centralized Frontend API Service
 * Handles authenticated HTTP requests with JWT injection and error sanitization.
 */

const API_BASE = '/api/v1';

// Token helpers
export const getStoredToken = () => localStorage.getItem('securerotate_token');
export const setStoredToken = (token) => localStorage.setItem('securerotate_token', token);
export const removeStoredToken = () => localStorage.removeItem('securerotate_token');

/**
 * Core authenticated fetch wrapper
 */
async function request(endpoint, options = {}) {
  const token = localStorage.getItem('securerotate_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If not on login endpoint, notify token expired
    if (!endpoint.includes('/auth/login') && !endpoint.includes('/auth/register')) {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
  }

  const contentType = response.headers.get('content-type');
  let data = null;
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = data?.detail || data?.message || (typeof data === 'string' ? data : 'Request failed');
    throw new Error(errorMsg);
  }

  return data;
}

export const apiService = {
  // --- Authentication ---
  login: async (usernameOrEmail, password) => {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        username_or_email: usernameOrEmail,
        password: password,
      }),
    });
  },

  register: async (username, email, password, role = 'AUDITOR') => {
    return request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username,
        email,
        password,
        role,
      }),
    });
  },

  getMe: async () => {
    return request('/auth/me');
  },

  logout: async () => {
    try {
      await request('/auth/logout', { method: 'POST' });
    } catch {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('securerotate_token');
      localStorage.removeItem('securerotate_user');
    }
  },

  // --- User Management (Admin Only) ---
  getUsers: () => request('/users'),
  createUser: (userData) => request('/users', { method: 'POST', body: JSON.stringify(userData) }),
  updateUser: (id, userData) => request(`/users/${id}`, { method: 'PUT', body: JSON.stringify(userData) }),
  deactivateUser: (id) => request(`/users/${id}`, { method: 'DELETE' }),

  // --- Health & Dashboard Stats ---
  getHealth: () => request('/health'),
  getDashboardStats: () => request('/credentials/dashboard-stats'),

  // --- Credentials Vault ---
  getCredentials: () => request('/credentials'),
  getCredentialById: (id) => request(`/credentials/${id}`),
  createCredential: (payload) => request('/credentials', { method: 'POST', body: JSON.stringify(payload) }),
  updateCredential: (id, payload) => request(`/credentials/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteCredential: (id) => request(`/credentials/${id}`, { method: 'DELETE' }),
  seedDemoData: (force = false) => request(`/credentials/seed-demo-data${force ? '?force=true' : ''}`, { method: 'POST' }),

  // --- Risk Engine ---
  getRiskOverview: () => request('/risk/overview'),
  getCredentialRisk: (id) => request(`/risk/credentials/${id}`),
  predictRisk: (features) => request('/risk/predict', { method: 'POST', body: JSON.stringify(features) }),

  // --- Dependencies & Impact ---
  getCredentialDependencies: (credId) => request(`/credentials/${credId}/dependencies`),
  getCredentialImpact: (credId) => request(`/credentials/${credId}/impact`),
  createDependency: (credId, depData) => request(`/credentials/${credId}/dependencies`, { method: 'POST', body: JSON.stringify(depData) }),
  deleteDependency: (depId) => request(`/dependencies/${depId}`, { method: 'DELETE' }),

  // --- Approvals & Workflows ---
  getApprovals: () => request('/approvals'),
  createRotationRequest: (credential_id, reason) => request('/rotation-requests', {
    method: 'POST',
    body: JSON.stringify({ credential_id, reason }),
  }),
  approveRotationRequest: (approvalId) => request(`/approvals/${approvalId}/approve`, { method: 'POST' }),
  rejectRotationRequest: (approvalId, rejection_reason) => request(`/approvals/${approvalId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ rejection_reason }),
  }),

  // --- Rotation Execution ---
  executeRotation: (credential_id, simulate_failure = false) => request(
    `/rotation/${credential_id}${simulate_failure ? '?simulate_failure=true' : ''}`,
    { method: 'POST' }
  ),
  getRotationStatus: (credential_id) => request(`/rotation/${credential_id}/status`),

  // --- Notifications ---
  getNotifications: () => request('/notifications'),
  triggerExpiryScan: () => request('/notifications/check-expiry', { method: 'POST' }),

  // --- Audit Trail ---
  getAuditLogs: () => request('/audit-logs'),
};
