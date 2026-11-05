import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Role } from "../api";
import type { Assignment } from "../documents";
import ErrorMessage from "../components/ErrorMessage";
export default function Courses({ role }: { role: Role }) {
  const [course, setCourse] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const manage = ["teacher", "admin", "coordinator", "superadmin"].includes(
    role,
  );
  const courses = useQuery({
    queryKey: ["courses"],
    queryFn: () => api<{ items: { id: string; name: string }[] }>("/courses"),
  });
  const teachers = useQuery({
    queryKey: ["course-teachers"],
    queryFn: () =>
      api<{ items: { id: string; name: string }[] }>("/course-teachers"),
    enabled: manage,
  });
  const assignments = useQuery({
    queryKey: ["assignments"],
    queryFn: () => api<{ items: Assignment[] }>("/assignments"),
  });
  const students = useQuery({
    queryKey: ["course-students", course],
    queryFn: () =>
      api<{ items: { id: string; name: string; enrolled: boolean }[] }>(
        `/courses/${course}/students`,
      ),
    enabled: manage && Boolean(course),
  });
  async function save(path: string, values: unknown) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api(path, values);
      await Promise.all([
        courses.refetch(),
        assignments.refetch(),
        course ? students.refetch() : Promise.resolve(),
      ]);
      setMessage("Cambios guardados");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h1>Asignaturas y actividades</h1>
      <p className="muted">
        Organiza las entregas por asignatura y matrícula autorizada.
      </p>
      <ErrorMessage
        message={
          error || courses.error?.message || assignments.error?.message || ""
        }
      />
      <p role="status">{message}</p>
      {manage && (
        <form
          className="panel user-form"
          onSubmit={(e) => {
            e.preventDefault();
            const values = Object.fromEntries(new FormData(e.currentTarget));
            if (!values.teacher_id) delete values.teacher_id;
            void save("/courses", values);
          }}
        >
          <h2>Nueva asignatura</h2>
          <label>
            Nombre de la asignatura
            <input name="name" required maxLength={160} />
          </label>
          {["admin", "superadmin", "coordinator"].includes(role) && (
            <label>
              Docente responsable
              <select name="teacher_id">
                <option value="">Mi propia cuenta</option>
                {teachers.data?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button disabled={busy}>Crear asignatura</button>
        </form>
      )}
      <div className="panel">
        <label>
          Asignatura seleccionada
          <select value={course} onChange={(e) => setCourse(e.target.value)}>
            <option value="">Seleccionar asignatura</option>
            {courses.data?.items.map((c) => (
              <option value={c.id} key={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        {!courses.data?.items.length && (
          <p>No hay asignaturas disponibles para tu cuenta.</p>
        )}
      </div>
      {course && (
        <>
          <div className="panel">
            <h2>Actividades</h2>
            {assignments.data?.items
              .filter((a) => a.course_id === course)
              .map((a) => (
                <p key={a.id}>{a.name}</p>
              ))}
            {manage && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const values = Object.fromEntries(
                    new FormData(e.currentTarget),
                  );
                  void save("/assignments", { ...values, course_id: course });
                }}
              >
                <label>
                  Nueva actividad
                  <input name="name" required maxLength={160} />
                </label>
                <button disabled={busy}>Crear actividad</button>
              </form>
            )}
          </div>
          {manage && (
            <div className="panel">
              <h2>Matrículas</h2>
              <ErrorMessage message={students.error?.message ?? ""} />
              {students.data?.items.map((s) => (
                <div className="activity-row" key={s.id}>
                  <span>{s.name}</span>
                  {s.enrolled ? (
                    <span className="pill">Matriculado</span>
                  ) : (
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() =>
                        void save(`/courses/${course}/enrollments`, {
                          student_id: s.id,
                        })
                      }
                    >
                      Matricular a {s.name}
                    </button>
                  )}
                </div>
              ))}
              {students.data?.items.length === 0 && (
                <p>
                  No hay estudiantes activos. Un administrador puede crearlos en
                  Usuarios.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
