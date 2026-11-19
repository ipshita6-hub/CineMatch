import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Search, SlidersHorizontal } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { movieApi } from '../services/api'
import MovieCard from '../components/MovieCard'
import { EmptyState, ErrorState, Spinner } from '../components/States'

const SORTS = [
  ['popularity', 'Most rated'],
  ['rating', 'Highest rated'],
  ['year', 'Newest'],
  ['title', 'A-Z'],
]

export default function Browse() {
  const [search, setSearch] = useState('')
  const [debounced, setDebounced] = useState('')
  const [genre, setGenre] = useState('')
  const [sort, setSort] = useState('popularity')
  const [minYear, setMinYear] = useState('')
  const [maxYear, setMaxYear] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    const t = setTimeout(() => { setDebounced(search); setPage(1) }, 350)
    return () => clearTimeout(t)
  }, [search])

  const genres = useApi(() => movieApi.genres(), [])
  const result = useApi(
    () => movieApi.list({
      search: debounced || undefined,
      genre: genre || undefined,
      sort,
      min_year: minYear || undefined,
      max_year: maxYear || undefined,
      page,
      page_size: 24,
    }),
    [debounced, genre, sort, minYear, maxYear, page],
  )

  const items = result.data?.items || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-plum-900">Browse the catalog</h1>
        <p className="text-sm text-plum-500">
          {result.data ? `${result.data.total.toLocaleString()} movies match your filters` : 'MovieLens 20M catalog'}
        </p>
      </div>

      <div className="glass space-y-3 rounded-xl p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-plum-500" />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title…" aria-label="Search movies by title"
            className="w-full rounded-lg border border-blush-300 bg-blush-100 py-2.5 pl-10 pr-3 text-sm text-plum-700 outline-none transition placeholder:text-plum-500 focus:border-rose-500" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-plum-500" aria-hidden />
          <select value={genre} onChange={(e) => { setGenre(e.target.value); setPage(1) }} aria-label="Filter by genre"
            className="rounded-lg border border-blush-300 bg-blush-100 px-3 py-2 text-sm text-plum-700 outline-none focus:border-rose-500">
            <option value="">All genres</option>
            {(genres.data || []).map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
          <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1) }} aria-label="Sort by"
            className="rounded-lg border border-blush-300 bg-blush-100 px-3 py-2 text-sm text-plum-700 outline-none focus:border-rose-500">
            {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <input type="number" value={minYear} placeholder="From year" aria-label="Minimum release year"
            onChange={(e) => { setMinYear(e.target.value); setPage(1) }}
            className="w-28 rounded-lg border border-blush-300 bg-blush-100 px-3 py-2 text-sm text-plum-700 outline-none focus:border-rose-500" />
          <input type="number" value={maxYear} placeholder="To year" aria-label="Maximum release year"
            onChange={(e) => { setMaxYear(e.target.value); setPage(1) }}
            className="w-28 rounded-lg border border-blush-300 bg-blush-100 px-3 py-2 text-sm text-plum-700 outline-none focus:border-rose-500" />
          {(genre || minYear || maxYear || search) && (
            <button type="button" className="text-sm text-plum-500 underline hover:text-rose-700"
              onClick={() => { setGenre(''); setMinYear(''); setMaxYear(''); setSearch(''); setPage(1) }}>
              Reset
            </button>
          )}
        </div>
      </div>

      {result.loading && <Spinner label="Searching the catalog…" />}
      {result.error && <ErrorState message={result.error} onRetry={result.reload} />}
      {!result.loading && !result.error && items.length === 0 && (
        <EmptyState title="No movies match" hint="Try a broader search or clear the filters." />
      )}

      {items.length > 0 && (
        <>
          <div className="grid grid-cols-2 justify-items-center gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {items.map((m) => <MovieCard key={m.movie_id} movie={m} />)}
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1 rounded-lg border border-blush-300 px-3 py-2 text-sm text-plum-600 transition hover:border-rose-500 disabled:opacity-40">
              <ChevronLeft className="h-4 w-4" /> Previous
            </button>
            <span className="text-sm text-plum-500">Page {result.data.page} of {result.data.pages}</span>
            <button type="button" disabled={page >= result.data.pages} onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 rounded-lg border border-blush-300 px-3 py-2 text-sm text-plum-600 transition hover:border-rose-500 disabled:opacity-40">
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </>
      )}
    </div>
  )
}
