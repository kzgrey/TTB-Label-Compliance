import { Link } from 'react-router-dom';
import './index.css';

function Home() {
  return (
    <div className="home-container">
      <header className="home-header">
        <h1>Intelligence Hub</h1>
        <p className="home-subtitle">Automated Label Compliance Analysis</p>
        <div className="home-disclaimer" style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'rgba(255, 200, 0, 0.1)', border: '1px solid rgba(255, 200, 0, 0.5)', borderRadius: '8px', color: '#ffcc00', maxWidth: '600px', margin: '1rem auto' }}>
          <strong>Disclaimer:</strong> This system has only been trained to support rules for Distilled Spirits and not Wine or Malts.
        </div>
      </header>
      <div className="button-grid">
        <Link to="/single" className="hero-button glass-panel single-button">
          <div className="button-content">
            <h2>Analyze Single Application</h2>
            <p>Process a single TTB application and label image</p>
          </div>
        </Link>
        <Link to="#" className="hero-button glass-panel bulk-button" style={{ opacity: 0.5, cursor: 'not-allowed', pointerEvents: 'none' }}>
          <div className="button-content">
            <h2>Analyze Bulk Applications</h2>
            <p>Upload and process a batch of TTB applications (Coming Soon)</p>
          </div>
        </Link>
      </div>
    </div>
  );
}

export default Home;
