import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Landing from './components/Landing';
import Signup from './components/Signup';
import Login from './components/Login';
import Home from './components/Home';
import TextSummary from './components/TextSummary';
import VideoSummary from './components/VideoSummary';
import Sidebar from './components/Sidebar';  // Import Sidebar
import './App.css';

function PrivateRoute({ children }) {
  return localStorage.getItem("token") ? children : <Navigate to="/login" />;
}

function AppLayout() {
  const location = useLocation();
  const hideSidebar = location.pathname === "/login" || location.pathname === "/signup"; 

  return (
    <div className="App">
      {!hideSidebar && <Sidebar />}  {/* Sidebar is hidden on login & signup pages */}
      <div className={`content ${!hideSidebar ? 'with-sidebar' : ''}`}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/login" element={<Login />} />
          <Route path="/home" element={<PrivateRoute><Home /></PrivateRoute>} />
          <Route path="/text-summary" element={<PrivateRoute><TextSummary /></PrivateRoute>} />
          <Route path="/video-summary" element={<PrivateRoute><VideoSummary /></PrivateRoute>} />
        </Routes>
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppLayout />
    </Router>
  );
}

export default App;
