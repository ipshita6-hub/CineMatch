import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Check, Loader2, Sparkles } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { errorMessage, movieApi, userApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import Poster from '../components/Poster'
import RatingStars from '../components/RatingStars'
import { ErrorState, Spinner } from '../components/States'

const MIN_RATINGS = 3

export default function Onboarding() {
  const navigate = useNavigate()
  const { refresh } = useAuth()
  const [step, setStep] = useState(1)
  const [genres, setGenres] = useState([])
  const [ratings, setRatings] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const genreList = useApi(() => movieApi.genres(), [])
  const popular = useApi(
    () => movieApi.list({ sort: 'popularity', page_size: 24, min_ratings: 20000 }), [])

  const rated = useMemo(() => Object.keys(ratings).length, [ratings])

  const finish = async () => {
    setBusy(true)
    setError(null)
    try {
      const payload = {
        preferred_genres: genres,
        ratings: Object.entries(ratings).map(([movie_id, rating]) => ({
          movie_id: Number(movie_id), rating,
        })),
      }
      const res = await userApi.onboarding(payload)
      setResult(res)
      await refresh()
      setStep(3)
    } catch (err) {
      setError(errorMessage(err, 'Could not save your onboarding answers.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8 flex items-center gap-3">
        {[1, 2, 3].map((s) => (
          <div key={s} className={`h-1.5 flex-1 rounded-full ${s <= step ? 'bg-accent-500' : 'bg-ink-700'}`} />
        ))}
      </div>

      {step === 1 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-white">Which genres do you gravitate to?</h1>
          <p className="mt-1.5 text-sm text-mist-400">
            Used for filtering and for the hybrid re-ranker. Optional — the model itself learns
            from your ratings, not your genre picks.
          </p>
          {genreList.loading && <Spinner />}
          {genreList.error && <ErrorState message={genreList.error} onRetry={genreList.reload} />}
          <div className="mt-6 flex flex-wrap gap-2">
            {(genreList.data || []).map((g) => {
              const on = genres.includes(g)
              return (
                <button key={g} type="button"
                  onClick={() => setGenres(on ? genres.filter((x) => x !== g) : [...genres, g])}
                  className={`flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm font-medium transition ${
                    on ? 'border-accent-500 bg-accent-500/15 text-accent-200'
                       : 'border-ink-600 text-mist-300 hover:border-mist-400'}`}>
                  {on && <Check className="h-3.5 w-3.5" />} {g}
                </button>
              )
            })}
          </div>
          <button type="button" onClick={() => setStep(2)}
            className="mt-8 rounded-lg bg-accent-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-400">
            Continue
          </button>
        </motion.div>
      )}

      {step === 2 && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-white">Rate a few films you know</h1>
          <p className="mt-1.5 text-sm text-mist-400">
            At least {MIN_RATINGS} ratings are needed before a NeuMF user embedding can be fitted
            for your account. Rate more and the fit gets sharper.
          </p>
          {popular.loading && <Spinner />}
          {popular.error && <ErrorState message={popular.error} onRetry={popular.reload} />}
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(popular.data?.items || []).map((m) => (
              <div key={m.movie_id} className="flex gap-3 rounded-xl border border-ink-700/70 bg-ink-850 p-3">
                <div className="h-24 w-16 shrink-0 overflow-hidden rounded-lg"><Poster movie={m} rounded="rounded-none" /></div>
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-2 text-sm font-semibold text-mist-200">{m.title}</p>
                  <p className="mt-0.5 text-[11px] text-mist-400">{(m.genres || []).slice(0, 2).join(' · ')}</p>
                  <div className="mt-2">
                    <RatingStars size="sm" value={ratings[m.movie_id] ?? null}
                      onChange={(v) => setRatings({ ...ratings, [m.movie_id]: v })} />
                  </div>
                  {ratings[m.movie_id] && (
                    <button type="button" onClick={() => {
                      const next = { ...ratings }; delete next[m.movie_id]; setRatings(next)
                    }} className="mt-1 text-[11px] text-mist-400 underline hover:text-accent-300">clear</button>
                  )}
                </div>
              </div>
            ))}
          </div>
          {error && <p role="alert" className="mt-5 rounded-lg bg-accent-500/10 px-3 py-2 text-sm text-accent-300">{error}</p>}
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <button type="button" onClick={finish} disabled={busy || rated < MIN_RATINGS}
              className="flex items-center gap-2 rounded-lg bg-accent-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-400 disabled:opacity-50">
              {busy && <Loader2 className="h-4 w-4 animate-spin" />} Fit my model ({rated}/{MIN_RATINGS})
            </button>
            <button type="button" onClick={finish} disabled={busy}
              className="text-sm text-mist-400 underline hover:text-mist-200">
              Skip — use popularity recommendations for now
            </button>
          </div>
        </motion.div>
      )}

      {step === 3 && (
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
                    className="glass rounded-2xl p-8 text-center">
          <Sparkles className="mx-auto h-10 w-10 text-accent-400" />
          <h1 className="mt-4 text-2xl font-bold text-white">
            {result?.embedding_fitted ? 'Your embedding is ready' : 'You are all set'}
          </h1>
          <p className="mx-auto mt-2 max-w-lg text-sm text-mist-300">{result?.embedding_detail}</p>
          {!result?.embedding_fitted && (
            <p className="mx-auto mt-2 max-w-lg text-xs text-mist-400">
              Until then you will see popularity-based recommendations, which are not personalised.
            </p>
          )}
          <button type="button" onClick={() => navigate('/app', { replace: true })}
            className="mt-6 rounded-lg bg-accent-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-400">
            Go to my recommendations
          </button>
        </motion.div>
      )}
    </div>
  )
}
