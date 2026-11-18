import { useState } from 'react'
import { Film } from 'lucide-react'

/**
 * MovieLens ships no artwork. When TMDB metadata is configured we show the
 * real poster; otherwise we draw a deterministic genre-derived placeholder.
 * We never show an unrelated image in place of a missing one.
 */
const GENRE_COLORS = {
  Action: ['#7f1d1d', '#ef4444'],
  Adventure: ['#78350f', '#f59e0b'],
  Animation: ['#164e63', '#22d3ee'],
  Children: ['#134e4a', '#2dd4bf'],
  Comedy: ['#713f12', '#facc15'],
  Crime: ['#1f2937', '#64748b'],
  Documentary: ['#1e3a5f', '#60a5fa'],
  Drama: ['#4c1d95', '#a78bfa'],
  Fantasy: ['#581c87', '#c084fc'],
  'Film-Noir': ['#0f172a', '#475569'],
  Horror: ['#450a0a', '#dc2626'],
  IMAX: ['#083344', '#06b6d4'],
  Musical: ['#831843', '#f472b6'],
  Mystery: ['#1e1b4b', '#818cf8'],
  Romance: ['#881337', '#fb7185'],
  'Sci-Fi': ['#0c4a6e', '#38bdf8'],
  Thriller: ['#3b0764', '#8b5cf6'],
  War: ['#365314', '#84cc16'],
  Western: ['#7c2d12', '#fb923c'],
}

function gradientFor(genres = [], title = '') {
  const match = genres.find((g) => GENRE_COLORS[g])
  if (match) return GENRE_COLORS[match]
  let hash = 0
  for (let i = 0; i < title.length; i += 1) hash = (hash * 31 + title.charCodeAt(i)) % 360
  return [`hsl(${hash}, 42%, 16%)`, `hsl(${(hash + 48) % 360}, 58%, 42%)`]
}

export default function Poster({ movie, className = '', rounded = 'rounded-xl' }) {
  const [failed, setFailed] = useState(false)
  const genres = movie?.genres || []
  const [from, to] = gradientFor(genres, movie?.title || '')
  const showImage = movie?.poster_url && !failed

  if (showImage) {
    return (
      <img
        src={movie.poster_url}
        alt={`Poster for ${movie.title}`}
        loading="lazy"
        onError={() => setFailed(true)}
        className={`${className} ${rounded} h-full w-full object-cover`}
      />
    )
  }

  return (
    <div
      role="img"
      aria-label={`${movie?.title || 'Movie'} — no poster available, genre placeholder`}
      className={`${className} ${rounded} relative flex h-full w-full flex-col items-center justify-center overflow-hidden p-3 text-center`}
      style={{ background: `linear-gradient(145deg, ${from}, ${to})` }}
    >
      <div className="absolute inset-0 opacity-25"
           style={{ backgroundImage: 'radial-gradient(circle at 30% 20%, rgba(255,255,255,.35), transparent 55%)' }} />
      <Film className="relative mb-2 h-7 w-7 text-white/70" aria-hidden />
      <span className="relative line-clamp-3 text-[11px] font-semibold leading-tight text-white/90">
        {movie?.title}
      </span>
      {genres[0] && (
        <span className="relative mt-1 text-[9px] uppercase tracking-widest text-white/60">
          {genres[0]}
        </span>
      )}
    </div>
  )
}
