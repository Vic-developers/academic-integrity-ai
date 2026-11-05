export type Role =
  | "superadmin"
  | "admin"
  | "coordinator"
  | "teacher"
  | "auditor"
  | "student";
export type Identity = {
  user: { id: string; email: string; name: string };
  institution_id: string | null;
  memberships: { institution_id: string; name: string; role: Role }[];
};
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const csrf =
    document.cookie
      .split("; ")
      .find((x) => x.startsWith("aid_csrf="))
      ?.split("=")[1] ?? "";
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "AcademicIntegrityAI",
      "X-CSRF-Token": csrf,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => ({}));
    const detail =
      typeof data === "object" && data && "detail" in data
        ? String(data.detail)
        : "No se pudo conectar con el servicio";
    throw new ApiError(response.status, detail);
  }
  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>);
}
