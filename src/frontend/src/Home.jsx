import { Link } from 'react-router-dom';
import './index.css';

function Home() {
  return (
    <div className="home-container">
      <header className="home-header">
        <h1>Intelligence Hub</h1>
        <p className="home-subtitle">Automated Label Compliance Analysis</p>
      </header>
      <div className="button-grid">
        <Link to="/single" className="hero-button glass-panel single-button">
          <div className="button-content">
            <h2>Analyze Single Application</h2>
            <p>Process a single TTB application and label image</p>
          </div>
        </Link>
        <Link to="/bulk" className="hero-button glass-panel bulk-button">
          <div className="button-content">
            <h2>Analyze Bulk Applications</h2>
            <p>Upload and process a batch of TTB applications</p>
          </div>
        </Link>
      </div>
    </div>
  );
}

export default Home;
