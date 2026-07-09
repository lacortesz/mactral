import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError, apiFetch } from "../api/client";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import type { ModuleKey } from "../domain";

type ModuleResponse = { module: string; label: string; message: string };

export default function ModulePage() {
  const { moduleKey } = useParams<{ moduleKey: ModuleKey }>();
  const { token, accessibleModules } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<ModuleResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!moduleKey || !token) return;

    // Chequeo rápido en cliente: si el rol no tiene el módulo en su lista,
    // ni siquiera se llama al backend (escenario 3, acceso directo por URL).
    if (!accessibleModules.includes(moduleKey)) {
      navigate("/dashboard?denied=1", { replace: true });
      return;
    }

    let cancelled = false;
    setLoading(true);
    apiFetch<ModuleResponse>(`/modules/${moduleKey}`, { token })
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (cancelled) return;
        // La autorización real la aplica el backend (403): si el chequeo de
        // cliente quedó desactualizado, este catch igual redirige.
        if (err instanceof ApiError && err.status === 403) {
          navigate("/dashboard?denied=1", { replace: true });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [moduleKey, token, accessibleModules, navigate]);

  return (
    <AppShell>
      {loading && <p>Cargando...</p>}
      {data && (
        <>
          <h1 className="page-title">{data.label}</h1>
          <div className="card">{data.message}</div>
        </>
      )}
    </AppShell>
  );
}
