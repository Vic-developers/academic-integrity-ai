import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "../api";
import { queryClient } from "../query";
import Brand from "../components/Brand";
import ErrorMessage from "../components/ErrorMessage";
const loginSchema = z.object({
  email: z.email("Escribe un correo válido"),
  password: z.string().min(1, "Escribe tu contraseña"),
});
export default function Login() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
  });
  return (
    <div className="login-grid">
      <aside className="intro">
        <Brand />
        <div>
          <span className="eyebrow">UN ESPACIO PARA LA REVISIÓN ACADÉMICA</span>
          <h1>
            La evidencia abre
            <br />
            la conversación.
          </h1>
          <p>
            Un entorno institucional para documentar hallazgos, preservar el
            contexto y apoyar decisiones humanas.
          </p>
        </div>
        <p className="footnote">
          La similitud requiere interpretación.
          <br />
          Cada decisión conserva su contexto.
        </p>
      </aside>
      <main className="login-main">
        <div className="login-card">
          <span className="eyebrow">ACCESO INSTITUCIONAL</span>
          <h2>Bienvenido de nuevo</h2>
          <p className="muted">Inicia sesión con tu cuenta autorizada.</p>
          <form
            onSubmit={handleSubmit(async (values) => {
              setError("");
              try {
                await api("/auth/login", values);
                queryClient.clear();
                navigate("/");
              } catch (e) {
                setError((e as Error).message);
              }
            })}
          >
            <label htmlFor="email">Correo electrónico</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              {...register("email")}
            />
            <ErrorMessage message={errors.email?.message ?? ""} />
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
            />
            <ErrorMessage message={errors.password?.message ?? ""} />
            <ErrorMessage message={error} />
            <button disabled={isSubmitting}>
              {isSubmitting ? "Verificando…" : "Iniciar sesión →"}
            </button>
          </form>
          <Link className="subtle-link" to="/recuperar">
            ¿Olvidaste tu contraseña?
          </Link>
          <div className="notice">
            Acceso privado. Los permisos dependen de tu institución y de tu rol.
          </div>
        </div>
      </main>
    </div>
  );
}
