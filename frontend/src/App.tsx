import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import AllogatorUI from './components/AllogatorUI';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AllogatorUI />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;