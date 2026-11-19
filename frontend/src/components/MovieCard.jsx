import { Link } from 'react-router-dom'
import { Star, TrendingUp } from 'lucide-react'
import Poster from './Poster'

export default function MovieCard({ movie, showScore = false, rank = null, compact = false }) {
  const year = movie.release_year
  return (
    <Link
      to={`/movies/${movie.movie_id}`}
      className={`card-hover group relative block overflow-hidden rounded-xl border border-blush-200/70 bg-card ${
        compact ? 'w-36' : 'w-44'
      } shrink-0`}
    >
      <div className={`relative ${compact ? 'h-52' : 'h-64'} overflow-hidden`}>
        <Poster movie={movie} rounded="rounded-none" />
        {rank != null && (
          <span className="absolute left-2 top-2 rounded-md bg-scrim-900/90 px-2 py-0.5 text-xs font-bold text-rose-300">
            #{rank}
          </span>
        )}
        {movie.user_rating != null && (
          <span className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-gold-400/90 px-1.5 py-0.5 text-[11px] font-bold text-plum-900">
            <Star className="h-3 w-3 fill-current" /> {movie.user_rating}
          </span>
        )}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-scrim-900 to-transparent" />
      </div>

      <div className="space-y-1 p-3">
        <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-plum-700 group-hover:text-plum-900">
          {movie.title}
        </h3>
        <div className="flex items-center gap-2 text-[11px] text-plum-500">
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
          <div className="pt-1 text-[11px] font-medium text-rose-700">
            score {movie.score.toFixed(3)}
          </div>
        )}
        <div className="flex flex-wrap gap-1 pt-1">
          {(movie.genres || []).slice(0, 2).map((g) => (
            <span key={g} className="rounded-full bg-blush-200/80 px-2 py-0.5 text-[10px] text-plum-600">
              {g}
            </span>
          ))}
        </div>
      </div>
    </Link>
  )
}
