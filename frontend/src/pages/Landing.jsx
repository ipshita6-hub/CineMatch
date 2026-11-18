import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Brain, GitCompare, Layers, Sparkles, Target } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { metricsApi, movieApi } from '../services/api'
import Poster from '../components/Poster'
import { NotEvaluated } from '../components/States'

const fmt = (v, d = 4) => (typeof v === 'number' ? v.toFixed(d) : null)

export default function Landing() {
  const { data: metrics } = useApi(() => metricsApi.models(), [])
  const { data: featured } = useApi(
    () => movieApi.list({ sort: 'popularity', page_size: 12, min_ratings: 10000 }), [])

  const models = metrics?.models || {}
  const neumf = models.NeuMF
  const mf = models.MatrixFactorization
  const pop = models.Popularity

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-300 font-black text-ink-950">N</span>
          <span className="font-extrabold tracking-tight">Cine<span className="text-accent-400">NeuMF</span></span>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/login" className="rounded-lg px-4 py-2 text-sm font-semibold text-mist-300 transition hover:text-white">Sign in</Link>
          <Link to="/register" className="rounded-lg bg-accent-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-400">Create account</Link>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-10 lg:grid-cols-[1.05fr_1fr] lg:items-center">
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <span className="inline-flex items-center gap-2 rounded-full border border-ink-700 bg-ink-850 px-3 py-1 text-xs font-medium text-mist-300">
            <Sparkles className="h-3.5 w-3.5 text-accent-400" />
            Neural Collaborative Filtering · He et al., WWW 2017
          </span>
          <h1 className="mt-5 text-4xl font-extrabold leading-[1.1] tracking-tight text-white sm:text-5xl">
            Recommendations learned from<br />
            <span className="bg-gradient-to-r from-accent-400 to-gold-400 bg-clip-text text-transparent">
              20 million real ratings
            </span>
          </h1>
          <p className="mt-4 max-w-xl text-mist-300">
            A NeuMF model — a generalized matrix-factorization branch fused with a multi-layer
            perceptron — trained on MovieLens 20M, served through FastAPI, and benchmarked
            against both a matrix-factorization and a popularity baseline on identical
            candidate sets.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to="/register" className="flex items-center gap-2 rounded-lg bg-accent-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent-400">
              Get recommendations <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/login" className="rounded-lg border border-ink-600 px-5 py-3 text-sm font-semibold text-mist-200 transition hover:border-accent-500 hover:text-white">
              I already have an account
            </Link>
          </div>

          <dl className="mt-9 grid grid-cols-3 gap-4 border-t border-ink-700/60 pt-6">
            {[
              ['Held-out users evaluated', neumf?.evaluated_users?.toLocaleString()],
              ['NeuMF HR@10', fmt(neumf?.['HR@10'])],
              ['NeuMF NDCG@10', fmt(neumf?.['NDCG@10'])],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[11px] uppercase tracking-wider text-mist-400">{label}</dt>
                <dd className="mt-1 text-xl font-bold text-white">{value ?? <NotEvaluated />}</dd>
              </div>
            ))}
          </dl>
        </motion.div>

        <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="grid grid-cols-4 gap-3">
          {(featured?.items || []).slice(0, 12).map((m, i) => (
            <div key={m.movie_id}
                 className={`overflow-hidden rounded-lg border border-ink-700/70 ${i % 5 === 0 ? 'row-span-2 h-full' : 'h-40'}`}>
              <Poster movie={m} rounded="rounded-none" />
            </div>
          ))}
          {!featured && Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton h-40 rounded-lg" />
          ))}
        </motion.div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-7xl px-4 py-14">
        <h2 className="text-2xl font-bold text-white">How the engine works</h2>
        <p className="mt-2 max-w-2xl text-sm text-mist-400">
          Classical collaborative filtering scores a user-item pair with a fixed inner product.
          NeuMF keeps that linear view and adds a learned non-linear one, then fuses both.
        </p>
        <div className="mt-7 grid gap-4 md:grid-cols-3">
          {[
            { icon: Layers, title: 'GMF branch',
              body: 'User and item embeddings combined element-wise — the generalization of matrix factorization that captures linear interaction structure.' },
            { icon: Brain, title: 'MLP branch',
              body: 'A second, independent pair of embeddings is concatenated and passed through fully-connected ReLU layers that learn arbitrary interaction functions.' },
            { icon: Target, title: 'NeuMF fusion',
              body: 'Both representations are concatenated into a final prediction layer, trained with binary cross-entropy against sampled unobserved movies.' },
          ].map(({ icon: Icon, title, body }) => (
            <div key={title} className="glass rounded-xl p-5">
              <Icon className="h-6 w-6 text-accent-400" aria-hidden />
              <h3 className="mt-3 font-semibold text-mist-200">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-mist-400">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Model comparison */}
      <section className="mx-auto max-w-7xl px-4 pb-20">
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center gap-2">
            <GitCompare className="h-5 w-5 text-accent-400" />
            <h2 className="text-lg font-bold text-white">Measured against its baselines</h2>
          </div>
          <p className="mt-1 text-xs text-mist-400">
            {metrics?.protocol
              ? `Leave-one-out, ${metrics.protocol.candidates_per_user} candidates per user, identical candidate sets for every model.`
              : 'Run the evaluation suite to populate these numbers.'}
          </p>
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-mist-400">
                <tr><th className="pb-2">Model</th><th className="pb-2">HR@10</th>
                    <th className="pb-2">NDCG@10</th><th className="pb-2">ROC-AUC</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-700/60">
                {[['Popularity', pop], ['Matrix Factorization', mf], ['NeuMF', neumf]].map(([name, m]) => (
                  <tr key={name} className={name === 'NeuMF' ? 'text-white' : 'text-mist-300'}>
                    <td className="py-2.5 font-semibold">{name}</td>
                    <td className="py-2.5">{fmt(m?.['HR@10']) ?? <NotEvaluated />}</td>
                    <td className="py-2.5">{fmt(m?.['NDCG@10']) ?? <NotEvaluated />}</td>
                    <td className="py-2.5">{fmt(m?.ROC_AUC) ?? <NotEvaluated />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {metrics?.improvements?.['NeuMF_vs_MatrixFactorization_HR@10_pct'] != null && (
            <p className="mt-4 text-sm text-mist-300">
              NeuMF improves HR@10 by{' '}
              <span className="font-bold text-accent-300">
                {metrics.improvements['NeuMF_vs_MatrixFactorization_HR@10_pct']}%
              </span>{' '}
              over matrix factorization and{' '}
              <span className="font-bold text-accent-300">
                {metrics.improvements['NeuMF_vs_Popularity_HR@10_pct']}%
              </span>{' '}
              over the popularity baseline.
            </p>
          )}
        </div>
      </section>
    </div>
  )
}
