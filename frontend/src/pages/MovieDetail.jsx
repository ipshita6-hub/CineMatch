import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Star, TrendingUp, Users } from 'lucide-react'
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'framer-motion'
import { useApi } from '../hooks/useApi'
import { errorMessage, movieApi, userApi } from '../services/api'
import Poster from '../components/Poster'
import MovieCard from '../components/MovieCard'
import RatingStars from '../components/RatingStars'
import { ErrorState, Spinner } from '../components/States'

export default function MovieDetail() {
  const { movieId } = useParams()
  const detail = useApi(() => movieApi.detail(movieId), [movieId])
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState(null)
  const [saved, setSaved] = useState(null)
  const reduceMotion = useReducedMotion()
  const pointerX = useMotionValue(0)
  const pointerY = useMotionValue(0)
  const rotateY = useSpring(useTransform(pointerX, [-0.5, 0.5], [-9, 9]), { stiffness: 100, damping: 18 })
  const rotateX = useSpring(useTransform(pointerY, [-0.5, 0.5], [7, -7]), { stiffness: 100, damping: 18 })

  const movie = detail.data

  const rate = async (value) => {
    setSaving(true)
    setSaveError(null)
    try {
      await userApi.rate({ movie_id: Number(movieId), rating: value })
      setSaved(value)
      detail.reload()
    } catch (err) {
      setSaveError(errorMessage(err, 'Could not save your rating.'))
    } finally {
      setSaving(false)
    }
  }

  if (detail.loading) return <Spinner label="Loading movie…" />
  if (detail.error) return <ErrorState message={detail.error} onRetry={detail.reload} />
  if (!movie) return null

  const current = saved ?? movie.user_rating ?? null

  return (
    <div className="space-y-8">
      <Link to="/app/movies" className="inline-flex items-center gap-1.5 text-sm text-plum-500 hover:text-rose-700">
        <ArrowLeft className="h-4 w-4" /> Back to browse
      </Link>

      <div className="movie-showcase relative overflow-hidden rounded-2xl border border-blush-200/70">
        {(movie.backdrop_url || movie.poster_url) && (
          <div className="absolute inset-0">
            <img src={movie.backdrop_url || movie.poster_url} alt="" aria-hidden className="h-full w-full object-cover opacity-60" />
            <div className="absolute inset-0 bg-gradient-to-r from-blush-50 via-blush-50/85 to-blush-50/40" />
          </div>
        )}
        <div className="relative grid gap-8 p-6 lg:grid-cols-[1fr_1.05fr_1fr] lg:items-center lg:p-10">
          <div className="min-w-0 space-y-4">
            <div>
              <p className="mb-3 text-xs font-bold uppercase tracking-[.2em] text-rose-300">Movie spotlight</p>
              <h1 className="text-3xl font-extrabold leading-tight text-plum-900">{movie.title}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {(movie.genres || []).map((g) => (
                  <span key={g} className="rounded-full bg-blush-200/80 px-2.5 py-1 text-xs text-plum-600">{g}</span>
                ))}
              </div>
            </div>

            {movie.overview && <p className="max-w-2xl text-sm leading-relaxed text-plum-600">{movie.overview}</p>}
            {!movie.overview && (
              <p className="text-xs text-plum-500">
                MovieLens provides no synopsis. {movie.poster_source === 'placeholder'
                  ? 'TMDB metadata is unavailable for this title, so a genre placeholder is shown.'
                  : ''}
              </p>
            )}
          </div>
          <div className="movie-poster-stage" onPointerMove={(event) => { if (reduceMotion || event.pointerType === 'touch') return; const rect = event.currentTarget.getBoundingClientRect(); pointerX.set((event.clientX - rect.left) / rect.width - 0.5); pointerY.set((event.clientY - rect.top) / rect.height - 0.5) }} onPointerLeave={() => { pointerX.set(0); pointerY.set(0) }}>
            <span className="movie-poster-word" aria-hidden="true">{movie.genres?.[0] || 'CINEMA'}</span>
            <motion.div key={movie.movie_id} initial={reduceMotion ? false : { opacity: 0, y: 55, rotate: 5 }} animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ duration: 0.65, type: 'spring', bounce: 0.2 }} style={reduceMotion ? undefined : { rotateX, rotateY }} className="movie-poster-float">
              <div className="movie-poster-art"><Poster movie={movie} rounded="rounded-xl" /></div>
            </motion.div>
            <span className="movie-poster-shadow" aria-hidden="true" />
          </div>
          <div className="min-w-0 space-y-5">
            <p className="text-xs font-bold uppercase tracking-[.2em] text-rose-300">Movie details</p>
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-plum-500">Dataset average</dt>
                <dd className="mt-1 flex items-center gap-1 text-lg font-bold text-plum-900">
                  <Star className="h-4 w-4 text-gold-600" />
                  {movie.dataset_avg_rating != null ? movie.dataset_avg_rating.toFixed(2) : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-plum-500">Ratings</dt>
                <dd className="mt-1 flex items-center gap-1 text-lg font-bold text-plum-900">
                  <Users className="h-4 w-4 text-plum-500" />
                  {(movie.dataset_rating_count || 0).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-plum-500">Released</dt>
                <dd className="mt-1 text-lg font-bold text-plum-900">{movie.release_year || '—'}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-plum-500">Predicted for you</dt>
                <dd className="mt-1 flex items-center gap-1 text-lg font-bold text-rose-700">
                  <TrendingUp className="h-4 w-4" />
                  {movie.predicted_rating != null ? movie.predicted_rating.toFixed(2) : 'n/a'}
                </dd>
              </div>
            </dl>

            {movie.predicted_rating == null && (
              <p className="text-xs text-plum-500">
                A predicted rating needs a fitted user embedding — rate at least three movies.
              </p>
            )}
            {movie.predicted_rating != null && (
              <p className="text-xs text-plum-500">
                Predicted on the {movie.predicted_rating_scale?.join('–')} MovieLens scale by the
                dedicated rating model, not by the ranking score.
              </p>
            )}

            <div className="glass rounded-xl p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-plum-500">Your rating</p>
              <RatingStars size="lg" value={current} onChange={rate} disabled={saving} />
              {saving && <p className="mt-2 text-xs text-plum-500">Saving and refitting your embedding…</p>}
              {saveError && <p role="alert" className="mt-2 text-xs text-rose-700">{saveError}</p>}
            </div>
          </div>
        </div>
      </div>

      {movie.similar_movies?.length > 0 && (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-bold text-plum-700">Similar by genre</h2>
            <p className="text-xs text-plum-500">
              Content-based: cosine similarity over MovieLens genre vectors — not a NeuMF output.
            </p>
          </div>
          <div className="no-scrollbar flex gap-4 overflow-x-auto pb-2">
            {movie.similar_movies.map((m) => <MovieCard key={m.movie_id} movie={m} />)}
          </div>
        </section>
      )}
    </div>
  )
}
