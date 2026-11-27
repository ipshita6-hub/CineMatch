import { useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import Brand from '../components/Brand'
import { motion, useReducedMotion } from 'framer-motion'
import { ChevronDown, LogOut, Menu, Search, User, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const NAV = [
  { to: '/app', label: 'Home', end: true },
  { to: '/app/movies', label: 'Explore' },
  { to: '/app/recommendations', label: 'For you' },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const reduced = useReducedMotion()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const handleLogout = async () => { await logout(); setOpen(false); navigate('/') }
  const submitSearch = (event) => { event.preventDefault(); navigate(`/app/movies?search=${encodeURIComponent(search.trim())}`); setOpen(false) }

  return (
    <div className="dashboard-shell relative mx-auto min-h-screen max-w-[1800px]">
      <div className="dashboard-ambient" aria-hidden="true"><span /><span /></div>
      <header className="editorial-header sticky top-0 z-40" onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false) }}>
        <div className="editorial-nav mx-auto flex max-w-[1600px] items-center gap-3 px-4 sm:px-5">
          <Brand to="/app" onClick={() => setOpen(false)} />
          <nav className="editorial-links hidden lg:flex" aria-label="Main navigation">{NAV.map(({ to, label, end }) => <NavLink key={to} to={to} end={end} className="editorial-link">{({ isActive }) => <><span>{label}</span>{isActive && <motion.span layoutId="active-navigation" className="nav-active-surface" transition={reduced ? { duration: 0 } : { type: 'spring', stiffness: 350, damping: 32 }} />}</>}</NavLink>)}</nav>
          <form onSubmit={submitSearch} className="editorial-search ml-auto hidden sm:flex"><Search size={17} aria-hidden /><input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search movies" placeholder="Search movies" /></form>
          <details className="account-menu hidden lg:block"><summary aria-label="Account menu"><span className="account-avatar">{user?.username?.[0]?.toUpperCase() || <User size={17} />}</span><ChevronDown size={14} /></summary><div className="account-popover"><p>Signed in as <strong>{user?.username || 'Movie lover'}</strong></p><Link to="/app/profile" onClick={(event) => { event.currentTarget.closest('details').open = false }}><User size={16} /> My profile</Link><button type="button" onClick={handleLogout}><LogOut size={16} /> Sign out</button></div></details>
          <button type="button" onClick={() => setOpen((value) => !value)} aria-label={open ? 'Close navigation' : 'Open navigation'} aria-controls="dashboard-navigation" aria-expanded={open} className="mobile-menu-button ml-auto lg:hidden">{open ? <X size={20} /> : <Menu size={20} />}</button>
        </div>
        {open && <nav id="dashboard-navigation" className="editorial-mobile lg:hidden" aria-label="Mobile navigation"><form onSubmit={submitSearch} className="editorial-search flex sm:hidden"><Search size={16} aria-hidden /><input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search movies" placeholder="Search films" /></form>{[...NAV, { to: '/app/profile', label: 'My profile' }].map(({ to, label, end }) => <NavLink key={to} to={to} end={end} className="editorial-link" onClick={() => setOpen(false)}>{label}</NavLink>)}<button type="button" onClick={handleLogout} className="editorial-mobile-logout"><LogOut size={16} /> Sign out</button></nav>}
      </header>
      <main className="dashboard-main mx-auto max-w-[1600px] px-4 py-6 sm:px-8"><motion.div key={location.pathname} initial={reduced ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .4, ease: 'easeOut' }}><Outlet /></motion.div></main>
      <footer className="mx-auto max-w-[1600px] px-4 pb-10 pt-6 text-xs text-plum-500 sm:px-8">NeuMF trained on MovieLens 20M · the PRD specifies MovieLens 25M; this project uses the supplied 20M release.</footer>
    </div>
  )
}
