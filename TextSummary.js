import React, { useState } from 'react'; 
import './TextSummary.css';

const TextSummary = () => {
  const [inputText, setInputText] = useState('');
  const [summarizedText, setSummarizedText] = useState('');

  const handleSummarizeText = async () => {
    if (!inputText.trim()) {
      alert("Please enter some text to summarize.");
      return;
    }

    try {
      const response = await fetch("http://localhost:5000/summarize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: inputText }),
      });

      const data = await response.json();

      if (data.error) {
        alert("Error: " + data.error);
        return;
      }

      setSummarizedText(data.summary);
    } catch (error) {
      console.error("Error summarizing text:", error);
      alert("Failed to summarize text. Check backend logs.");
    }
  };

  const handleSaveSummary = async () => {
    if (!summarizedText.trim()) {
        alert("No summary to save!");
        return;
    }

    try {
        const response = await fetch('http://localhost:5000/save_summary', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                original_text: inputText, 
                summary_text: summarizedText 
            })
        });

        if (response.ok) {
            console.log("Summary saved to DB successfully!");
        } else {
            console.error("Failed to save summary!");
        }
    } catch (error) {
        console.error("Error saving summary:", error);
    }

    const blob = new Blob([summarizedText], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'summarized_text.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="text-summary-container">
      <div className="text-summary-box">
        <h2 className="text-summary-title">Text Summarization</h2>
        <textarea
          className="input-text"
          placeholder="Enter long text here"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
        />
        <button className="summarize-button" onClick={handleSummarizeText}>
          Summarize Text
        </button>
        {summarizedText && (
          <div className="summary-box">
            <h3 className="summary-title">Summarized Text:</h3>
            <p className="summary-text">{summarizedText}</p>
            <button className="save-button" onClick={handleSaveSummary}>
              Save Summary
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TextSummary;
