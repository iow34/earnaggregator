import { NavLink, Outlet } from "react-router-dom";
import { useApiKey } from "../../context/ApiKeyContext";
import { ExitIcon } from "@radix-ui/react-icons";

const NAV_LINKS = [
  { to: "/", label: "Dashboard" },
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
        <button className="sidebar__logout" onClick={clearApiKey}>
          <ExitIcon /> Change API key
        </button>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
};

