import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import AuthShell, { Field, inputClass } from '../components/AuthShell'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../services/api'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!form.username || !form.password) {
      setError('Enter your username and password.')
      return
    }
    setBusy(true)
    try {
      const user = await login(form)
      navigate(user.onboarded ? location.state?.from || '/app' : '/onboarding', { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Sign in failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to see the recommendations fitted to your ratings."
      footer={<>No account yet? <Link to="/register" className="font-semibold text-accent-300 hover:text-accent-200">Create one</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Username or email">
          <input className={inputClass} value={form.username} autoComplete="username"
                 onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </Field>
        <Field label="Password">
          <input className={inputClass} type="password" value={form.password} autoComplete="current-password"
                 onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        {error && <p role="alert" className="rounded-lg bg-accent-500/10 px-3 py-2 text-sm text-accent-300">{error}</p>}
        <button type="submit" disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-400 disabled:opacity-60">
          {busy && <Loader2 className="h-4 w-4 animate-spin" />} Sign in
        </button>
      </form>
    </AuthShell>
  )
}
