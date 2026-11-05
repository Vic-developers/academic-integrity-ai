import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../api";
import Brand from "../components/Brand";
import ErrorMessage from "../components/ErrorMessage";
export default function Recovery({ confirm = false }: { confirm?: boolean }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [token] = useState(
    () => new URLSearchParams(location.hash.slice(1)).get("token") ?? "",
  );
  useEffect(() => {
    if (confirm) history.replaceState(null, "", location.pathname);
  }, [confirm]);
  return (
    <main className="recovery">
      <Brand />
      <div className="login-card">
        <h1>{confirm ? "Nueva contraseña" : "Recupera tu acceso"}</h1>
        <p className="muted">
          {confirm
            ? "Elige una contraseña de al menos 12 caracteres."
            : "Te enviaremos instrucciones si tu cuenta está activa."}
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              const result = await api<{ message: string }>(
                confirm
                  ? "/auth/password-reset/confirm"
                  : "/auth/password-reset/request",
                confirm ? { token, password } : { email },
              );
              setMessage(result.message);
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {confirm ? (
            <>
              <label htmlFor="new-password">Nueva contraseña</label>
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                minLength={12}
                maxLength={256}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </>
          ) : (
            <>
              <label htmlFor="reset-email">Correo electrónico</label>
              <input
                id="reset-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </>
          )}
          <ErrorMessage message={error} />
          {message && <p role="status">{message}</p>}
          <button disabled={busy || Boolean(message)}>
            {busy
              ? "Enviando…"
              : confirm
                ? "Actualizar contraseña"
                : "Enviar instrucciones"}
          </button>
        </form>
        <Link className="subtle-link" to="/login">
          Volver al inicio de sesión
        </Link>
      </div>
    </main>
  );
}
