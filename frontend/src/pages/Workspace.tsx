import { lazy, Suspense, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api";
import type { Identity } from "../api";
import { queryClient } from "../query";
import { labels } from "../roles";
import Brand from "../components/Brand";
import ErrorMessage from "../components/ErrorMessage";
import Users from "./Users";
import Activity from "./Activity";
import Overview from "./Overview";
import Documents from "./Documents";
import DocumentDetail from "./DocumentDetail";
import Courses from "./Courses";
import Audits from "./Audits";
import EvidenceViewer from "./EvidenceViewer";
import Bibliography from "./Bibliography";
import BibliographyResult from "./BibliographyResult";
import AuditResult from "./AuditResult";
import Claims from "./Claims";

import ClaimResult from "./ClaimResult";
const ExperimentalAI = lazy(() => import("./ExperimentalAI"));
export default function Workspace() {
  const { data, error, isPending } = useQuery({
    queryKey: ["identity"],
    queryFn: () => api<Identity>("/auth/me"),
  });
  const [message, setMessage] = useState("");
  const [dark, setDark] = useState(
    () => localStorage.getItem("theme") === "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  if (error instanceof ApiError && error.status === 401)
    return <Navigate to="/login" replace />;
  if (isPending)
    return (
      <main className="recovery" role="status">
        Cargando tu espacio…
      </main>
    );
  if (error || !data)
    return (
      <main className="recovery">
        <ErrorMessage
          message={error?.message ?? "No se pudo cargar la sesión"}
        />
        <button onClick={() => void queryClient.invalidateQueries()}>
          Reintentar
        </button>
      </main>
    );
  const selected = data.memberships.find(
    (m) => m.institution_id === data.institution_id,
  );
  async function choose(id: string) {
    setMessage("");
    try {
      await api("/auth/institution", { institution_id: id });
      queryClient.clear();
      location.assign("/");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }
  if (!selected)
    return (
      <main className="recovery">
        <Brand />
        <h1>Selecciona tu institución</h1>
        <p className="muted">Solo se muestran tus membresías activas.</p>
        {data.memberships.map((m) => (
          <button
            key={m.institution_id}
            onClick={() => void choose(m.institution_id)}
          >
            {m.name} · {labels[m.role]}
          </button>
        ))}
        {!data.memberships.length && (
          <p>No tienes membresías activas. Contacta al administrador.</p>
        )}
        <ErrorMessage message={message} />
        <button
          className="secondary"
          onClick={async () => {
            await api("/auth/logout", {});
            queryClient.clear();
            location.assign("/login");
          }}
        >
          Cerrar sesión
        </button>
      </main>
    );
  return (
    <div className="workspace">
      <a className="skip" href="#content">
        Saltar al contenido
      </a>
      <aside className="sidebar">
        <Brand />
        <span className="nav-label">ESPACIO DE TRABAJO</span>
        <nav aria-label="Principal">
          <Link to="/">◈ &nbsp; Resumen</Link>
          <Link to="/documentos">▤ &nbsp; Documentos</Link>
          <Link to="/asignaturas">▦ &nbsp; Asignaturas</Link>
          <Link to="/indicios-ia">◌ &nbsp; Observaciones lingüísticas</Link>
          <Link to="/afirmaciones">◇ &nbsp; Afirmaciones</Link>
          <Link to="/bibliografia">▧ &nbsp; Bibliografía</Link>
          <Link to="/auditorias">⌕ &nbsp; Comparación literal</Link>
          {["admin", "superadmin", "coordinator"].includes(selected.role) && (
            <Link to="/usuarios">♙ &nbsp; Usuarios</Link>
          )}
          {["admin", "superadmin", "coordinator", "auditor"].includes(
            selected.role,
          ) && <Link to="/actividad">≡ &nbsp; Actividad</Link>}
        </nav>
        <div className="sidebar-bottom">
          <span className="pill">Acceso institucional</span>
          <p>
            La evidencia informa.
            <br />
            Las personas deciden.
          </p>
          <button className="secondary" onClick={() => setDark((v) => !v)}>
            {dark ? "Modo claro" : "Modo oscuro"}
          </button>
        </div>
      </aside>
      <div className="workspace-body">
        <header>
          <div>
            <span className="muted small">INSTITUCIÓN</span>
            <label className="sr-only" htmlFor="institution">
              Institución activa
            </label>
            <select
              id="institution"
              value={selected.institution_id}
              onChange={(e) => void choose(e.target.value)}
            >
              {data.memberships.map((m) => (
                <option key={m.institution_id} value={m.institution_id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
          <div className="account">
            <span>
              {data.user.name}
              <small>{labels[selected.role]}</small>
            </span>
            <button
              className="secondary"
              onClick={async () => {
                try {
                  await api("/auth/logout", {});
                  queryClient.clear();
                  location.assign("/login");
                } catch (e) {
                  setMessage((e as Error).message);
                }
              }}
            >
              Salir
            </button>
          </div>
        </header>
        <main id="content" tabIndex={-1}>
          <ErrorMessage message={message} />
          <Routes>
            <Route path="/" element={<Overview identity={data} />} />
            <Route
              path="/documentos"
              element={<Documents role={selected.role} />}
            />
            <Route path="/documentos/:id" element={<DocumentDetail />} />
            <Route
              path="/indicios-ia"
              element={
                <Suspense
                  fallback={<p role="status">Cargando observaciones…</p>}
                >
                  <ExperimentalAI />
                </Suspense>
              }
            />
            <Route
              path="/indicios-ia/:id"
              element={
                <Suspense
                  fallback={<p role="status">Cargando observaciones…</p>}
                >
                  <ExperimentalAI key={location.pathname} />
                </Suspense>
              }
            />
            <Route path="/afirmaciones" element={<Claims />} />
            <Route
              path="/afirmaciones/:id"
              element={
                <ClaimResult
                  key={location.pathname}
                  canReview={selected.role !== "student"}
                />
              }
            />
            <Route path="/bibliografia" element={<Bibliography />} />
            <Route
              path="/bibliografia/:documentId"
              element={<Bibliography />}
            />
            <Route
              path="/bibliografia/resultados/:id"
              element={<BibliographyResult />}
            />
            <Route path="/auditorias" element={<Audits />} />
            <Route
              path="/auditorias/:id/evidencias"
              element={
                <EvidenceViewer canReview={selected.role !== "student"} />
              }
            />
            <Route path="/auditorias/:id" element={<AuditResult />} />
            <Route
              path="/asignaturas"
              element={<Courses role={selected.role} />}
            />
            <Route
              path="/usuarios"
              element={
                ["admin", "superadmin", "coordinator"].includes(
                  selected.role,
                ) ? (
                  <Users
                    canCreate={["admin", "superadmin"].includes(selected.role)}
                  />
                ) : (
                  <ErrorMessage message="No tienes permiso para esta sección" />
                )
              }
            />
            <Route
              path="/actividad"
              element={
                ["admin", "superadmin", "coordinator", "auditor"].includes(
                  selected.role,
                ) ? (
                  <Activity />
                ) : (
                  <ErrorMessage message="No tienes permiso para esta sección" />
                )
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer>
          Academic Integrity AI{" "}
          <span>Gestión documental · Revisión humana</span>
        </footer>
      </div>
    </div>
  );
}
