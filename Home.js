import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Home.css';

function Home() {
  const [selectedOption, setSelectedOption] = useState('');
  const navigate = useNavigate();

  const handleOptionSelection = (option) => {
    setSelectedOption(option);
    if (option === 'text') {
      navigate('/text-summary'); // Navigate to Text Summary page
    } else if (option === 'video') {
      navigate('/video-summary'); // Navigate to Video Summary page
    }
  };

  return (
    <div className="home-container">
      <div className="home-box">
        <h2>Welcome to Concisely</h2>
        <p>Choose an option to proceed:</p>
        <div className="option-buttons">
          <button onClick={() => handleOptionSelection('text')}>Summarize Text</button>
          <button onClick={() => handleOptionSelection('video')}>Summarize Video</button>
        </div>
      </div>
    </div>
  );
}

export default Home;
