import type { Role } from "./api";
export const labels: Record<Role, string> = {
  superadmin: "Superadministrador",
  admin: "Administrador institucional",
  coordinator: "Coordinador",
  teacher: "Docente",
  auditor: "Auditor",
  student: "Estudiante",
};
