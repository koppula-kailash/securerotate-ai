import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiService } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('securerotate_user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('securerotate_token'));
  const [isLoading, setIsLoading] = useState(true);

  // Sync token and verify profile on initial load
  useEffect(() => {
    async function initAuth() {
      const savedToken = localStorage.getItem('securerotate_token');
      if (savedToken) {
        try {
          const profile = await apiService.getMe();
          setUser(profile);
          localStorage.setItem('securerotate_user', JSON.stringify(profile));
        } catch {
          // If token verification fails, clear local storage
          localStorage.removeItem('securerotate_token');
          localStorage.removeItem('securerotate_user');
          setUser(null);
          setToken(null);
        }
      }
      setIsLoading(false);
    }

    initAuth();

    // Listen for unauthorized 401 events dispatched from API service
    const handleUnauthorized = () => {
      localStorage.removeItem('securerotate_token');
      localStorage.removeItem('securerotate_user');
      setUser(null);
      setToken(null);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = async (usernameOrEmail, password) => {
    const data = await apiService.login(usernameOrEmail, password);
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('securerotate_token', data.access_token);
    localStorage.setItem('securerotate_user', JSON.stringify(data.user));
    return data.user;
  };

  const register = async (username, email, password, role = 'AUDITOR') => {
    const newUser = await apiService.register(username, email, password, role);
    // Automatically log in after registration
    return await login(username, password);
  };

  const logout = async () => {
    await apiService.logout();
    setUser(null);
    setToken(null);
  };

  // Demo helper: quickly log into demo accounts (admin, devops, auditor)
  const switchDemoRole = async (targetRole) => {
    const roleCredentials = {
      ADMIN: { u: 'admin', p: 'Admin123!' },
      DEVOPS: { u: 'devops', p: 'Devops123!' },
      AUDITOR: { u: 'auditor', p: 'Auditor123!' },
    };
    const creds = roleCredentials[targetRole.toUpperCase()];
    if (creds) {
      return await login(creds.u, creds.p);
    }
  };

  const role = user?.role?.toUpperCase() || 'GUEST';
  const isAdmin = role === 'ADMIN';
  const isDevOps = role === 'DEVOPS';
  const isAuditor = role === 'AUDITOR';
  const canManageCredentials = isAdmin || isDevOps;
  const canApproveRotation = isAdmin;

  const value = {
    user,
    token,
    role,
    isAuthenticated: !!user && !!token,
    isLoading,
    isAdmin,
    isDevOps,
    isAuditor,
    canManageCredentials,
    canApproveRotation,
    login,
    register,
    logout,
    switchDemoRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
