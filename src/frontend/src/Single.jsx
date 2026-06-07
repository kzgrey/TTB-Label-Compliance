import { Link } from 'react-router-dom';

function Single() {
  return (
    <div className="container">
      <header>
        <h1>Single Application Analysis</h1>
        <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>&larr; Back to Home</Link>
      </header>
      <div className="glass-panel">
        <p>This view is under construction.</p>
      </div>
    </div>
  );
}

export default Single;
