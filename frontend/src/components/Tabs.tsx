import type { MouseEvent } from "react";
import { NavLink } from "react-router-dom";

export interface TabItem {
  to: string;
  label: string;
}

export default function Tabs({
  items,
  guardedNavigate,
}: {
  items: TabItem[];
  guardedNavigate: (to: string) => (e: MouseEvent) => void;
}) {
  return (
    <nav className="tab-nav">
      {items.map((t) => (
        <NavLink key={t.to} to={t.to} onClick={guardedNavigate(t.to)}>
          {t.label}
        </NavLink>
      ))}
    </nav>
  );
}
