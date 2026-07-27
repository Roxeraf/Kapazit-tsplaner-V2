import type { ReactNode } from "react";

export default function CollapsiblePanel({
  title,
  defaultOpen = true,
  style,
  children,
}: {
  title: ReactNode;
  defaultOpen?: boolean;
  style?: React.CSSProperties;
  children: ReactNode;
}) {
  return (
    <details className="card" open={defaultOpen} style={{ marginTop: "1rem", ...style }}>
      <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--navy)" }}>{title}</summary>
      <div style={{ marginTop: "0.75rem" }}>{children}</div>
    </details>
  );
}
