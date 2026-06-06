import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

function App() {
  const [jobs, setJobs] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API_URL}/jobs`);
      setJobs(response.data);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Poll every 5 seconds
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !prompt) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('prompt', prompt);

    try {
      await axios.post(`${API_URL}/jobs/submit`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      // Reset form
      setPrompt('');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchJobs();
    } catch (error) {
      console.error('Error submitting job:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>Intelligence Hub</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Asynchronous OCR & LLM Vision Processing</p>
      </header>

      <div className="glass-panel">
        <h2>Submit New Job</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="prompt">Instructions / Prompt</label>
            <input 
              type="text" 
              id="prompt" 
              value={prompt} 
              onChange={(e) => setPrompt(e.target.value)} 
              placeholder="e.g., Extract the company name and logo description..."
              required 
            />
          </div>
          <div className="form-group">
            <label htmlFor="file">Image File</label>
            <input 
              type="file" 
              id="file" 
              accept="image/*"
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files[0])} 
              required 
            />
          </div>
          <button type="submit" disabled={loading || !file || !prompt}>
            {loading ? 'Submitting...' : 'Process Image'}
          </button>
        </form>
      </div>

      <div className="glass-panel">
        <h2>Job Dashboard</h2>
        <div className="job-list">
          {jobs.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No jobs found.</p>
          ) : (
            jobs.map((job) => (
              <div key={job.id} className="job-item">
                <div className="job-info">
                  <h3>Job ID: {job.id.substring(0, 8)}...</h3>
                  <p className="job-meta">
                    Created: {new Date(job.created_at).toLocaleString()} 
                    {job.total_duration_sec && ` | Duration: ${job.total_duration_sec.toFixed(2)}s`}
                  </p>
                </div>
                <div className={`status-badge status-${job.status}`}>
                  {job.status}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
