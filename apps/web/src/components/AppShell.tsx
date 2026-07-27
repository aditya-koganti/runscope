import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/authState";

const navigation = [
  { to: "/overview", label: "Overview" },
  { to: "/projects", label: "Projects" },
  { to: "/experiments", label: "Experiments" },
  { to: "/runs", label: "Runs" },
  { to: "/workers", label: "Workers" },
  { to: "/platform-health", label: "Platform health" },
];

export function AppShell() {
  const { user, signOut } = useAuth();
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/overview" aria-label="RunScope overview">
          <span className="brand-mark" aria-hidden="true">
            RS
          </span>
          <span>RunScope</span>
        </NavLink>
        <div className="account">
          <div>
            <strong>{user?.email}</strong>
            <span>{user?.role}</span>
          </div>
          <button className="button button-secondary" onClick={signOut} type="button">
            Sign out
          </button>
        </div>
      </header>
      <div className="workspace">
        <nav className="sidebar" aria-label="Primary navigation">
          <p className="nav-label">Workspace</p>
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
