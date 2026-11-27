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
  const [searchOpen, setSearchOpen] = useState(false)
  const [search, setSearch] = useState('')
  const handleLogout = async () => { await logout(); setOpen(false); navigate('/') }
  const submitSearch = (event) => { event.preventDefault(); navigate(`/app/movies?search=${encodeURIComponent(search.trim())}`); setOpen(false); setSearchOpen(false) }

  return (
    <div className="dashboard-shell relative mx-auto min-h-screen max-w-[1800px]">
      <div className="dashboard-ambient" aria-hidden="true"><span /><span /></div>
      <header className="editorial-header sticky top-0 z-40" onKeyDown={(event) => { if (event.key === 'Escape') { setOpen(false); setSearchOpen(false) } }}>
        <div className="editorial-nav mx-auto flex items-center gap-2">
          <Brand to="/app" className="nav-logo" onClick={() => setOpen(false)} />
          <nav className="editorial-links" aria-label="Main navigation">{NAV.map(({ to, label, end }) => <NavLink key={to} to={to} end={end} className="editorial-link"><span className="nav-roll"><span>{label}</span><span aria-hidden="true">{label}</span></span></NavLink>)}<button type="button" className="editorial-link nav-search-trigger" onClick={() => setSearchOpen((value) => !value)} aria-expanded={searchOpen} aria-controls="nav-search"><span className="nav-roll"><span>Search</span><span aria-hidden="true">Search</span></span></button></nav>
          <details className="account-menu"><summary aria-label="Account menu"><span className="account-label">{user?.username || 'My account'}</span><ChevronDown size={14} /></summary><div className="account-popover"><p>Signed in as <strong>{user?.username || 'Movie lover'}</strong></p><Link to="/app/profile" onClick={(event) => { event.currentTarget.closest('details').open = false }}><User size={16} /> My profile</Link><button type="button" onClick={handleLogout}><LogOut size={16} /> Sign out</button></div></details>
          <button type="button" onClick={() => setOpen((value) => !value)} aria-label={open ? 'Close navigation' : 'Open navigation'} aria-controls="dashboard-navigation" aria-expanded={open} className="mobile-menu-button ml-auto lg:hidden">{open ? <X size={20} /> : <Menu size={20} />}</button>
        </div>
        {searchOpen && <form id="nav-search" onSubmit={submitSearch} className="nav-search-panel"><Search size={18} aria-hidden /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search movies" placeholder="Search for a movie…" /><button type="submit">Search</button></form>}
        {open && <nav id="dashboard-navigation" className="editorial-mobile" aria-label="Mobile navigation"><form onSubmit={submitSearch} className="editorial-search"><Search size={16} aria-hidden /><input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search movies" placeholder="Search films" /></form>{[...NAV, { to: '/app/profile', label: 'My profile' }].map(({ to, label, end }) => <NavLink key={to} to={to} end={end} className="editorial-link" onClick={() => setOpen(false)}>{label}</NavLink>)}<button type="button" onClick={handleLogout} className="editorial-mobile-logout"><LogOut size={16} /> Sign out</button></nav>}
      </header>
      <main className="dashboard-main mx-auto max-w-[1600px] px-4 py-6 sm:px-8"><motion.div key={location.pathname} initial={reduced ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .4, ease: 'easeOut' }}><Outlet /></motion.div></main>
      <footer className="mx-auto max-w-[1600px] px-4 pb-10 pt-6 text-xs text-plum-500 sm:px-8">NeuMF trained on MovieLens 20M · the PRD specifies MovieLens 25M; this project uses the supplied 20M release.</footer>
    </div>
  )
}
