import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Star, TrendingUp, Users } from 'lucide-react'
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
      <Link to="/app/movies" className="inline-flex items-center gap-1.5 text-sm text-mist-400 hover:text-accent-300">
        <ArrowLeft className="h-4 w-4" /> Back to browse
      </Link>

      <div className="relative overflow-hidden rounded-2xl border border-ink-700/70">
        {movie.backdrop_url && (
          <div className="absolute inset-0">
            <img src={movie.backdrop_url} alt="" aria-hidden className="h-full w-full object-cover opacity-25" />
            <div className="absolute inset-0 bg-gradient-to-r from-ink-950 via-ink-950/85 to-ink-950/40" />
          </div>
        )}
        <div className="relative flex flex-col gap-6 p-6 sm:flex-row">
          <div className="h-72 w-48 shrink-0 overflow-hidden rounded-xl border border-ink-700">
            <Poster movie={movie} rounded="rounded-none" />
          </div>
          <div className="min-w-0 flex-1 space-y-4">
            <div>
              <h1 className="text-3xl font-extrabold leading-tight text-white">{movie.title}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {(movie.genres || []).map((g) => (
                  <span key={g} className="rounded-full bg-ink-700/80 px-2.5 py-1 text-xs text-mist-300">{g}</span>
                ))}
              </div>
            </div>

            {movie.overview && <p className="max-w-2xl text-sm leading-relaxed text-mist-300">{movie.overview}</p>}
            {!movie.overview && (
              <p className="text-xs text-mist-400">
                MovieLens provides no synopsis. {movie.poster_source === 'placeholder'
                  ? 'TMDB metadata is unavailable for this title, so a genre placeholder is shown.'
                  : ''}
              </p>
            )}

            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-mist-400">Dataset average</dt>
                <dd className="mt-1 flex items-center gap-1 text-lg font-bold text-white">
                  <Star className="h-4 w-4 text-gold-400" />
                  {movie.dataset_avg_rating != null ? movie.dataset_avg_rating.toFixed(2) : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-mist-400">Ratings</dt>
                <dd className="mt-1 flex items-center gap-1 text-lg font-bold text-white">
                  <Users className="h-4 w-4 text-mist-400" />
                  {(movie.dataset_rating_count || 0).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-mist-400">Released</dt>
                <dd className="mt-1 text-lg font-bold text-white">{movie.release_year || '—'}</dd>
              </div>
              <div>
                <dt className="text-[11px] uppercase tracking-wider text-mist-400">Predicted for you</dt>
                <dd className="mt-1 flex items-center gap-1 text-lg font-bold text-accent-300">
                  <TrendingUp className="h-4 w-4" />
                  {movie.predicted_rating != null ? movie.predicted_rating.toFixed(2) : 'n/a'}
                </dd>
              </div>
            </dl>

            {movie.predicted_rating == null && (
              <p className="text-xs text-mist-400">
                A predicted rating needs a fitted user embedding — rate at least three movies.
              </p>
            )}
            {movie.predicted_rating != null && (
              <p className="text-xs text-mist-400">
                Predicted on the {movie.predicted_rating_scale?.join('–')} MovieLens scale by the
                dedicated rating model, not by the ranking score.
              </p>
            )}

            <div className="glass rounded-xl p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-mist-400">Your rating</p>
              <RatingStars size="lg" value={current} onChange={rate} disabled={saving} />
              {saving && <p className="mt-2 text-xs text-mist-400">Saving and refitting your embedding…</p>}
              {saveError && <p role="alert" className="mt-2 text-xs text-accent-300">{saveError}</p>}
            </div>
          </div>
        </div>
      </div>

      {movie.similar_movies?.length > 0 && (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-bold text-mist-200">Similar by genre</h2>
            <p className="text-xs text-mist-400">
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
