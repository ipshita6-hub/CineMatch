import { useRef } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import MovieCard from './MovieCard'
import { EmptyState, ErrorState, SkeletonRow } from './States'

export default function MovieRow({
  title, subtitle, movies, loading, error, onRetry, showScore = false, showRank = false,
  emptyHint,
}) {
  const scroller = useRef(null)
  const scroll = (dir) => {
    scroller.current?.scrollBy({ left: dir * 520, behavior: 'smooth' })
  }

  return (
    <section className="movie-shelf space-y-4">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-plum-700">{title}</h2>
          {subtitle && <p className="mt-1 text-xs text-plum-500">{subtitle}</p>}
        </div>
        {!loading && !error && movies?.length > 4 && (
          <div className="hidden gap-1 sm:flex">
            <button type="button" aria-label={`Scroll ${title} left`} onClick={() => scroll(-1)}
              className="rounded-lg border border-blush-200 p-1.5 text-plum-600 transition hover:border-rose-500 hover:text-plum-900">
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button type="button" aria-label={`Scroll ${title} right`} onClick={() => scroll(1)}
              className="rounded-lg border border-blush-200 p-1.5 text-plum-600 transition hover:border-rose-500 hover:text-plum-900">
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {loading && <SkeletonRow />}
      {!loading && error && <ErrorState message={error} onRetry={onRetry} />}
      {!loading && !error && (!movies || movies.length === 0) && (
        <EmptyState title="No movies to show" hint={emptyHint} />
      )}
      {!loading && !error && movies?.length > 0 && (
        <div ref={scroller} className="no-scrollbar flex gap-4 overflow-x-auto pb-2">
          {movies.map((m, i) => (
            <div key={m.movie_id} className="shelf-item" style={{ '--item-delay': `${Math.min(i, 7) * 55}ms` }}><MovieCard movie={m} showScore={showScore}
                       rank={showRank ? m.rank ?? i + 1 : null} /></div>
          ))}
        </div>
      )}
    </section>
  )
}
