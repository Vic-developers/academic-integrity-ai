import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Identity } from "../api";
import ErrorMessage from "../components/ErrorMessage";
export default function Overview({ identity }: { identity: Identity }) {
  const { data, error } = useQuery({
    queryKey: ["statistics"],
    queryFn: () => api<{ active_members: number }>("/statistics"),
  });
  return (
    <section>
      <span className="eyebrow">TU ESPACIO INSTITUCIONAL</span>
      <h1>Un punto de partida confiable.</h1>
      <p className="muted">
        Hola, {identity.user.name}. Administra el acceso de tu equipo.
      </p>
      <ErrorMessage message={error?.message ?? ""} />
      <div className="cards">
        <div className="panel">
          <span className="eyebrow">MIEMBROS ACTIVOS</span>
          <strong className="metric">{data?.active_members ?? "—"}</strong>
          <span className="muted">
            Usuarios autorizados en esta institución
          </span>
        </div>
        <div className="panel phase">
          <span className="pill">FASE 3</span>
          <h2>La base está en marcha</h2>
          <p>Documentos y comparación literal con evidencias.</p>
        </div>
      </div>
      <div className="panel next">
        <div className="document-icon" aria-hidden="true">
          ▤
        </div>
        <h2>Prepara tus documentos para la revisión</h2>
        <p>
          La carga y la extracción de archivos están disponibles en Documentos.
          <br />
          Compara textos con fuentes seleccionadas y revisa las evidencias.
        </p>
        <Link className="button-link" to="/auditorias">
          Comparación literal disponible
        </Link>
      </div>
      <p className="muted small">
        Las coincidencias y los indicios lingüísticos requieren revisión humana.
      </p>
    </section>
  );
}
