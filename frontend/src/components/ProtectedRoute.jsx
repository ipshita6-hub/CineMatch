import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './States'

export default function ProtectedRoute({ children, requireOnboarding = true }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <Spinner label="Restoring your session…" />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (requireOnboarding && !user.onboarded && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }
  return children
}
