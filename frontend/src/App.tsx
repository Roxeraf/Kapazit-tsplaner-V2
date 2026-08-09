import { Navigate, Route, Routes } from "react-router-dom";
import PortfolioDashboard from "./views/PortfolioDashboard";
import TeamCapacity from "./views/TeamCapacity";
import GapAnalysis from "./views/GapAnalysis";
import JiraProjects from "./views/JiraProjects";
import ProjectWorkspace from "./views/project/ProjectWorkspace";
import ProjectOverviewTab from "./views/project/ProjectOverviewTab";
import ProjectPlanningTab from "./views/project/ProjectPlanningTab";
import ProjectCommunicationTab from "./views/project/ProjectCommunicationTab";
import ProjectJiraTab from "./views/project/ProjectJiraTab";
import ProjectDocumentsTab from "./views/project/ProjectDocumentsTab";
import ProjectHistoryTab from "./views/project/ProjectHistoryTab";
import ProjectSettingsTab from "./views/project/ProjectSettingsTab";
import { UnsavedChangesProvider } from "./unsavedChanges";
import { useGuardedNavigate } from "./useGuardedNavigate";
import { NavLink } from "react-router-dom";

export default function App() {
  return (
    <UnsavedChangesProvider>
      <AppShell />
    </UnsavedChangesProvider>
  );
}

function AppShell() {
  const guardedNavigate = useGuardedNavigate();

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>plx.Kapazitätsplaner TEAM GOAL</h1>
        <nav className="app-nav app-nav--tiered">
          <div className="app-nav-group" aria-label="Projektmanagement">
            <span className="app-nav-group-label">Projektmanagement</span>
            <NavLink to="/" end onClick={guardedNavigate("/")}>
              Dashboard
            </NavLink>
          </div>
          <div className="app-nav-group" aria-label="Controlling">
            <span className="app-nav-group-label">Controlling</span>
            <NavLink to="/gap" onClick={guardedNavigate("/gap")}>
              Gap-Analyse
            </NavLink>
            <NavLink to="/team" onClick={guardedNavigate("/team")}>
              Kapazität
            </NavLink>
          </div>
          <div className="app-nav-group app-nav-group--utility">
            <NavLink to="/jira-projekte" onClick={guardedNavigate("/jira-projekte")}>
              Jira-Projekte
            </NavLink>
          </div>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<PortfolioDashboard />} />
          <Route path="/projekte/:id" element={<ProjectWorkspace />}>
            <Route index element={<Navigate to="uebersicht" replace />} />
            <Route path="uebersicht" element={<ProjectOverviewTab />} />
            <Route path="planung" element={<ProjectPlanningTab />} />
            <Route path="kommunikation" element={<ProjectCommunicationTab />} />
            <Route path="jira" element={<ProjectJiraTab />} />
            <Route path="dokumente" element={<ProjectDocumentsTab />} />
            <Route path="historie" element={<ProjectHistoryTab />} />
            <Route path="einstellungen" element={<ProjectSettingsTab />} />
          </Route>
          <Route path="/team" element={<TeamCapacity />} />
          <Route path="/jira-projekte" element={<JiraProjects />} />
          <Route path="/gap" element={<GapAnalysis />} />
        </Routes>
      </main>
    </div>
  );
}
