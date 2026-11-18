import { Link } from 'react-router-dom'

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-300 font-black text-ink-950">N</span>
          <span className="font-extrabold tracking-tight">Cine<span className="text-accent-400">NeuMF</span></span>
        </Link>
        <div className="glass rounded-2xl p-7">
          <h1 className="text-xl font-bold text-white">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-mist-400">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
        {footer && <p className="mt-5 text-center text-sm text-mist-400">{footer}</p>}
      </div>
    </div>
  )
}

export function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-mist-400">{label}</span>
      {children}
      {error && <span className="mt-1 block text-xs text-accent-300">{error}</span>}
    </label>
  )
}

export const inputClass =
  'w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2.5 text-sm text-mist-200 outline-none transition placeholder:text-mist-400/60 focus:border-accent-500'
