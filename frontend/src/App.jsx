import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'
import LoginPage       from './components/auth/LoginPage'
import Layout          from './components/layout/Layout'
import HomePage        from './pages/HomePage'
import EditorPage      from './pages/EditorPage'
import DashboardPage   from './pages/DashboardPage'
import ReportsPage     from './pages/ReportsPage'
import SettingsPage    from './pages/SettingsPage'
import UsersPage       from './pages/UsersPage'
import DataPage        from './pages/DataPage'
import SSOCallbackPage  from './pages/SSOCallbackPage'

function PrivateRoute({ children, roles }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user?.role)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/sso"   element={<SSOCallbackPage />} />

      <Route path="/" element={
        <PrivateRoute>
          <Layout><HomePage /></Layout>
        </PrivateRoute>
      } />

      <Route path="/editor" element={
        <PrivateRoute roles={['creator', 'superuser']}>
          <Layout><EditorPage /></Layout>
        </PrivateRoute>
      } />
      <Route path="/editor/:id" element={
        <PrivateRoute roles={['creator', 'superuser']}>
          <Layout><EditorPage /></Layout>
        </PrivateRoute>
      } />

      <Route path="/dashboards" element={
        <PrivateRoute>
          <Layout><DashboardPage /></Layout>
        </PrivateRoute>
      } />

      <Route path="/reports" element={
        <PrivateRoute>
          <Layout><ReportsPage /></Layout>
        </PrivateRoute>
      } />

      <Route path="/data" element={
        <PrivateRoute roles={['creator', 'superuser']}>
          <Layout><DataPage /></Layout>
        </PrivateRoute>
      } />

      <Route path="/settings" element={
        <PrivateRoute roles={['creator', 'superuser']}>
          <Layout><SettingsPage /></Layout>
        </PrivateRoute>
      } />

      <Route path="/users" element={
        <PrivateRoute roles={['superuser']}>
          <Layout><UsersPage /></Layout>
        </PrivateRoute>
      } />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
