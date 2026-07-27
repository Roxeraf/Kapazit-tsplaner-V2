import { NavLink, Route, Routes } from "react-router-dom";
import PortfolioDashboard from "./views/PortfolioDashboard";
import ProjectDetail from "./views/ProjectDetail";
import TeamCapacity from "./views/TeamCapacity";
import GapAnalysis from "./views/GapAnalysis";
import JiraProjects from "./views/JiraProjects";

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>plx.crew · BUILD · Kapazitätsplaner</h1>
        <nav className="app-nav">
          <NavLink to="/" end>
            Portfolio
          </NavLink>
          <NavLink to="/team">Team-Kapazität</NavLink>
          <NavLink to="/jira-projekte">Jira-Projekte</NavLink>
          <NavLink to="/gap">Gap-Analyse</NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<PortfolioDashboard />} />
          <Route path="/projekte/:id" element={<ProjectDetail />} />
          <Route path="/team" element={<TeamCapacity />} />
          <Route path="/jira-projekte" element={<JiraProjects />} />
          <Route path="/gap" element={<GapAnalysis />} />
        </Routes>
      </main>
    </div>
  );
}
