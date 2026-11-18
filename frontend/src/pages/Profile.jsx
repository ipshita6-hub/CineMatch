import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Loader2, Trash2 } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { errorMessage, movieApi, userApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import MovieCard from '../components/MovieCard'
import { EmptyState, ErrorState, Spinner } from '../components/States'

export default function Profile() {
  const { user } = useAuth()
  const genres = useApi(() => movieApi.genres(), [])
  const prefs = useApi(() => userApi.preferences(), [])
  const ratings = useApi(() => userApi.ratings(), [])
  const history = useApi(() => userApi.history(), [])
  const status = useApi(() => userApi.status(), [])

  const [selected, setSelected] = useState(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  const current = selected ?? prefs.data?.preferred_genres ?? []

  const toggle = (g) =>
    setSelected(current.includes(g) ? current.filter((x) => x !== g) : [...current, g])

  const save = async () => {
    setSaving(true); setError(null); setMessage(null)
    try {
      await userApi.savePreferences({
        preferred_genres: current,
        default_model: prefs.data?.default_model || 'neumf',
      })
      setMessage('Preferences saved.')
      prefs.reload()
    } catch (err) {
      setError(errorMessage(err, 'Could not save preferences.'))
    } finally {
      setSaving(false)
    }
  }

  const removeRating = async (movieId) => {
    try {
      await userApi.deleteRating(movieId)
      ratings.reload(); status.reload()
    } catch (err) {
      setError(errorMessage(err, 'Could not remove that rating.'))
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">{user?.username}</h1>
        <p className="text-sm text-mist-400">{user?.email}</p>
      </div>

      <section className="glass rounded-xl p-5">
        <h2 className="font-semibold text-mist-200">Personalisation</h2>
        {status.loading && <Spinner />}
        {status.data && (
          <dl className="mt-3 grid gap-4 sm:grid-cols-4">
            {[
              ['Method', status.data.method],
              ['Ratings submitted', status.data.ratings_submitted],
              ['Embedding fitted', status.data.embedding_fitted ? 'Yes' : 'Not yet'],
              ['Fitted from', status.data.embedding_ratings ? `${status.data.embedding_ratings} ratings` : '—'],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-[11px] uppercase tracking-wider text-mist-400">{k}</dt>
                <dd className="mt-1 text-sm font-semibold text-mist-200">{v}</dd>
              </div>
            ))}
          </dl>
        )}
        {status.data && !status.data.embedding_fitted && (
          <p className="mt-3 text-xs text-mist-400">
            Rate at least three movies and a NeuMF user embedding will be fitted for your account
            automatically.
          </p>
        )}
      </section>

      <section className="glass rounded-xl p-5">
        <h2 className="font-semibold text-mist-200">Favourite genres</h2>
        <p className="text-xs text-mist-400">Used for filters and the hybrid re-ranker.</p>
        {genres.error && <ErrorState message={genres.error} onRetry={genres.reload} />}
        <div className="mt-4 flex flex-wrap gap-2">
          {(genres.data || []).map((g) => {
            const on = current.includes(g)
            return (
              <button key={g} type="button" onClick={() => toggle(g)}
                className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition ${
                  on ? 'border-accent-500 bg-accent-500/15 text-accent-200'
                     : 'border-ink-600 text-mist-300 hover:border-mist-400'}`}>
                {on && <Check className="h-3.5 w-3.5" />} {g}
              </button>
            )
          })}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button type="button" onClick={save} disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-400 disabled:opacity-60">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />} Save preferences
          </button>
          {message && <span className="text-sm text-teal-400">{message}</span>}
          {error && <span role="alert" className="text-sm text-accent-300">{error}</span>}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-semibold text-mist-200">Movies you rated</h2>
        {ratings.loading && <Spinner />}
        {ratings.error && <ErrorState message={ratings.error} onRetry={ratings.reload} />}
        {ratings.data?.items?.length === 0 && (
          <EmptyState title="No ratings yet"
            hint="Rate movies from the catalog to train your personal embedding."
            action={<Link to="/app/movies" className="mt-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-semibold text-white">Browse movies</Link>} />
        )}
        {ratings.data?.items?.length > 0 && (
          <div className="grid grid-cols-2 justify-items-center gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {ratings.data.items.map((m) => (
              <div key={m.movie_id} className="relative">
                <MovieCard movie={m} />
                <button type="button" aria-label={`Remove your rating of ${m.title}`}
                  onClick={() => removeRating(m.movie_id)}
                  className="absolute -right-2 -top-2 rounded-full border border-ink-600 bg-ink-900 p-1.5 text-mist-400 transition hover:border-accent-500 hover:text-accent-300">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="font-semibold text-mist-200">Recommendation history</h2>
        {history.loading && <Spinner />}
        {history.data?.items?.length === 0 && (
          <EmptyState title="Nothing served yet" hint="Your served recommendations will be logged here." />
        )}
        {history.data?.items?.length > 0 && (
          <div className="glass overflow-x-auto rounded-xl">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-mist-400">
                <tr><th className="px-4 py-3">Movie</th><th className="px-4 py-3">Model</th>
                    <th className="px-4 py-3">Rank</th><th className="px-4 py-3">Score</th>
                    <th className="px-4 py-3">When</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-700/60 text-mist-300">
                {history.data.items.slice(0, 25).map((h, i) => (
                  <tr key={`${h.movie_id}-${i}`}>
                    <td className="px-4 py-2.5">{h.title}</td>
                    <td className="px-4 py-2.5">{h.model_name}</td>
                    <td className="px-4 py-2.5">#{h.rank}</td>
                    <td className="px-4 py-2.5">{h.score?.toFixed(3)}</td>
                    <td className="px-4 py-2.5 text-mist-400">{new Date(h.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
