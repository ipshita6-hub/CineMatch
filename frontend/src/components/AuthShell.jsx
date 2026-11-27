import { Link } from 'react-router-dom'
import Brand from './Brand'

export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <Brand to="/" className="mb-6 justify-center" />
        <div className="glass rounded-3xl p-8 shadow-2xl shadow-black/50">
          <h1 className="text-3xl font-extrabold tracking-tight text-plum-900">{title}</h1>
          {subtitle && <p className="mt-2 text-sm leading-relaxed text-plum-500">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
        {footer && <p className="mt-5 text-center text-sm text-plum-500">{footer}</p>}
      </div>
    </div>
  )
}

export function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-plum-500">{label}</span>
      {children}
      {error && <span className="mt-1 block text-xs text-rose-700">{error}</span>}
    </label>
  )
}

export const inputClass =
  'w-full rounded-lg border border-blush-300 bg-blush-100 px-3 py-2.5 text-sm text-plum-700 outline-none transition placeholder:text-plum-500 focus:border-rose-500'
