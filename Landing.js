import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Landing.css';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-container">
      <div className="landing-content">
        <h1 className="landing-title">Welcome to Concisely</h1>
        <p className="landing-subtitle">Summarize text or video within seconds</p>
      </div>
      <div className="landing-right">
        <div className="landing-buttons">
          <button 
            onClick={() => navigate('/login')} 
            className="landing-btn" 
            title="Login to your account"
          >
            Login
          </button>
          <button 
            onClick={() => navigate('/signup')} 
            className="landing-btn" 
            title="Create a new account"
          >
            Signup
          </button>
        </div>
      </div>
    </div>
  );
};

export default Landing;
