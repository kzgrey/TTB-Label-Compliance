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
        <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>
          While bulk handling is not yet implemented in the UI, the backend system fully supports asynchronous execution of many concurrent jobs via the Celery task queue.
        </p>
      </div>
    </div>
  );
}

export default Bulk;
