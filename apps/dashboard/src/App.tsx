import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import StatusPage from './pages/StatusPage';
import CandidatesPage from './pages/CandidatesPage';
import CandidateDetailPage from './pages/CandidateDetailPage';
import DeploymentsPage from './pages/DeploymentsPage';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded text-sm font-medium ${isActive ? 'bg-blue-700 text-white' : 'text-blue-200 hover:bg-blue-600 hover:text-white'}`;

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <span className="text-lg font-bold text-blue-400">SEDBMS</span>
          <NavLink to="/" className={linkClass} end>Status</NavLink>
          <NavLink to="/candidates" className={linkClass}>Candidates</NavLink>
          <NavLink to="/deployments" className={linkClass}>Deployments</NavLink>
        </nav>
        <main className="p-6">
          <Routes>
            <Route path="/" element={<StatusPage />} />
            <Route path="/candidates" element={<CandidatesPage />} />
            <Route path="/candidates/:id" element={<CandidateDetailPage />} />
            <Route path="/deployments" element={<DeploymentsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
