import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { apiFetch } from "../api/client";
import type { ModuleKey, Rol } from "../domain";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: Rol;
};

type MeResponse = AuthUser & { accessible_modules: ModuleKey[] };

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  accessibleModules: ModuleKey[];
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const TOKEN_STORAGE_KEY = "mactral_token";
// E1-H2 escenario 1: la sesión expira tras 8h de inactividad. Con un JWT
// de vida corta-media, "actividad" se aprueba renovando el token mientras
// la pestaña siga abierta; si el usuario deja de interactuar y la pestaña
// se cierra, el JWT expira naturalmente 8h después de la última renovación.
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_STORAGE_KEY)
  );
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessibleModules, setAccessibleModules] = useState<ModuleKey[]>([]);
  const [loading, setLoading] = useState(true);
  const tokenRef = useRef(token);
  tokenRef.current = token;

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setAccessibleModules([]);
  }, []);

  const applySession = useCallback((newToken: string, me: MeResponse) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
    setUser({ id: me.id, name: me.name, email: me.email, role: me.role });
    setAccessibleModules(me.accessible_modules);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const result = await apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      const me = await apiFetch<MeResponse>("/auth/me", { token: result.access_token });
      applySession(result.access_token, me);
    },
    [applySession]
  );

  // Hidrata la sesión al cargar la app si ya había un token guardado.
  useEffect(() => {
    let cancelled = false;
    async function hydrate() {
      if (!tokenRef.current) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiFetch<MeResponse>("/auth/me", { token: tokenRef.current });
        if (!cancelled) {
          setUser({ id: me.id, name: me.name, email: me.email, role: me.role });
          setAccessibleModules(me.accessible_modules);
        }
      } catch {
        if (!cancelled) logout();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    hydrate();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Renueva la sesión periódicamente mientras la app está abierta y hay token.
  useEffect(() => {
    if (!token) return;

    async function refresh() {
      try {
        const result = await apiFetch<{ access_token: string }>("/auth/refresh", {
          method: "POST",
          token: tokenRef.current,
        });
        localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
        setToken(result.access_token);
      } catch {
        logout();
      }
    }

    const interval = setInterval(refresh, REFRESH_INTERVAL_MS);
    const onFocus = () => refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", onFocus);
    };
  }, [token, logout]);

  const value = useMemo<AuthContextValue>(
    () => ({ token, user, accessibleModules, loading, login, logout }),
    [token, user, accessibleModules, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
