import { useEffect, useState } from "react";
import { api } from "../../api/client";
import NotesSection from "../../components/NotesSection";
import type { Comment } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

type Section = "diskussionen" | "entscheidungen" | "risiken" | "meetingprotokolle";

const SECTIONS: { key: Section; label: string }[] = [
  { key: "diskussionen", label: "Diskussionen" },
  { key: "entscheidungen", label: "Entscheidungen" },
  { key: "risiken", label: "Risiken" },
  { key: "meetingprotokolle", label: "Meetingprotokolle" },
];

export default function ProjectCommunicationTab() {
  const { project } = useProjectWorkspace();
  const [section, setSection] = useState<Section>("diskussionen");
  const [comments, setComments] = useState<Comment[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refreshComments = () => {
    api.listComments(project.id).then(setComments).catch((e) => setError(String(e)));
  };

  useEffect(refreshComments, [project.id]);

  const generalComments = (subprojectId: number | null) =>
    comments.filter((c) => c.subproject_id === subprojectId && c.monat === null && c.phase_code === null);

  const handleAddNote = async (subprojectId: number | null, text: string) => {
    await api.createComment(project.id, { subproject_id: subprojectId, text });
    refreshComments();
  };

  const handleDeleteComment = async (commentId: number) => {
    await api.deleteComment(commentId);
    refreshComments();
  };

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      <div className="legend-row" style={{ marginBottom: "1rem" }}>
        {SECTIONS.map((s) => (
          <button
            key={s.key}
            type="button"
            className={s.key === section ? "btn" : "btn secondary"}
            onClick={() => setSection(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {section === "diskussionen" && (
        <div>
          <div className="card" style={{ marginBottom: "1rem" }}>
            <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Projekt</h3>
            <NotesSection notes={generalComments(null)} onAdd={(text) => handleAddNote(null, text)} onDelete={handleDeleteComment} />
          </div>
          {project.subprojects.map((sp) => (
            <div key={sp.id} className="card" style={{ marginBottom: "1rem" }}>
              <h3 style={{ color: "var(--navy)", marginTop: 0 }}>{sp.name}</h3>
              <NotesSection
                notes={generalComments(sp.id)}
                onAdd={(text) => handleAddNote(sp.id, text)}
                onDelete={handleDeleteComment}
              />
            </div>
          ))}
        </div>
      )}

      {section !== "diskussionen" && (
        <div className="stub-view">
          {SECTIONS.find((s) => s.key === section)?.label} — in Planung (siehe CONCEPT.md, Phase 4 Kommunikation-Datenmodell).
        </div>
      )}
    </div>
  );
}
