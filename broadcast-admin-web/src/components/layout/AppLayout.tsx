import { NavLink, Outlet } from "react-router-dom";
import { useApiKey } from "../../context/apiKey";
import { ExitIcon } from "@radix-ui/react-icons";

const NAV_LINKS = [
  { to: "/", label: "Dashboard" },
  ...(import.meta.env.VITE_PREVIEW_MODE === "true" ? [{ to: "/catalogue", label: "Earn catalogue" }] : []),
  { to: "/broadcasts", label: "Broadcasts" },
  { to: "/broadcasts/create", label: "Create broadcast" },
];

export const AppLayout = () => {
  const { clearApiKey } = useApiKey();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="logo">EarnAggregator</div>
        <nav>
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => (isActive ? "active" : undefined)}
              end={link.to === "/"}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        {import.meta.env.VITE_PREVIEW_MODE !== "true" && <button className="sidebar__logout" onClick={clearApiKey}>
          <ExitIcon /> Change API key
        </button>}
      </aside>
      <main className="content">
        {import.meta.env.VITE_PREVIEW_MODE === "true" && <p className="preview-banner" role="status">Interactive preview · Synthetic rates · Broadcasts stay as drafts · No messages are sent</p>}
        <Outlet />
      </main>
    </div>
  );
};

