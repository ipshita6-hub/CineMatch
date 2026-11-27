import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { movieApi } from '../services/api'
import AnimatedMarqueeHero from '../components/AnimatedMarqueeHero'

export default function Landing() {
  const { data: featured, loading } = useApi(
    () => movieApi.list({ sort: 'popularity', page_size: 12, min_ratings: 10000 }), [])

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-rose-500 to-rose-700 font-black text-white">C</span>
          <span className="font-extrabold tracking-tight">Cine<span className="text-rose-600">Match</span></span>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/login" className="rounded-lg px-4 py-2 text-sm font-semibold text-plum-600 transition hover:text-plum-900">Sign in</Link>
          <Link to="/register" className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-600">Create account</Link>
        </div>
      </header>
      <AnimatedMarqueeHero movies={featured?.items || []} loading={loading} />
    </div>
  )
}
