import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Role } from "../api";
import { labels } from "../roles";
import ErrorMessage from "../components/ErrorMessage";
export default function Users({ canCreate }: { canCreate: boolean }) {
  const [offset, setOffset] = useState(0);
  const { data, error, refetch } = useQuery({
    queryKey: ["users", offset],
    queryFn: () =>
      api<{ items: { id: string; name: string; email: string; role: Role }[] }>(
        `/users?limit=25&offset=${offset}`,
      ),
  });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <section>
      <h1>Usuarios de la institución</h1>
      <ErrorMessage message={error?.message ?? ""} />
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Rol</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{labels[u.role]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination" aria-label="Paginación de usuarios">
        <button
          className="secondary"
          disabled={offset === 0}
          onClick={() => setOffset((v) => Math.max(0, v - 25))}
        >
          Anterior
        </button>
        <span className="muted small">
          Página {Math.floor(offset / 25) + 1}
        </span>
        <button
          className="secondary"
          disabled={data?.items.length !== 25}
          onClick={() => setOffset((v) => v + 25)}
        >
          Siguiente
        </button>
      </div>
      {canCreate && (
        <div className="panel">
          <h2>Crear usuario</h2>
          <p className="muted">
            Solo identidades nuevas. Entrega la contraseña inicial por un canal
            autorizado.
          </p>
          <form
            className="user-form"
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.currentTarget;
              const values = Object.fromEntries(new FormData(form));
              setBusy(true);
              setMessage("");
              try {
                await api("/users", values);
                form.reset();
                await refetch();
                setMessage("Usuario creado");
              } catch (e) {
                setMessage((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Nombre
              <input name="name" required maxLength={160} autoComplete="off" />
            </label>
            <label>
              Correo
              <input name="email" type="email" required autoComplete="off" />
            </label>
            <label>
              Contraseña inicial
              <input
                name="password"
                type="password"
                minLength={12}
                maxLength={256}
                required
                autoComplete="new-password"
              />
            </label>
            <label>
              Rol
              <select name="role">
                <option value="teacher">Docente</option>
                <option value="student">Estudiante</option>
                <option value="auditor">Auditor</option>
                <option value="coordinator">Coordinador</option>
                <option value="admin">Administrador institucional</option>
              </select>
            </label>
            <button disabled={busy}>
              {busy ? "Creando…" : "Crear usuario"}
            </button>
            <p role="status">{message}</p>
          </form>
        </div>
      )}
    </section>
  );
}
