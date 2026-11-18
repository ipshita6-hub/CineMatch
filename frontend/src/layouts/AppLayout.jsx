import { useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { BarChart3, Clapperboard, Compass, LogOut, Menu, Sparkles, User, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/app', label: 'Discover', icon: Compass, end: true },
  { to: '/app/movies', label: 'Browse', icon: Clapperboard },
  { to: '/app/recommendations', label: 'For you', icon: Sparkles },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/profile', label: 'Profile', icon: User },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  const linkClass = ({ isActive }) =>
    `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive ? 'bg-accent-500/15 text-accent-300' : 'text-mist-400 hover:bg-ink-800 hover:text-mist-200'
    }`

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-ink-700/60 bg-ink-950/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <Link to="/app" className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-300 font-black text-ink-950">
              N
            </span>
            <span className="text-sm font-extrabold tracking-tight text-mist-200">
              Cine<span className="text-accent-400">NeuMF</span>
            </span>
          </Link>

          <nav className="ml-4 hidden items-center gap-1 md:flex">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass}>
                <Icon className="h-4 w-4" aria-hidden /> {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <span className="hidden text-xs text-mist-400 sm:block">{user?.username}</span>
            <button type="button" onClick={handleLogout}
              className="hidden items-center gap-1.5 rounded-lg border border-ink-700 px-3 py-1.5 text-xs font-semibold text-mist-300 transition hover:border-accent-500 hover:text-white md:flex">
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
            <button type="button" aria-label="Toggle navigation" onClick={() => setOpen((o) => !o)}
              className="rounded-lg border border-ink-700 p-2 text-mist-300 md:hidden">
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {open && (
          <nav className="space-y-1 border-t border-ink-700/60 px-4 py-3 md:hidden">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass} onClick={() => setOpen(false)}>
                <Icon className="h-4 w-4" aria-hidden /> {label}
              </NavLink>
            ))}
            <button type="button" onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-mist-400 hover:text-white">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-10 pt-6 text-xs text-mist-400">
        NeuMF (He et al., WWW 2017) trained on MovieLens 20M · the PRD specifies MovieLens 25M;
        this project uses the 20M release that was supplied.
      </footer>
    </div>
  )
}
