import { Link } from 'react-router-dom'
import { ArrowUpRight, Star, TrendingUp } from 'lucide-react'
import Poster from './Poster'

/**
 * A poster card.
 *
 * Width is fluid rather than a fixed 11rem: the card has to work both inside
 * MovieRow's horizontal scroller and inside Browse's grid, and the old fixed
 * width was what forced cards to overflow on narrow screens. The poster uses
 * the real 2:3 ratio so it scales with the card instead of being pinned to a
 * fixed height.
 *
 * Stats are set in the mono face, matching the reference's instrument-panel
 * voice. The formatting is unchanged — tests assert on "4.18" and "63,366".
 */
export default function MovieCard({ movie, showScore = false, rank = null, compact = false }) {
  const year = movie.release_year
  const width = compact
    ? 'w-[clamp(7.5rem,32vw,9rem)]'
    : 'w-[clamp(8.5rem,40vw,11rem)]'

  return (
    <Link
      to={`/app/movies/${movie.movie_id}`}
      className={`card-hover group relative block shrink-0 overflow-hidden rounded-2xl border border-white/10 ${width}`}
    >
      <div className="relative aspect-[2/3] overflow-hidden">
        <Poster movie={movie} rounded="rounded-none" />

        {rank != null && (
          <span className="absolute left-2 top-2 rounded-md bg-scrim-900/90 px-2 py-0.5 font-mono text-[11px] font-semibold tabular-nums text-accent-300">
            #{rank}
          </span>
        )}

        {movie.user_rating != null && (
          <span className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-gold-400/90 px-1.5 py-0.5 text-[11px] font-bold text-black">
            <Star className="h-3 w-3 fill-current" /> {movie.user_rating}
          </span>
        )}

        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-scrim-900 to-transparent" />
        <span
          className="movie-card-action absolute bottom-3 right-3 grid h-9 w-9 place-items-center rounded-full border border-accent-500/40 bg-black/50 text-accent-300 backdrop-blur-md"
          aria-hidden="true"
        >
          <ArrowUpRight size={16} />
        </span>
      </div>

      <div className="space-y-1.5 p-3.5">
        <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-plum-700 group-hover:text-plum-900">
          {movie.title}
        </h3>

        <div className="flex items-center gap-2 font-mono text-[10.5px] tabular-nums text-plum-500">
          {year && <span>{year}</span>}
          {movie.dataset_avg_rating != null && (
            <span className="flex items-center gap-0.5">
              <Star className="h-3 w-3 text-gold-600" />
              {movie.dataset_avg_rating.toFixed(2)}
            </span>
          )}
          {movie.dataset_rating_count > 0 && (
            <span className="flex items-center gap-0.5">
              <TrendingUp className="h-3 w-3" />
              {movie.dataset_rating_count.toLocaleString()}
            </span>
          )}
        </div>

        {showScore && movie.score != null && (
          <div className="pt-1 font-mono text-[10.5px] font-medium tabular-nums text-accent-400">
            score {movie.score.toFixed(3)}
          </div>
        )}

        <div className="flex flex-wrap gap-1 pt-1">
          {(movie.genres || []).slice(0, 2).map((g) => (
            <span key={g} className="rounded-full border border-white/8 bg-white/5 px-2 py-0.5 text-[10px] text-plum-600">
              {g}
            </span>
          ))}
        </div>
      </div>
    </Link>
  )
}
