import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AllogatorUI from './components/AllogatorUI';
import LandingPage from './components/LandingPage';
import SignupPage from './components/SignupPage';
import LoginPage from './components/LoginPage';

function App() {
  const [authStatus, setAuthStatus] = useState<'loading' | 'guest' | 'authenticated'>('loading');

  useEffect(() => {
    // Check authentication status
    const checkAuth = () => {
      const user = localStorage.getItem('allogator_user');
      const token = localStorage.getItem('allogator_access_token');
      
      if (user && token) {
        setAuthStatus('authenticated');
      } else {
        setAuthStatus('guest');
      }
    };

    // Check on mount
    checkAuth();

    // Listen for storage changes (for cross-tab sync and auth updates)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'allogator_access_token' || e.key === 'allogator_user') {
        checkAuth();
      }
    };

    // Listen for custom auth events (for same-tab updates)
    const handleAuthChange = () => {
      checkAuth();
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('auth-state-changed', handleAuthChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('auth-state-changed', handleAuthChange);
    };
  }, []);

  // Show loading state while checking auth status
  if (authStatus === 'loading') {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-400"></div>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        {/* Landing page as the default route */}
        <Route path="/" element={<LandingPage />} />
        
        {/* Login page */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Signup page */}
        <Route path="/signup" element={<SignupPage />} />
        
        {/* Legacy onboarding redirect */}
        <Route path="/onboarding" element={<Navigate to="/signup" replace />} />
        
        {/* Main application - allow guest access */}
        <Route 
          path="/app" 
          element={<AllogatorUI isGuest={authStatus === 'guest'} />} 
        />
        
        {/* Catch all - redirect to landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;