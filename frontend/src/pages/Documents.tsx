import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Role } from "../api";
import type { Assignment, DocumentRecord } from "../documents";
import { stateNames } from "../documents";
import ErrorMessage from "../components/ErrorMessage";

export default function Documents({ role }: { role: Role }) {
  const [offset, setOffset] = useState(0);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [assignment, setAssignment] = useState("");
  const [owner, setOwner] = useState("");
  const limits = useQuery({
    queryKey: ["document-limits"],
    queryFn: () =>
      api<{
        max_file_bytes: number;
        max_request_bytes: number;
        max_batch_files: number;
      }>("/documents/limits"),
  });
  const list = useQuery({
    queryKey: ["documents", offset],
    queryFn: () =>
      api<{ items: DocumentRecord[] }>(`/documents?offset=${offset}&limit=25`),
    refetchInterval: (q) =>
      q.state.data?.items.some((d) =>
        ["received", "extracting"].includes(d.state),
      )
        ? 1500
        : false,
  });
  const assignments = useQuery({
    queryKey: ["assignments"],
    queryFn: () => api<{ items: Assignment[] }>("/assignments"),
  });
  const course = assignments.data?.items.find(
    (a) => a.id === assignment,
  )?.course_id;
  const students = useQuery({
    queryKey: ["course-students", course],
    queryFn: () =>
      api<{ items: { id: string; name: string; enrolled: boolean }[] }>(
        `/courses/${course}/students`,
      ),
    enabled:
      Boolean(course) &&
      ["teacher", "admin", "superadmin", "coordinator"].includes(role),
  });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErrors([]);
    setMessage("");
    const body = new FormData();
    files.forEach((f) => body.append("files", f));
    if (assignment) body.append("assignment_id", assignment);
    if (owner) body.append("owner_id", owner);
    try {
      const result = await api<{
        items: (DocumentRecord & { duplicate_of: string | null })[];
        errors: { name: string; detail: string }[];
      }>("/documents", body);
      setErrors(result.errors.map((x) => `${x.name}: ${x.detail}`));
      setMessage(
        `${result.items.length} archivo(s) recibido(s). ${result.items.filter((d) => d.duplicate_of).length} coincidencia(s) de archivo duplicado entre tus documentos visibles.`,
      );
      setFiles([]);
      setOffset(0);
      await list.refetch();
    } catch (e) {
      setErrors([(e as Error).message]);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <span className="eyebrow">BIBLIOTECA PRIVADA</span>
      <h1>Documentos</h1>
      <p className="muted">
        Conserva el original y revisa el contenido extraído antes de analizarlo.
      </p>
      {role !== "auditor" && (
        <form className="panel" onSubmit={submit}>
          <h2>Nueva carga</h2>
          <div
            className="dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              setFiles(Array.from(e.dataTransfer.files));
            }}
          >
            <label htmlFor="documents-input">
              Seleccionar o arrastrar documentos
            </label>
            <input
              id="documents-input"
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
            <p className="muted small">
              PDF, DOCX o TXT UTF-8 ·{" "}
              {limits.data
                ? `${limits.data.max_file_bytes / 1048576} MiB por archivo · ${limits.data.max_request_bytes / 1048576} MiB por lote · ${limits.data.max_batch_files} archivos máximo`
                : "Consultando límites…"}
            </p>
            {files.length > 0 && (
              <p>{files.length} archivo(s) seleccionado(s)</p>
            )}
          </div>
          <div className="upload-fields">
            <label>
              Actividad opcional
              <select
                value={assignment}
                onChange={(e) => {
                  setAssignment(e.target.value);
                  setOwner("");
                }}
              >
                <option value="">Sin actividad</option>
                {assignments.data?.items.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.course} · {a.name}
                  </option>
                ))}
              </select>
            </label>
            {course && students.data && (
              <label>
                Entrega de
                <select
                  value={owner}
                  onChange={(e) => setOwner(e.target.value)}
                >
                  <option value="">Mi propia cuenta</option>
                  {students.data.items
                    .filter((s) => s.enrolled)
                    .map((s) => (
                      <option value={s.id} key={s.id}>
                        {s.name}
                      </option>
                    ))}
                </select>
              </label>
            )}
          </div>
          <button
            disabled={
              busy ||
              !files.length ||
              files.length > (limits.data?.max_batch_files ?? 0)
            }
          >
            {busy ? "Guardando originales…" : "Cargar documentos"}
          </button>
          <p role="status">{message}</p>
          {errors.map((error, index) => (
            <ErrorMessage key={index} message={error} />
          ))}
        </form>
      )}
      <ErrorMessage
        message={list.error?.message ?? assignments.error?.message ?? ""}
      />
      {list.isPending && <p role="status">Cargando documentos…</p>}
      <div className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>Documento</th>
              <th>Formato</th>
              <th>Estado</th>
              <th>Tamaño</th>
            </tr>
          </thead>
          <tbody>
            {list.data?.items.map((d) => (
              <tr key={d.id}>
                <td>
                  <Link to={`/documentos/${d.id}`}>{d.name}</Link>
                </td>
                <td>{d.format.toUpperCase()}</td>
                <td>
                  <span className={`doc-state ${d.state}`}>
                    {stateNames[d.state]}
                  </span>
                </td>
                <td>{(d.size / 1024).toFixed(1)} KiB</td>
              </tr>
            ))}
          </tbody>
        </table>
        {list.data?.items.length === 0 && (
          <div className="empty-state">
            <h2>Aún no hay documentos</h2>
            <p>Los archivos que puedas consultar aparecerán aquí.</p>
          </div>
        )}
      </div>
      <div className="pagination">
        <button
          className="secondary"
          disabled={!offset}
          onClick={() => setOffset((v) => Math.max(0, v - 25))}
        >
          Anterior
        </button>
        <span>Página {offset / 25 + 1}</span>
        <button
          className="secondary"
          disabled={list.data?.items.length !== 25}
          onClick={() => setOffset((v) => v + 25)}
        >
          Siguiente
        </button>
      </div>
    </section>
  );
}
