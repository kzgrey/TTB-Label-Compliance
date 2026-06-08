import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const FIELD_MAPPING = [
  { label: 'Brand', key: 'BrandName', prefixes: ['DS-LABEL-001'] },
  { label: 'Class', key: 'ClassTypeDesignation', prefixes: ['DS-LABEL-010'] },
  { label: 'ABV', key: 'ABV', prefixes: ['DS-LABEL-020'] },
  { label: 'Net Contents', key: 'NetContents', prefixes: ['DS-LABEL-030'] },
  { label: 'Bottler/Producer', key: 'BottlerProducerNameAddr', prefixes: ['DS-LABEL-040'] },
  { label: 'Origin', key: 'ImportOrigin', prefixes: ['DS-LABEL-050'] },
  { label: 'Proof', key: 'Proof', prefixes: ['DS-LABEL-060'] },
  { label: 'Govt Warning Header Present', key: 'GovernmentWarningHeaderText', prefixes: ['DS-LABEL-191'] },
  { label: 'Govt Warning Present', key: 'GovernmentWarningText', prefixes: ['DS-LABEL-192'] },
];

function Single() {
  const [file, setFile] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [useLlmOcr, setUseLlmOcr] = useState(false);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobDetails, setJobDetails] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);


  const fileInputRef = useRef(null);
  const pollInterval = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
      if (fileInputRef.current) {
        fileInputRef.current.files = e.dataTransfer.files;
      }
    }
  };

  const getFieldStatus = (prefixes) => {
    if (!jobDetails || !jobDetails.output) return 'fail';
    const failedRules = Object.keys(jobDetails.output.rules_failed || {});
    for (const rule of failedRules) {
      if (prefixes.some(p => rule.startsWith(p))) return 'fail';
    }
    return 'pass';
  };



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
        <h1>Alcoholic Beverage Label Compliance</h1>
        <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>&larr; Back to Home</Link>
      </header>

      <div className="glass-panel" style={{ marginBottom: '2rem' }}>
        <p style={{ margin: 0 }}>
          <strong>Instructions:</strong> Upload a label image and optionally paste the COLA application facts below. 
          The system currently only contains rules for Distilled Spirits, derived from the{' '}
          <a href="https://www.ttb.gov/system/files/images/pdfs/spirits_bam/complete-distilled-spirit-beverage-alcohol-manual.pdf" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary-color)' }}>
            BAM for Distilled Spirits
          </a>.
        </p>
      </div>

      <div className="glass-panel">
        <h2>Submit Application</h2>
        <form onSubmit={handleSubmit}>
          <div 
            className="form-group" 
            onDragOver={handleDragOver} 
            onDragLeave={handleDragLeave} 
            onDrop={handleDrop}
            style={{ 
              border: isDragging ? '2px dashed var(--primary-color)' : '2px dashed transparent', 
              padding: '1rem', 
              borderRadius: '8px',
              transition: 'border 0.2s ease',
              backgroundColor: isDragging ? 'rgba(100, 108, 255, 0.1)' : 'transparent'
            }}
          >
            <label htmlFor="file">Label Image (Drag & Drop here)</label>
            <input
              type="file"
              id="file"
              accept="image/*"
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files[0])}
              style={{ width: '100%', boxSizing: 'border-box' }}
              required
            />
            {file && <p style={{marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--primary-color)'}}>Selected: {file.name}</p>}
          </div>
          <div className="form-group">
            <label htmlFor="prompt">Application Information (JSON or Text)</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows="5"
              style={{ width: '100%', boxSizing: 'border-box', resize: 'vertical' }}
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
                    <h3>Extracted Label Details</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 2fr 80px', gap: '1rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <div style={{ fontWeight: 'bold' }}>Field</div>
                      <div style={{ fontWeight: 'bold' }}>Extracted Value</div>
                      <div style={{ fontWeight: 'bold' }}>Application Value</div>
                      <div style={{ fontWeight: 'bold', textAlign: 'center' }}>Status</div>
                      {FIELD_MAPPING.map(field => {
                        const status = getFieldStatus(field.prefixes);
                        const val = jobDetails.output.llm_extracted_json?.Label?.[field.key];
                        const appVal = jobDetails.output.application_data?.[field.key];
                        return (
                          <React.Fragment key={field.key}>
                            <div style={{ alignSelf: 'center' }}>{field.label}</div>
                            <div style={{ fontFamily: 'monospace', alignSelf: 'center', wordBreak: 'break-word' }}>
                              {val !== null && val !== undefined ? val.toString() : 'null'}
                            </div>
                            <div style={{ fontFamily: 'monospace', alignSelf: 'center', wordBreak: 'break-word', color: 'var(--text-secondary)' }}>
                              {appVal !== null && appVal !== undefined ? appVal.toString() : 'null'}
                            </div>
                            <div style={{ alignSelf: 'center', textAlign: 'center' }}>
                              <span className={`status-badge status-${status === 'pass' ? 'completed' : 'failed'}`}>
                                {status}
                              </span>
                            </div>
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>

                  <div className="form-group" style={{ marginTop: '1.5rem' }}>
                    <h3 style={{ color: '#4caf50' }}>Rules Passed ({Object.keys(jobDetails.output.rules_passed || {}).length})</h3>
                    <ul style={{ paddingLeft: '20px' }}>
                      {Object.entries(jobDetails.output.rules_passed || {}).map(([rule, desc]) => (
                        <li key={rule}><strong>{rule}</strong>: {desc.message}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="form-group">
                    <h3 style={{ color: '#f44336' }}>Rules Failed ({Object.keys(jobDetails.output.rules_failed || {}).length})</h3>
                    <ul style={{ paddingLeft: '20px' }}>
                      {Object.entries(jobDetails.output.rules_failed || {}).map(([rule, desc]) => (
                        <li key={rule}><strong>{rule}</strong>: {desc.message}{desc.is_hard_failure ? ' (Hard Failure)' : ''}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="form-group">
                    <h3 style={{ color: '#ff9800' }}>Rules Unknown ({Object.keys(jobDetails.output.rules_unknown || {}).length})</h3>
                    <ul style={{ paddingLeft: '20px' }}>
                      {Object.entries(jobDetails.output.rules_unknown || {}).map(([rule, desc]) => (
                        <li key={rule}><strong>{rule}</strong>: {desc.message}</li>
                      ))}
                    </ul>
                  </div>
                  
                  <details style={{ marginTop: '2rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>View Raw JSON Data</summary>
                    <div className="form-group" style={{ marginTop: '1rem' }}>
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
                  </details>
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
