import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDown, ArrowUpRight, Info, Search } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { movieApi, recommendationApi, userApi } from '../services/api'
import MovieRow from '../components/MovieRow'
import Poster from '../components/Poster'
import { Counter, SectionMarker } from '../components/Furniture'

/**
 * Home.
 *
 * The hero follows the IRIS_AI reference's corner-pinned composition: a label
 * top-left, section marker and counter top-right, the film title bottom-left,
 * its synopsis and actions bottom-right, a scroll hint centred below, and the
 * featured artwork owning the middle. Every value shown is real — the counter
 * tracks the actual featured list, and no row is labelled "trending", because
 * the backend has no trending signal.
 */
export default function Discover() {
  const { user } = useAuth()
  const reduced = useReducedMotion()
  const [selectedId, setSelectedId] = useState(null)

  const status = useApi(() => userApi.status(), [])
  const recs = useApi(() => recommendationApi.mine({ limit: 18, model: 'neumf' }), [])
  const mostRated = useApi(() => movieApi.list({ sort: 'popularity', page_size: 18 }), [])
  const topRated = useApi(() => movieApi.list({ sort: 'rating', page_size: 18, min_ratings: 5000 }), [])
  const recent = useApi(() => movieApi.list({ sort: 'year', page_size: 18, min_ratings: 500 }), [])
  const prefs = useApi(() => userApi.preferences(), [])

  const favouriteGenre = prefs.data?.preferred_genres?.[0]
  const byGenre = useApi(
    () => movieApi.list({ genre: favouriteGenre, sort: 'popularity', page_size: 18 }),
    [favouriteGenre], { enabled: Boolean(favouriteGenre) },
  )

  const recItems = useMemo(() => recs.data?.items || [], [recs.data])
  const featuredMovies = recItems.length ? recItems : (mostRated.data?.items || [])
  const selectedIndex = Math.max(0, featuredMovies.findIndex((m) => m.movie_id === selectedId))
  const selected = featuredMovies[selectedIndex] || featuredMovies[0]
  const featuredDetail = useApi(
    () => movieApi.detail(selected.movie_id), [selected?.movie_id], { enabled: Boolean(selected) })
  const featured = featuredDetail.data?.movie_id === selected?.movie_id ? featuredDetail.data : selected

  const personalised = recs.data?.personalised

  return (
    <div className="space-y-10">
      <div className="dashboard-intro flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">CINEMATCH <span className="text-ink-faint">/</span> DISCOVER</p>
          <h1 className="display mt-3 text-3xl sm:text-4xl">
            Welcome back<em>{user?.username ? `, ${user.username}` : ''}</em>
          </h1>
        </div>
        <Link to="/app/recommendations" className="dashboard-pill">
          Explore your picks <ArrowUpRight size={16} />
        </Link>
      </div>

      <section className="cinema-hero dashboard-feature relative flex min-h-[560px] flex-col rounded-3xl border border-white/10 px-6 pb-7 pt-7 sm:px-10">
        <AnimatePresence initial={false}>
          {(featured?.backdrop_url || featured?.poster_url) && (
            <motion.div
              key={featured.movie_id}
              className="feature-backdrop"
              style={{ backgroundImage: `url("${featured.backdrop_url || featured.poster_url}")` }}
              initial={{ opacity: 0, scale: reduced ? 1 : 1.05 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: reduced ? 0 : 0.7 }}
              aria-hidden="true"
            />
          )}
        </AnimatePresence>
        <div className="hero-orbit hero-orbit-one" aria-hidden="true" />
        <div className="hero-orbit hero-orbit-two" aria-hidden="true" />
        <div className="feature-grid" aria-hidden="true" />

        {featured && (
          <motion.div
            key={`poster-${featured.movie_id}`}
            className="feature-poster hidden lg:block"
            initial={reduced ? false : { opacity: 0, y: 25, rotate: 5 }}
            animate={{ opacity: 1, y: 0, rotate: 0 }}
            transition={{ duration: 0.7 }}
          >
            <Poster movie={featured} rounded="rounded-2xl" />
          </motion.div>
        )}

        {/* top-left label · top-right marker + counter */}
        <div className="relative z-10 flex items-start justify-between gap-4">
          <p className="feature-label">{personalised ? 'Featured for you' : 'Most rated'}</p>
          <div className="flex items-center gap-4">
            <SectionMarker letter="A" />
            <Counter index={selectedIndex} total={featuredMovies.length} />
          </div>
        </div>

        <div className="flex-1" />

        {/* bottom-left headline · bottom-right synopsis + actions */}
        <div className="relative z-10 grid items-end gap-7 lg:grid-cols-[minmax(0,1fr)_minmax(0,20rem)]">
          <div key={featured?.movie_id} className="animate-[page-enter_.45s_ease_both]">
            <h2 className="feature-title display text-4xl sm:text-6xl">
              {featured?.title || <>Discover something <em>extraordinary</em></>}
            </h2>
            {featured && (
              <p className="mono-tag mt-4">
                {[featured.release_year, ...(featured.genres || []).slice(0, 3)].filter(Boolean).join('  ·  ')}
              </p>
            )}
          </div>

          <div className="lg:pb-1">
            {featured?.overview && (
              <p className="line-clamp-4 text-sm leading-relaxed text-plum-600">{featured.overview}</p>
            )}
            <div className="mt-5 flex flex-wrap gap-3">
              {featured && (
                <Link
                  to={`/app/movies/${featured.movie_id}`}
                  className="rounded-full bg-accent-500 px-6 py-2.5 font-mono text-xs font-semibold uppercase tracking-[.14em] text-black transition hover:bg-accent-400"
                >
                  Movie details
                </Link>
              )}
              <Link
                to="/app/movies"
                className="rounded-full border border-white/30 px-6 py-2.5 font-mono text-xs font-semibold uppercase tracking-[.14em] text-plum-700 transition hover:border-accent-500 hover:text-accent-300"
              >
                Browse
              </Link>
            </div>
          </div>
        </div>

        <div
          className="feature-selector no-scrollbar relative z-10 mt-7 flex gap-2 overflow-x-auto pb-1 pt-2"
          aria-label="Choose a featured movie"
        >
          {featuredMovies.map((movie) => (
            <button
              key={movie.movie_id}
              type="button"
              onClick={() => setSelectedId(movie.movie_id)}
              aria-label={`Feature ${movie.title}`}
              aria-pressed={selected?.movie_id === movie.movie_id}
              className={`h-16 w-11 shrink-0 overflow-hidden rounded-lg border-2 transition duration-300 hover:-translate-y-1 ${
                selected?.movie_id === movie.movie_id
                  ? 'border-accent-500 shadow-[0_0_18px_rgba(232,184,75,.45)]'
                  : 'border-transparent opacity-60 hover:opacity-100'
              }`}
            >
              <Poster movie={movie} rounded="rounded-md" />
            </button>
          ))}
        </div>

        <p className="relative z-10 mt-5 flex items-center justify-center gap-2 text-ink-faint" aria-hidden="true">
          <ArrowDown size={14} />
          <span className="mono-tag">scroll</span>
        </p>
      </section>

      <div className="cinema-data-grid">
        <div>
          <span>THE COLLECTION</span>
          <strong>{mostRated.data?.total != null ? mostRated.data.total.toLocaleString() : '—'}</strong>
          <small>Movies in the catalog</small>
        </div>
        <div>
          <span>YOUR DISCOVERY</span>
          <strong>{recs.data?.items?.length ?? '—'}</strong>
          <small>Recommendations in this selection</small>
        </div>
        <div>
          <span>THE ENGINE</span>
          <strong>NeuMF</strong>
          <small>Personalised movie discovery</small>
        </div>
      </div>

      <div className="dashboard-context flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-plum-500">
          {status.data?.method ? `Personalisation method: ${status.data.method}` : 'Curated from the MovieLens catalog'}
        </p>
        <Link
          to="/app/movies"
          className="flex items-center gap-2 rounded-lg border border-blush-300 px-4 py-2 text-sm font-semibold text-plum-600 transition hover:border-accent-500 hover:text-plum-900"
        >
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

      <MovieRow
        title={personalised ? 'Top picks for you' : 'Popular right now'}
        subtitle={recs.data ? `${recs.data.model_used} · generated in ${recs.data.generated_in_ms} ms` : undefined}
        movies={recItems} loading={recs.loading} error={recs.error} onRetry={recs.reload}
        showScore showRank emptyHint="Rate a few movies to unlock personalised recommendations."
      />

      <MovieRow title="Most rated in the dataset" subtitle="Ranked by number of training ratings"
        movies={mostRated.data?.items} loading={mostRated.loading} error={mostRated.error} onRetry={mostRated.reload} />

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
