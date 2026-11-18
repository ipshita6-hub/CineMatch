import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import AuthShell, { Field, inputClass } from '../components/AuthShell'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../services/api'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const validate = () => {
    const e = {}
    if (!/^[A-Za-z0-9_.-]{3,64}$/.test(form.username)) {
      e.username = '3-64 characters: letters, digits, dot, dash or underscore.'
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) e.email = 'Enter a valid email address.'
    if (form.password.length < 8) e.password = 'At least 8 characters.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = async (ev) => {
    ev.preventDefault()
    setError(null)
    if (!validate()) return
    setBusy(true)
    try {
      await register(form)
      navigate('/onboarding', { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Registration failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="You will rate a handful of movies next so a user embedding can be fitted for you."
      footer={<>Already registered? <Link to="/login" className="font-semibold text-accent-300 hover:text-accent-200">Sign in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Username" error={errors.username}>
          <input className={inputClass} value={form.username} autoComplete="username"
                 onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </Field>
        <Field label="Email" error={errors.email}>
          <input className={inputClass} type="email" value={form.email} autoComplete="email"
                 onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
        <Field label="Password" error={errors.password}>
          <input className={inputClass} type="password" value={form.password} autoComplete="new-password"
                 onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </Field>
        {error && <p role="alert" className="rounded-lg bg-accent-500/10 px-3 py-2 text-sm text-accent-300">{error}</p>}
        <button type="submit" disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-400 disabled:opacity-60">
          {busy && <Loader2 className="h-4 w-4 animate-spin" />} Create account
        </button>
      </form>
    </AuthShell>
  )
}
