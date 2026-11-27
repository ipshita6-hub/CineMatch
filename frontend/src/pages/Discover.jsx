import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Info, Search, Sparkles } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { movieApi, recommendationApi, userApi } from '../services/api'
import MovieRow from '../components/MovieRow'
import Poster from '../components/Poster'

export default function Discover() {
  const { user } = useAuth()
  const reduced = useReducedMotion()
  const [selectedId, setSelectedId] = useState(null)
  const status = useApi(() => userApi.status(), [])
  const recs = useApi(() => recommendationApi.mine({ limit: 18, model: 'neumf' }), [])
  const trending = useApi(() => movieApi.list({ sort: 'popularity', page_size: 18 }), [])
  const topRated = useApi(
    () => movieApi.list({ sort: 'rating', page_size: 18, min_ratings: 5000 }), [])
  const recent = useApi(
    () => movieApi.list({ sort: 'year', page_size: 18, min_ratings: 500 }), [])
  const prefs = useApi(() => userApi.preferences(), [])

  const favouriteGenre = prefs.data?.preferred_genres?.[0]
  const byGenre = useApi(
    () => movieApi.list({ genre: favouriteGenre, sort: 'popularity', page_size: 18 }),
    [favouriteGenre], { enabled: Boolean(favouriteGenre) },
  )

  const recItems = useMemo(() => recs.data?.items || [], [recs.data])
  const featuredMovies = recItems.length ? recItems : (trending.data?.items || [])
  const selected = featuredMovies.find((movie) => movie.movie_id === selectedId) || featuredMovies[0]
  const featuredDetail = useApi(() => movieApi.detail(selected.movie_id), [selected?.movie_id], { enabled: Boolean(selected) })
  const featured = featuredDetail.data?.movie_id === selected?.movie_id ? featuredDetail.data : selected

  return (
    <div className="space-y-10">
      <div className="dashboard-intro flex flex-wrap items-end justify-between gap-4">
        <div><p className="eyebrow"><Sparkles size={14} /> YOUR CINEMA, REIMAGINED</p><h1 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">Welcome back{user?.username ? `, ${user.username}` : ''}.</h1><p className="mt-2 text-sm text-plum-500">A little inspiration for your next movie night.</p></div>
        <Link to="/app/recommendations" className="dashboard-pill">Explore your picks <ArrowUpRight size={16} /></Link>
      </div>
      <section className="cinema-hero dashboard-feature flex min-h-[540px] flex-col justify-end rounded-3xl border border-white/10 px-6 pb-8 pt-14 sm:px-12">
        <AnimatePresence initial={false}>
          {(featured?.backdrop_url || featured?.poster_url) && <motion.div key={featured.movie_id} className="feature-backdrop" style={{ backgroundImage: `url("${featured.backdrop_url || featured.poster_url}")` }} initial={{ opacity: 0, scale: reduced ? 1 : 1.05 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: reduced ? 0 : .7 }} aria-hidden="true" />}
        </AnimatePresence>
        <div className="hero-orbit hero-orbit-one" aria-hidden="true" /><div className="hero-orbit hero-orbit-two" aria-hidden="true" />
        <div className="feature-grid" aria-hidden="true" />
        {featured && <motion.div key={`poster-${featured.movie_id}`} className="feature-poster" initial={reduced ? false : { opacity: 0, y: 25, rotate: 5 }} animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ duration: .7 }}><Poster movie={featured} rounded="rounded-2xl" /></motion.div>}
        <div key={featured?.movie_id} className="max-w-xl animate-[page-enter_.45s_ease_both]">
          <p className="feature-label"><Sparkles size={13} /> Featured for you</p>
          <h1 className="feature-title mt-4 text-4xl font-black leading-[1.02] tracking-tight text-white sm:text-6xl">{featured?.title || 'Discover something extraordinary'}</h1>
          <p className="mt-4 text-sm text-plum-600">{featured ? [featured.release_year, ...(featured.genres || []).slice(0, 3)].filter(Boolean).join(' · ') : 'A world of stories, picked for you.'}</p>
          {featured?.overview && <p className="mt-3 line-clamp-3 max-w-lg text-sm leading-relaxed text-plum-600">{featured.overview}</p>}
          <div className="mt-6 flex flex-wrap gap-3">
            {featured && <Link to={`/app/movies/${featured.movie_id}`} className="rounded-full bg-rose-500 px-7 py-3 text-sm font-bold text-white transition hover:scale-105 hover:bg-rose-600">Movie details</Link>}
            <Link to="/app/movies" className="rounded-full border border-white/40 px-7 py-3 text-sm font-semibold text-white transition hover:bg-white/10">Browse movies</Link>
          </div>
        </div>
        <div className="feature-selector no-scrollbar relative mt-8 flex gap-2 overflow-x-auto pb-2 pt-2" aria-label="Choose a featured movie">
          {featuredMovies.map((movie) => <button key={movie.movie_id} type="button" onClick={() => setSelectedId(movie.movie_id)} aria-label={`Feature ${movie.title}`} aria-pressed={selected?.movie_id === movie.movie_id} className={`h-16 w-12 shrink-0 overflow-hidden rounded-lg border-2 transition duration-300 hover:-translate-y-1 ${selected?.movie_id === movie.movie_id ? 'border-rose-500 shadow-[0_0_18px_rgba(100,150,255,.45)]' : 'border-transparent opacity-70 hover:opacity-100'}`}><Poster movie={movie} rounded="rounded-md" /></button>)}
        </div>
      </section>
      <div className="cinema-data-grid">
        <div><span>THE COLLECTION</span><strong>{trending.data?.total != null ? trending.data.total.toLocaleString() : '—'}</strong><small>Movies in the catalog</small></div>
        <div><span>YOUR DISCOVERY</span><strong>{recs.data?.items?.length ?? '—'}</strong><small>Recommendations in this selection</small></div>
        <div><span>THE ENGINE</span><strong>NeuMF</strong><small>Personalised movie discovery</small></div>
      </div>
      <div className="dashboard-context flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-plum-500">{status.data?.method ? `Personalisation method: ${status.data.method}` : 'Curated from the MovieLens catalog'}</p>
        <Link to="/app/movies"
          className="flex items-center gap-2 rounded-lg border border-blush-300 px-4 py-2 text-sm font-semibold text-plum-600 transition hover:border-rose-500 hover:text-plum-900">
          <Search className="h-4 w-4" /> Search the catalog
        </Link>
      </div>

      {recs.data && !recs.data.personalised && (
        <div className="glass flex items-start gap-3 rounded-xl p-4">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-gold-600" />
          <p className="text-sm text-plum-600">
            {recs.data.fallback_reason || 'Showing popularity-based results, not personalised ones.'}{' '}
            <Link to="/app/movies" className="font-semibold text-rose-700 underline">Rate a few movies</Link>{' '}
            to fit your embedding.
          </p>
        </div>
      )}

      <MovieRow title={recs.data?.personalised ? 'Top picks for you' : 'Popular right now'}
        subtitle={recs.data ? `${recs.data.model_used} · generated in ${recs.data.generated_in_ms} ms` : undefined}
        movies={recItems} loading={recs.loading} error={recs.error} onRetry={recs.reload}
        showScore showRank emptyHint="Rate a few movies to unlock personalised recommendations." />

      <MovieRow title="Most rated in the dataset" subtitle="Ranked by number of training ratings"
        movies={trending.data?.items} loading={trending.loading} error={trending.error} onRetry={trending.reload} />

      <MovieRow title="Highest rated" subtitle="Average rating, among movies with 5,000+ ratings"
        movies={topRated.data?.items} loading={topRated.loading} error={topRated.error} onRetry={topRated.reload} />

      {favouriteGenre && (
        <MovieRow title={`Because you like ${favouriteGenre}`} subtitle="Genre collection from your preferences"
          movies={byGenre.data?.items} loading={byGenre.loading} error={byGenre.error} onRetry={byGenre.reload} />
      )}

      <MovieRow title="Newest in the catalog" subtitle="By release year recorded in MovieLens"
        movies={recent.data?.items} loading={recent.loading} error={recent.error} onRetry={recent.reload} />
    </div>
  )
}
