import { Link } from 'react-router-dom';

function Bulk() {
  return (
    <div className="container">
      <header>
        <h1>Bulk Applications Analysis</h1>
        <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>&larr; Back to Home</Link>
      </header>
      <div className="glass-panel">
        <p>This view is under construction.</p>
      </div>
    </div>
  );
}

export default Bulk;
