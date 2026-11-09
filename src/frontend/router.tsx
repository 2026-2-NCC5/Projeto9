/**
 * FECAP Guia — Roteador React Router v6
 * Conecta todas as 19 telas da Fase 2
 */
import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

// Telas do Estudante
import { SplashPage } from "@/pages/student/SplashPage";
import { LoginPage } from "@/pages/student/LoginPage";
import { ForgotPasswordPage } from "@/pages/student/ForgotPasswordPage";
import { HomePage } from "@/pages/student/HomePage";
import { ChatPage } from "@/pages/student/ChatPage";
import { ResultPage } from "@/pages/student/ResultPage";
import { HandoffPage } from "@/pages/student/HandoffPage";
import { HistoryPage } from "@/pages/student/HistoryPage";
import { FeedbackPage } from "@/pages/student/FeedbackPage";
import { ProfilePage } from "@/pages/student/ProfilePage";
import { HelpPage } from "@/pages/student/HelpPage";

// Telas Administrativas
import { AdminLoginPage } from "@/pages/admin/AdminLoginPage";
import { DashboardPage } from "@/pages/admin/DashboardPage";
import { KnowledgePage } from "@/pages/admin/KnowledgePage";
import { KnowledgeFormPage } from "@/pages/admin/KnowledgeFormPage";
import { UnansweredPage } from "@/pages/admin/UnansweredPage";
import { FeedbacksPage } from "@/pages/admin/FeedbacksPage";
import { HandoffsPage } from "@/pages/admin/HandoffsPage";
import { AuditPage } from "@/pages/admin/AuditPage";

const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const AdminRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, user } = useAuthStore();
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }
  if (user?.role !== "admin") {
    return <Navigate to="/home" replace />;
  }
  return children;
};

export const router = createBrowserRouter([
  // Redirecionamento Inicial
  { path: "/", element: <Navigate to="/splash" replace /> },

  // Rotas Públicas / Auth
  { path: "/splash", element: <SplashPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },

  // Rotas Protegidas do Estudante
  { path: "/home", element: <ProtectedRoute><HomePage /></ProtectedRoute> },
  { path: "/chat", element: <ProtectedRoute><ChatPage /></ProtectedRoute> },
  { path: "/result", element: <ProtectedRoute><ResultPage /></ProtectedRoute> },
  { path: "/handoff", element: <ProtectedRoute><HandoffPage /></ProtectedRoute> },
  { path: "/history", element: <ProtectedRoute><HistoryPage /></ProtectedRoute> },
  { path: "/feedback/:runId", element: <ProtectedRoute><FeedbackPage /></ProtectedRoute> },
  { path: "/profile", element: <ProtectedRoute><ProfilePage /></ProtectedRoute> },
  { path: "/help", element: <ProtectedRoute><HelpPage /></ProtectedRoute> },

  // Rotas Administrativas
  { path: "/admin", element: <Navigate to="/admin/login" replace /> },
  { path: "/admin/login", element: <AdminLoginPage /> },
  { path: "/admin/dashboard", element: <AdminRoute><DashboardPage /></AdminRoute> },
  { path: "/admin/knowledge", element: <AdminRoute><KnowledgePage /></AdminRoute> },
  { path: "/admin/knowledge/new", element: <AdminRoute><KnowledgeFormPage /></AdminRoute> },
  { path: "/admin/knowledge/:id", element: <AdminRoute><KnowledgeFormPage /></AdminRoute> },
  { path: "/admin/unanswered", element: <AdminRoute><UnansweredPage /></AdminRoute> },
  { path: "/admin/feedbacks", element: <AdminRoute><FeedbacksPage /></AdminRoute> },
  { path: "/admin/handoffs", element: <AdminRoute><HandoffsPage /></AdminRoute> },
  { path: "/admin/audit", element: <AdminRoute><AuditPage /></AdminRoute> },

  // Fallback 404
  { path: "*", element: <Navigate to="/login" replace /> },
]);

