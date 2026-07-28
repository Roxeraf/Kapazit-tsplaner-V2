import type { MouseEvent } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import PortfolioDashboard from "./views/PortfolioDashboard";
import ProjectDetail from "./views/ProjectDetail";
import TeamCapacity from "./views/TeamCapacity";
import GapAnalysis from "./views/GapAnalysis";
import JiraProjects from "./views/JiraProjects";
import { UnsavedChangesProvider, useUnsavedChanges } from "./unsavedChanges";

export default function App() {
  return (
    <UnsavedChangesProvider>
      <AppShell />
    </UnsavedChangesProvider>
  );
}

function AppShell() {
  const { isDirty, setIsDirty } = useUnsavedChanges();
  const navigate = useNavigate();

  // Verhindert versehentlichen Verlust ungespeicherter Planungsänderungen (Entwurfsmodus in
  // ProjectDetail), wenn über die globale Navigation eine andere Seite aufgerufen wird.
  const guardedNavigate = (to: string) => (e: MouseEvent) => {
    if (!isDirty) return;
    e.preventDefault();
    if (window.confirm("Ungespeicherte Änderungen gehen verloren. Trotzdem verlassen?")) {
      setIsDirty(false);
      navigate(to);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>plx.Kapazitätsplaner TEAM GOAL</h1>
        <nav className="app-nav">
          <NavLink to="/" end onClick={guardedNavigate("/")}>
            Portfolio
          </NavLink>
          <NavLink to="/team" onClick={guardedNavigate("/team")}>
            Team-Kapazität
          </NavLink>
          <NavLink to="/jira-projekte" onClick={guardedNavigate("/jira-projekte")}>
            Jira-Projekte
          </NavLink>
          <NavLink to="/gap" onClick={guardedNavigate("/gap")}>
            Gap-Analyse
          </NavLink>
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
