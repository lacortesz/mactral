import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import ComercialPage from "./pages/ComercialPage";
import DashboardPage from "./pages/DashboardPage";
import FinancieroPage from "./pages/FinancieroPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ImportacionesPage from "./pages/ImportacionesPage";
import LoginPage from "./pages/LoginPage";
import ModulePage from "./pages/ModulePage";
import RegMaestroPage from "./pages/RegMaestroPage";
import SetPasswordPage from "./pages/SetPasswordPage";
import StockPage from "./pages/StockPage";
import TecnicoPage from "./pages/TecnicoPage";
import UsuariosPage from "./pages/UsuariosPage";

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? "/dashboard" : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/activar-cuenta" element={<SetPasswordPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/usuarios"
        element={
          <ProtectedRoute>
            <UsuariosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/comercial"
        element={
          <ProtectedRoute>
            <ComercialPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reg-maestro"
        element={
          <ProtectedRoute>
            <RegMaestroPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/importaciones"
        element={
          <ProtectedRoute>
            <ImportacionesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/tecnico"
        element={
          <ProtectedRoute>
            <TecnicoPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/stock"
        element={
          <ProtectedRoute>
            <StockPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/financiero"
        element={
          <ProtectedRoute>
            <FinancieroPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/modulos/:moduleKey"
        element={
          <ProtectedRoute>
            <ModulePage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
