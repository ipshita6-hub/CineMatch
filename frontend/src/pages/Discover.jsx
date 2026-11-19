import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Info, Search } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { movieApi, recommendationApi, userApi } from '../services/api'
import MovieRow from '../components/MovieRow'

export default function Discover() {
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

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-plum-900">Discover</h1>
          <p className="text-sm text-plum-500">
            {status.data?.method
              ? `Personalisation method: ${status.data.method}`
              : 'Loading your personalisation status…'}
          </p>
        </div>
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
