import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import ErrorMessage from "../components/ErrorMessage";
export default function Activity() {
  const { data, error } = useQuery({
    queryKey: ["activity"],
    queryFn: () =>
      api<{ items: { id: string; action: string; created_at: string }[] }>(
        "/activity",
      ),
  });
  return (
    <section>
      <h1>Actividad institucional</h1>
      <ErrorMessage message={error?.message ?? ""} />
      <div className="panel">
        {data?.items.map((a) => (
          <div className="activity-row" key={a.id}>
            <span>{a.action}</span>
            <time>{new Date(a.created_at).toLocaleString("es")}</time>
          </div>
        ))}
        {data?.items.length === 0 && <p>Aún no hay actividad registrada.</p>}
      </div>
    </section>
  );
}
