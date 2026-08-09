import type { Document } from "../types";
import { api } from "../api/client";
import { categorize, CATEGORY_ICONS } from "../documentIcons";

export default function AttachmentList({ documents }: { documents: Document[] }) {
  if (documents.length === 0) return null;
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: "0.5rem 0 0", fontSize: "0.85rem" }}>
      {documents.map((doc) => (
        <li key={doc.id} style={{ padding: "0.15rem 0" }}>
          <a href={api.downloadDocumentUrl(doc.id)} target="_blank" rel="noreferrer">
            {CATEGORY_ICONS[categorize(doc.mimetype, doc.dateiname)]} {doc.dateiname}
          </a>
        </li>
      ))}
    </ul>
  );
}
