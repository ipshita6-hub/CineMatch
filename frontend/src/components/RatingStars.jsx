import { useState } from 'react'
import { Star } from 'lucide-react'

/** Half-star rating control matching the MovieLens 0.5-5.0 scale. */
export default function RatingStars({ value = null, onChange, size = 'md', disabled = false }) {
  const [hover, setHover] = useState(null)
  const shown = hover ?? value ?? 0
  const px = size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-7 w-7' : 'h-5 w-5'

  return (
    <div className="flex items-center gap-0.5" onMouseLeave={() => setHover(null)}>
      {[1, 2, 3, 4, 5].map((star) => (
        <span key={star} className="relative">
          <Star className={`${px} text-ink-600`} />
          <span className="absolute inset-0 overflow-hidden"
                style={{ width: `${Math.max(0, Math.min(1, shown - star + 1)) * 100}%` }}>
            <Star className={`${px} fill-gold-400 text-gold-400`} />
          </span>
          {!disabled && [0.5, 1].map((half) => (
            <button
              key={half}
              type="button"
              aria-label={`Rate ${star - 1 + half} out of 5`}
              onMouseEnter={() => setHover(star - 1 + half)}
              onClick={() => onChange?.(star - 1 + half)}
              className="absolute top-0 h-full w-1/2 cursor-pointer"
              style={{ left: half === 0.5 ? 0 : '50%' }}
            />
          ))}
        </span>
      ))}
      {value != null && <span className="ml-2 text-xs font-semibold text-mist-300">{value.toFixed(1)}</span>}
    </div>
  )
}
