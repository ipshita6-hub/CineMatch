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
      isActive ? 'bg-rose-500/15 text-rose-700' : 'text-plum-500 hover:bg-blush-100 hover:text-plum-700'
    }`

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-blush-200/60 bg-blush-50/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <Link to="/app" className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-rose-500 to-rose-700 font-black text-white">
              C
            </span>
            <span className="text-sm font-extrabold tracking-tight text-plum-700">
              Cine<span className="text-rose-600">Match</span>
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
            <span className="hidden text-xs text-plum-500 sm:block">{user?.username}</span>
            <button type="button" onClick={handleLogout}
              className="hidden items-center gap-1.5 rounded-lg border border-blush-200 px-3 py-1.5 text-xs font-semibold text-plum-600 transition hover:border-rose-500 hover:text-plum-900 md:flex">
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
            <button type="button" aria-label="Toggle navigation" onClick={() => setOpen((o) => !o)}
              className="rounded-lg border border-blush-200 p-2 text-plum-600 md:hidden">
              {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {open && (
          <nav className="space-y-1 border-t border-blush-200/60 px-4 py-3 md:hidden">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={linkClass} onClick={() => setOpen(false)}>
                <Icon className="h-4 w-4" aria-hidden /> {label}
              </NavLink>
            ))}
            <button type="button" onClick={handleLogout}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-plum-500 hover:text-plum-900">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-10 pt-6 text-xs text-plum-500">
        NeuMF (He et al., WWW 2017) trained on MovieLens 20M · the PRD specifies MovieLens 25M;
        this project uses the 20M release that was supplied.
      </footer>
    </div>
  )
}
