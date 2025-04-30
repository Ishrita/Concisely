import React, { useState, useRef } from 'react'; 
import { jsPDF } from 'jspdf';

function VideoSummary() {
  const [videoUrl, setVideoUrl] = useState('');
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const summaryRef = useRef(null);

  const handleSummarizeVideo = async () => {
    if (!videoUrl) {
      alert("Please enter a video URL to summarize.");
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:5000/summarize_youtube", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ youtube_url: videoUrl })
      });

      const data = await response.json();

      if (data.error) {
        alert(`Error: ${data.error}`);
        return;
      }

      const summaryText = 
        data.summary || 
        data.result?.summary || 
        data.transcript || 
        "No summary could be generated.";

      setSummary(summaryText);
    } catch (error) {
      console.error("Error summarizing video:", error);
      alert("Failed to summarize video. Check browser console and backend logs.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveSummary = async () => {
    if (!summary) {
      alert("No summary to save.");
      return;
    }

    try {
      const saveResponse = await fetch("http://localhost:5000/save_summary", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          video_url: videoUrl,
          summary: summary 
        })
      });

      const saveResult = await saveResponse.json();

      if (saveResult.error) {
        alert(`Save Error: ${saveResult.error}`);
        return;
      }

      // Generate PDF using jsPDF
      const doc = new jsPDF();
      doc.setFontSize(16);
      doc.text('Video Summary', 10, 10);
      doc.setFontSize(10);
      doc.text(`Source URL: ${videoUrl}`, 10, 20);
      doc.setFontSize(12);
      const splitText = doc.splitTextToSize(summary, 180);
      doc.text(splitText, 10, 30);
      doc.save('video_summary.pdf');

      alert("Summary saved to database and exported as PDF!");
    } catch (error) {
      console.error("Error saving summary:", error);
      alert("Failed to save summary.");
    }
  };

  return (
    <div className="video-summary-container">
      <div className="video-summary-box">
        <h2>Video Summarization</h2>
        <input
          type="text"
          placeholder="Enter video URL here"
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
          disabled={isLoading}
          className="video-url-input"
        />
        <button 
          onClick={handleSummarizeVideo}
          disabled={isLoading}
        >
          {isLoading ? 'Summarizing...' : 'Summarize Video'}
        </button>

        {summary && (
          <div ref={summaryRef} className="summary-box">
            <h3>Summary:</h3>
            <p className="scrollable-summary">{summary}</p>
            <button onClick={handleSaveSummary}>Save & Export Summary</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default VideoSummary;
