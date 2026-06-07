import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './Home';
import Jobs from './Jobs';
import Single from './Single';
import Bulk from './Bulk';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/single" element={<Single />} />
        <Route path="/bulk" element={<Bulk />} />
      </Routes>
    </Router>
  );
}

export default App;
