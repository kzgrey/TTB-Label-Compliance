import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

function Single() {
  const [file, setFile] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [useLlmOcr, setUseLlmOcr] = useState(false);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobDetails, setJobDetails] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);


  const fileInputRef = useRef(null);
  const pollInterval = useRef(null);



  const startPolling = (id) => {
    if (pollInterval.current) clearInterval(pollInterval.current);

    pollInterval.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/jobs/${id}/details`);
        const data = res.data;
        setJobDetails(data);

        if (data.job.status === 'completed' || data.job.status === 'failed') {
          clearInterval(pollInterval.current);
          setLoading(false);
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 250);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setJobDetails(null);
    setJobId(null);
    setImageUrl(null);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('use_llm_ocr', useLlmOcr);
    formData.append('prompt', prompt);

    try {
      const response = await axios.post(`${API_URL}/jobs/submit`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const id = response.data.job_id;
      setJobId(id);
      setImageUrl(`${API_URL}/jobs/${id}/image`);
      startPolling(id);
    } catch (error) {
      console.error('Error submitting job:', error);
      setLoading(false);
    }
  };

  const handleReset = () => {
    if (pollInterval.current) clearInterval(pollInterval.current);
    setFile(null);
    setPrompt('');
    setUseLlmOcr(false);
    setLoading(false);
    setJobId(null);
    setJobDetails(null);
    setImageUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  useEffect(() => {
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, []);

  return (
    <div className="container">
      <header>
        <h1>Single Application Analysis</h1>
        <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>&larr; Back to Home</Link>
      </header>

      <div className="glass-panel">
        <h2>Submit Application</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="file">Label Image</label>
            <input
              type="file"
              id="file"
              accept="image/*"
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files[0])}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="prompt">Application Information (JSON or Text)</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows="5"
              placeholder="Paste the COLA application facts or text here..."
            ></textarea>
          </div>
          <div className="form-group">
            <label htmlFor="ocr-method">OCR Method</label>
            <select
              id="ocr-method"
              value={useLlmOcr ? "llm" : "tesseract"}
              onChange={(e) => setUseLlmOcr(e.target.value === "llm")}
            >
              <option value="tesseract">Tesseract</option>
              <option value="llm">LLM</option>
            </select>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" disabled={loading || !file}>
              {loading ? 'Processing...' : 'Process'}
            </button>
            <button type="button" onClick={handleReset} style={{ background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}>
              Reset
            </button>
          </div>
        </form>
      </div>

      {(loading || jobDetails || imageUrl) && (
        <div className="glass-panel" style={{ marginTop: '2rem' }}>
          <h2>Job Output {jobId ? `(${jobId.substring(0, 8)}...)` : ''}</h2>
          
          {imageUrl && (
            <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
              <img 
                src={imageUrl} 
                alt="Uploaded Label" 
                style={{ maxWidth: '100%', maxHeight: '400px', borderRadius: '8px', border: '1px solid var(--border-color)' }} 
              />
            </div>
          )}

          {loading && (!jobDetails || (jobDetails.job.status !== 'completed' && jobDetails.job.status !== 'failed')) && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '1rem 0' }}>
              <span>Processing... (Status: {jobDetails ? jobDetails.job.status : 'pending'})</span>
            </div>
          )}

          {jobDetails && (jobDetails.job.status === 'completed' || jobDetails.job.status === 'failed') && (
            <div>
              <div className={`status-badge status-${jobDetails.job.status}`} style={{ display: 'inline-block', marginBottom: '1rem' }}>
                {jobDetails.job.status}
              </div>
              {jobDetails.job.total_duration_sec && (
                <p className="job-meta">Total Duration: {jobDetails.job.total_duration_sec.toFixed(2)}s</p>
              )}

              {jobDetails.output ? (
                <>
                  <div className="form-group" style={{ marginTop: '1.5rem' }}>
                    <h3>Rules Passed</h3>
                    <div className="code-block" style={{ borderColor: '#4caf50' }}>
                      {JSON.stringify(jobDetails.output.rules_passed, null, 2)}
                    </div>
                  </div>
                  <div className="form-group">
                    <h3>Rules Failed</h3>
                    <div className="code-block" style={{ borderColor: '#f44336' }}>
                      {JSON.stringify(jobDetails.output.rules_failed, null, 2)}
                    </div>
                  </div>
                  <div className="form-group">
                    <h3>Rules Unknown</h3>
                    <div className="code-block" style={{ borderColor: '#ff9800' }}>
                      {JSON.stringify(jobDetails.output.rules_unknown, null, 2)}
                    </div>
                  </div>
                  <div className="form-group">
                    <h3>LLM JSON Extract</h3>
                    <div className="code-block">
                      {JSON.stringify(jobDetails.output.llm_extracted_json, null, 2)}
                    </div>
                  </div>
                  <div className="form-group">
                    <h3>Raw OCR Output</h3>
                    <div className="code-block">
                      {jobDetails.output.ocr_output}
                    </div>
                  </div>
                </>
              ) : (
                <p>No output available.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Single;
