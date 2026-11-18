import { useState } from 'react'
import { Info, RefreshCw, Sparkles } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { movieApi, recommendationApi, userApi } from '../services/api'
import MovieCard from '../components/MovieCard'
import { EmptyState, ErrorState, Spinner } from '../components/States'

const MODELS = [
  ['neumf', 'NeuMF', 'GMF + MLP fusion — the project model'],
  ['mf', 'Matrix Factorization', 'Dot-product baseline'],
  ['hybrid', 'Hybrid re-rank', 'NeuMF blended with genre similarity and popularity'],
  ['popularity', 'Popularity', 'Non-personalised baseline'],
]
const SIZES = [10, 20, 50]

export default function Recommendations() {
  const [model, setModel] = useState('neumf')
  const [limit, setLimit] = useState(10)
  const [genre, setGenre] = useState('')

  const genres = useApi(() => movieApi.genres(), [])
  const status = useApi(() => userApi.status(), [])
  const recs = useApi(
    () => recommendationApi.mine({ model, limit, genre: genre || undefined }),
    [model, limit, genre],
  )

  const data = recs.data
  const items = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
            <Sparkles className="h-5 w-5 text-accent-400" /> My recommendations
          </h1>
          <p className="text-sm text-mist-400">
            Movies you have already rated are excluded automatically.
            {status.data?.method && ` Personalisation: ${status.data.method}.`}
          </p>
        </div>
        <button type="button" onClick={recs.reload}
          className="flex items-center gap-2 rounded-lg border border-ink-600 px-4 py-2 text-sm font-semibold text-mist-300 transition hover:border-accent-500 hover:text-white">
          <RefreshCw className={`h-4 w-4 ${recs.loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      <div className="glass space-y-4 rounded-xl p-4">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-mist-400">Model</p>
          <div className="flex flex-wrap gap-2">
            {MODELS.map(([value, label, hint]) => (
              <button key={value} type="button" onClick={() => setModel(value)} title={hint}
                className={`rounded-lg border px-3.5 py-2 text-sm font-medium transition ${
                  model === value ? 'border-accent-500 bg-accent-500/15 text-accent-200'
                                  : 'border-ink-600 text-mist-300 hover:border-mist-400'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-mist-400">Show</span>
            {SIZES.map((n) => (
              <button key={n} type="button" onClick={() => setLimit(n)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  limit === n ? 'bg-accent-500 text-white' : 'bg-ink-800 text-mist-300 hover:bg-ink-700'}`}>
                Top {n}
              </button>
            ))}
          </div>
          <select value={genre} onChange={(e) => setGenre(e.target.value)} aria-label="Filter recommendations by genre"
            className="rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-mist-200 outline-none focus:border-accent-500">
            <option value="">All genres</option>
            {(genres.data || []).map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
      </div>

      {data && (
        <div className="glass flex flex-wrap items-start gap-3 rounded-xl p-4 text-sm">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-gold-400" />
          <div className="space-y-1">
            <p className="text-mist-300">
              Served by <span className="font-semibold text-white">{data.model_used}</span> in{' '}
              {data.generated_in_ms} ms{data.cached ? ' (cached)' : ''}.
              {data.fallback_used && ` Requested ${data.model_requested}.`}
            </p>
            {data.fallback_reason && <p className="text-mist-400">{data.fallback_reason}</p>}
            {items[0]?.explanation && <p className="text-mist-400">{items[0].explanation}</p>}
          </div>
        </div>
      )}

      {recs.loading && <Spinner label="Scoring the catalog…" />}
      {recs.error && <ErrorState message={recs.error} onRetry={recs.reload} />}
      {!recs.loading && !recs.error && items.length === 0 && (
        <EmptyState title="No recommendations yet"
          hint="Rate a few movies so the model has something to learn from." />
      )}

      {items.length > 0 && (
        <div className="grid grid-cols-2 justify-items-center gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {items.map((m) => <MovieCard key={m.movie_id} movie={m} showScore rank={m.rank} />)}
        </div>
      )}
    </div>
  )
}
