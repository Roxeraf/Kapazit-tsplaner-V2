import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import { useTagDossier } from "../../../tagDossier";

// P16.5 (Aktuelle Themen): welche Tags gerade im Projekt am meisten Objekte tragen - reine
// Wiederverwendung bestehender Endpoints (GET /knowledge/project/{id} für die im Projekt
// verwendeten Tag-Namen, dann je Tag GET /knowledge/tags/dossier für dessen Objektanzahl,
// beide aus backend/app/routers/knowledge.py). Keine neue Aggregation im Backend - die Anzahl
// der Tag-Abfragen ist durch die tatsächlich im Projekt verwendeten Tags begrenzt.
const MAX_TAGS_QUERIED = 15;
const MAX_TAGS_SHOWN = 6;

interface TopicCount {
  tag: string;
  count: number;
}

export default function CurrentTopicsWidget({ projectId }: { projectId: number }) {
  const [topics, setTopics] = useState<TopicCount[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { openTag } = useTagDossier();

  useEffect(() => {
    let cancelled = false;
    setTopics(null);
    api
      .getProjectKnowledgeContext(projectId)
      .then(async (ctx) => {
        const tagNames = ctx.tags.slice(0, MAX_TAGS_QUERIED);
        const dossiers = await Promise.all(
          tagNames.map((tag) =>
            api
              .getTagDossier([tag], "and", projectId)
              .then((d) => ({ tag, count: Object.values(d.counts).reduce((sum, c) => sum + c, 0) }))
              .catch(() => ({ tag, count: 0 })),
          ),
        );
        if (cancelled) return;
        setTopics(dossiers.filter((t) => t.count > 0).sort((a, b) => b.count - a.count).slice(0, MAX_TAGS_SHOWN));
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (error || (topics && topics.length === 0)) return null;

  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <h3 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aktuelle Themen</h3>
      {!topics ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lade …</p>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {topics.map((t) => (
            <button
              key={t.tag}
              type="button"
              className="btn secondary"
              style={{ fontSize: "0.82rem" }}
              onClick={() => openTag(t.tag)}
            >
              #{t.tag} · {t.count} {t.count === 1 ? "Objekt" : "Objekte"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
