import { useMemo, useState } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Blend, Database, FlaskConical, Gauge, LayoutGrid, Layers, TrendingUp } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { metricsApi } from '../services/api'
import ChartCard, { DataTable, StatTile } from '../charts/ChartCard'
import { AXIS, CURVE, GRID, LABELS, SEQ, SERIES, SERIES_ORDER, axisProps, tooltipStyle } from '../charts/theme'
import { ErrorState, NotEvaluated, Spinner } from '../components/States'

const TABS = [
  ['dataset', 'Dataset', Database],
  ['performance', 'Model performance', TrendingUp],
  ['training', 'Training', Gauge],
  ['recommendations', 'Recommendation analytics', LayoutGrid],
  ['model', 'Model information', Layers],
  ['experiments', 'Experiments', FlaskConical],
  ['hybrid', 'Hybrid re-ranking', Blend],
]

const num = (v, d = 4) => (typeof v === 'number' ? v.toFixed(d) : null)
const int = (v) => (typeof v === 'number' ? v.toLocaleString() : null)
const Val = ({ v, digits = 4 }) => (num(v, digits) != null ? <>{num(v, digits)}</> : <NotEvaluated />)

export default function Analytics() {
  const [tab, setTab] = useState('dataset')
  const metrics = useApi(() => metricsApi.models(), [])
  const eda = useApi(() => metricsApi.eda(), [])
  const training = useApi(() => metricsApi.training(), [])
  const info = useApi(() => metricsApi.modelInfo(), [])
  const experiments = useApi(() => metricsApi.experiments(), [])
  const latency = useApi(() => metricsApi.latency(), [])

  const models = metrics.data?.models || {}
  const present = SERIES_ORDER.filter((m) => models[m])

  const comparison = useMemo(
    () => present.map((m) => ({
      name: LABELS[m], key: m,
      'HR@10': models[m]['HR@10'], 'NDCG@10': models[m]['NDCG@10'],
      'ROC-AUC': models[m].ROC_AUC, MRR: models[m].MRR,
      'Precision@10': models[m]['Precision@10'], 'Recall@10': models[m]['Recall@10'],
    })),
    [models, present],
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-plum-900">ML analytics</h1>
        <p className="text-sm text-plum-500">
          {metrics.data?.generated_at
            ? `Every figure comes from the evaluation run of ${new Date(metrics.data.generated_at).toLocaleString()}. Metrics that were never computed read "Not evaluated".`
            : 'Loading the evaluation artifacts…'}
        </p>
        {metrics.data?.dataset_note && (
          <p className="mt-2 rounded-lg border border-gold-600/25 bg-gold-600/10 px-3 py-2 text-xs text-gold-600">
            {metrics.data.dataset_note}
          </p>
        )}
      </div>

      <div className="no-scrollbar flex gap-2 overflow-x-auto border-b border-blush-200/60 pb-px">
        {TABS.map(([key, label, Icon]) => (
          <button key={key} type="button" onClick={() => setTab(key)}
            className={`flex shrink-0 items-center gap-1.5 rounded-t-lg px-3.5 py-2.5 text-sm font-medium transition ${
              tab === key ? 'border-b-2 border-rose-500 text-plum-900' : 'text-plum-500 hover:text-plum-700'}`}>
            <Icon className="h-4 w-4" aria-hidden /> {label}
          </button>
        ))}
      </div>

      {tab === 'dataset' && <DatasetTab eda={eda} metrics={metrics} />}
      {tab === 'performance' && (
        <PerformanceTab metrics={metrics} comparison={comparison} present={present} latency={latency} />
      )}
      {tab === 'training' && <TrainingTab training={training} />}
      {tab === 'recommendations' && <RecommendationTab metrics={metrics} />}
      {tab === 'model' && <ModelTab info={info} />}
      {tab === 'experiments' && <ExperimentTab experiments={experiments} />}
      {tab === 'hybrid' && <HybridTab metrics={metrics} />}
    </div>
  )
}

/* ------------------------------------------------------------------ dataset */
function DatasetTab({ eda, metrics }) {
  if (eda.loading) return <Spinner label="Loading dataset analysis…" />
  if (eda.error) return <ErrorState message={eda.error} onRetry={eda.reload} />
  const d = eda.data
  if (!d || d.status === 'Not evaluated') {
    return <ErrorState message="No EDA artifact. Run the preprocessing pipeline first." />
  }

  const shape = metrics.data?.dataset_shape
  const ratingDist = (d.rating_distribution || []).map((r) => ({
    rating: r.rating.toFixed(1), count: r.count, percentage: r.percentage,
  }))
  const genreDist = (d.genre_distribution || []).filter((g) => g.genre !== '(no genres listed)').slice(0, 18)
  const overTime = (d.ratings_over_time || []).filter((_, i, a) => a.length < 60 || i % 2 === 0)
  const userHist = (d.user_activity_histogram || []).filter((b) => b.count > 0)
  const movieHist = (d.movie_popularity_histogram || []).filter((b) => b.count > 0)

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Total ratings" value={int(d.sparsity?.observed_interactions)} hint="after cleaning and the ≥5 activity filter" />
        <StatTile label="Unique users" value={int(d.sparsity?.num_users)} />
        <StatTile label="Unique movies" value={int(d.sparsity?.num_movies)} hint={`${int(d.raw?.movies_in_movies_csv)} in the raw catalog`} />
        <StatTile label="Average rating" value={d.rating_summary?.mean} hint={`median ${d.rating_summary?.median} · σ ${d.rating_summary?.std}`} />
        <StatTile label="Sparsity" value={`${d.sparsity?.sparsity_pct}%`} hint={`${int(d.sparsity?.dense_cells)} cells if dense`} accent />
        <StatTile label="Ratings per user" value={`${Math.round(d.user_activity?.['50%'])} median`} hint={`min ${d.user_activity?.min} · max ${int(d.user_activity?.max)}`} />
        <StatTile label="Ratings per movie" value={`${Math.round(d.movie_activity?.['50%'])} median`} hint={`min ${d.movie_activity?.min} · max ${int(d.movie_activity?.max)}`} />
        <StatTile label="Positive rate" value={`${d.implicit_feedback?.positive_rate_pct}%`} hint={`rating ≥ ${d.implicit_feedback?.positive_rating_threshold} counts as positive`} />
      </div>

      <ChartCard title="Rating distribution"
        description="How the 20M explicit ratings fall across the half-star MovieLens scale."
        table={<DataTable columns={['Rating', 'Count', 'Share']}
          rows={ratingDist.map((r) => [r.rating, r.count.toLocaleString(), `${r.percentage.toFixed(2)}%`])} />}>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={ratingDist} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="rating" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={(v) => `${(v / 1e6).toFixed(1)}M`} />
            <Tooltip {...tooltipStyle} formatter={(v) => [v.toLocaleString(), 'ratings']} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={38}>
              {ratingDist.map((r, i) => (
                <Cell key={i} fill={SEQ[Math.min(SEQ.length - 1, Math.floor((i / ratingDist.length) * SEQ.length))]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Movies per genre" description="Genre labels are multi-valued, so a movie counts once per genre."
          table={<DataTable columns={['Genre', 'Movies']} rows={genreDist.map((g) => [g.genre, g.movie_count.toLocaleString()])} />}>
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={genreDist} layout="vertical" margin={{ left: 60, right: 16, top: 4, bottom: 4 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" {...axisProps} />
              <YAxis type="category" dataKey="genre" width={90} {...axisProps} />
              <Tooltip {...tooltipStyle} formatter={(v) => [v.toLocaleString(), 'movies']} />
              <Bar dataKey="movie_count" fill={SERIES.Popularity} radius={[0, 4, 4, 0]} maxBarSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Rating activity over time" description="Monthly rating volume across the dataset's 1995–2015 span."
          table={<DataTable columns={['Month', 'Ratings']} rows={overTime.slice(-24).map((m) => [m.month, m.count.toLocaleString()])} />}>
          <ResponsiveContainer width="100%" height={340}>
            <AreaChart data={overTime} margin={{ top: 8, right: 12, bottom: 4, left: 8 }}>
              <defs>
                <linearGradient id="timeFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={SERIES.Popularity} stopOpacity={0.5} />
                  <stop offset="100%" stopColor={SERIES.Popularity} stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="month" {...axisProps} minTickGap={48} />
              <YAxis {...axisProps} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip {...tooltipStyle} formatter={(v) => [v.toLocaleString(), 'ratings']} />
              <Area type="monotone" dataKey="count" stroke={SERIES.Popularity} strokeWidth={2} fill="url(#timeFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="User activity distribution" description="Users bucketed by how many movies they rated (log-spaced buckets)."
          table={<DataTable columns={['≥ ratings', 'Users']} rows={userHist.map((b) => [b.bin_start, b.count.toLocaleString()])} />}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={userHist} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="bin_start" {...axisProps} />
              <YAxis {...axisProps} tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v)} />
              <Tooltip {...tooltipStyle} labelFormatter={(l) => `≥ ${l} ratings`} formatter={(v) => [v.toLocaleString(), 'users']} />
              <Bar dataKey="count" fill={SERIES.MatrixFactorization} radius={[4, 4, 0, 0]} maxBarSize={22} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Movie popularity distribution" description="The long tail: most movies receive comparatively few ratings."
          table={<DataTable columns={['≥ ratings', 'Movies']} rows={movieHist.map((b) => [b.bin_start, b.count.toLocaleString()])} />}>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={movieHist} margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="bin_start" {...axisProps} />
              <YAxis {...axisProps} />
              <Tooltip {...tooltipStyle} labelFormatter={(l) => `≥ ${l} ratings`} formatter={(v) => [v.toLocaleString(), 'movies']} />
              <Bar dataKey="count" fill={SERIES.NeuMF} radius={[4, 4, 0, 0]} maxBarSize={22} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {shape && (
        <ChartCard title="Leave-one-out split" description="Each user's final interaction is the test item; the one before it is validation.">
          <DataTable columns={['Partition', 'Rows', 'Users']}
            rows={[['Train', int(shape.train_rows), int(shape.num_users)],
                   ['Validation', int(shape.validation_rows), int(shape.num_users)],
                   ['Test', int(shape.test_rows), int(shape.num_users)]]} />
        </ChartCard>
      )}
    </div>
  )
}

/* -------------------------------------------------------------- performance */
function PerformanceTab({ metrics, comparison, present, latency }) {
  if (metrics.loading) return <Spinner label="Loading evaluation results…" />
  if (metrics.error) return <ErrorState message={metrics.error} onRetry={metrics.reload} />
  if (metrics.data?.status === 'Not evaluated') {
    return <ErrorState message={metrics.data.detail} />
  }

  const models = metrics.data?.models || {}
  const rating = metrics.data?.rating_prediction || {}
  const improvements = metrics.data?.improvements || {}
  const proto = metrics.data?.protocol

  const rmseRows = rating.RMSE != null ? [
    { name: 'Rating predictor', RMSE: rating.RMSE, key: 'NeuMF' },
    { name: 'Item-mean baseline', RMSE: rating.baselines?.item_mean?.RMSE, key: 'MatrixFactorization' },
    { name: 'Global-mean baseline', RMSE: rating.baselines?.global_mean?.RMSE, key: 'Popularity' },
  ] : []

  const live = latency.data?.live || {}
  const recRoute = Object.entries(live).find(([k]) => k.includes('/recommendations'))

  return (
    <div className="space-y-5">
      {proto && (
        <div className="glass rounded-xl p-4 text-xs leading-relaxed text-plum-500">
          <span className="font-semibold text-plum-700">Protocol.</span>{' '}
          {proto.split} · {proto.relevance} · {proto.candidates_per_user} candidates per user
          ({proto.negatives_per_user} sampled negatives) · identical candidate sets for every model ·
          ties broken {proto.tie_breaking}. {proto.precision_recall_note}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="NeuMF HR@10" value={num(models.NeuMF?.['HR@10'])} accent
          hint={improvements['NeuMF_vs_MatrixFactorization_HR@10_pct'] != null
            ? `+${improvements['NeuMF_vs_MatrixFactorization_HR@10_pct']}% vs MF` : undefined} />
        <StatTile label="NeuMF NDCG@10" value={num(models.NeuMF?.['NDCG@10'])} accent
          hint={improvements['NeuMF_vs_MatrixFactorization_NDCG@10_pct'] != null
            ? `+${improvements['NeuMF_vs_MatrixFactorization_NDCG@10_pct']}% vs MF` : undefined} />
        <StatTile label="Rating RMSE" value={num(rating.RMSE, 4)}
          hint={rating.baselines?.item_mean ? `item-mean baseline ${num(rating.baselines.item_mean.RMSE)}` : undefined} />
        <StatTile label="Measured latency"
          value={recRoute ? `${recRoute[1].p50_ms} ms` : 'No requests yet'}
          hint={recRoute ? `p95 ${recRoute[1].p95_ms} ms over ${recRoute[1].count} requests · 200 ms target` : 'p50 of /recommendations'} />
      </div>

      <ChartCard title="HR@10 and NDCG@10 by model"
        description="Hit Rate is whether the held-out movie lands in the top 10; NDCG additionally rewards placing it near the top. Same candidate sets for all three models."
        table={<DataTable columns={['Model', 'HR@10', 'NDCG@10', 'MRR', 'ROC-AUC']}
          rows={comparison.map((c) => [c.name, num(c['HR@10']), num(c['NDCG@10']), num(c.MRR), num(c['ROC-AUC'])])} />}
        footnote="Higher is better on every metric shown.">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={comparison} margin={{ top: 8, right: 12, bottom: 4, left: 8 }} barGap={2}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="name" {...axisProps} />
            <YAxis domain={[0, 1]} {...axisProps} />
            <Tooltip {...tooltipStyle} formatter={(v, n) => [num(v), n]} />
            <Legend wrapperStyle={{ fontSize: 12, color: AXIS }} />
            <Bar fill={AXIS} dataKey="HR@10" radius={[4, 4, 0, 0]} maxBarSize={44}>
              {comparison.map((c) => <Cell key={c.key} fill={SERIES[c.key]} />)}
            </Bar>
            <Bar fill={AXIS} dataKey="NDCG@10" radius={[4, 4, 0, 0]} maxBarSize={44} fillOpacity={0.55}>
              {comparison.map((c) => <Cell key={c.key} fill={SERIES[c.key]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="ROC-AUC (implicit classification view)"
          description="Ability to score the held-out positive above the 99 sampled unobserved movies."
          table={<DataTable columns={['Model', 'ROC-AUC']} rows={comparison.map((c) => [c.name, num(c['ROC-AUC'])])} />}>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={comparison} layout="vertical" margin={{ left: 70, right: 24, top: 4, bottom: 4 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" domain={[0.9, 1]} {...axisProps} />
              <YAxis type="category" dataKey="name" width={120} {...axisProps} />
              <Tooltip {...tooltipStyle} formatter={(v) => [num(v), 'ROC-AUC']} />
              <Bar dataKey="ROC-AUC" radius={[0, 4, 4, 0]} maxBarSize={26}>
                {comparison.map((c) => <Cell key={c.key} fill={SERIES[c.key]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Rating prediction error (RMSE)"
          description="The separate calibrated rating model against two non-learned baselines on the same held-out ratings."
          table={<DataTable columns={['Predictor', 'RMSE', 'MAE']}
            rows={[['Rating predictor', num(rating.RMSE), num(rating.MAE)],
                   ['Item mean', num(rating.baselines?.item_mean?.RMSE), num(rating.baselines?.item_mean?.MAE)],
                   ['Global mean', num(rating.baselines?.global_mean?.RMSE), num(rating.baselines?.global_mean?.MAE)]]} />}
          footnote="Lower is better. Predictions are squashed into the 0.5–5.0 MovieLens scale by construction.">
          {rmseRows.length === 0 ? <NotEvaluated /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={rmseRows} layout="vertical" margin={{ left: 70, right: 24, top: 4, bottom: 4 }}>
                <CartesianGrid stroke={GRID} horizontal={false} />
                <XAxis type="number" domain={[0.8, 1.15]} {...axisProps} />
                <YAxis type="category" dataKey="name" width={130} {...axisProps} />
                <Tooltip {...tooltipStyle} formatter={(v) => [num(v), 'RMSE']} />
                <Bar dataKey="RMSE" radius={[0, 4, 4, 0]} maxBarSize={26}>
                  {rmseRows.map((r) => <Cell key={r.name} fill={SERIES[r.key]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      <ChartCard title="Full metric table"
        description="Precision@10 and Recall@10 are included because the PRD asks for them; with exactly one relevant item per user they are fixed functions of HR@10.">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-plum-500">
              <tr>
                {['Model', 'HR@10', 'NDCG@10', 'Precision@10', 'Recall@10', 'F1@10', 'MRR', 'ROC-AUC', 'RMSE'].map((h) => (
                  <th key={h} className="pb-2 pr-4">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-blush-200/60 text-plum-600">
              {Object.entries(models).map(([key, m]) => (
                <tr key={key} className={key === 'NeuMF' ? 'font-semibold text-plum-900' : ''}>
                  <td className="py-2.5 pr-4 flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SERIES[key] || '#7a5c67' }} aria-hidden />
                    {LABELS[key] || key}
                  </td>
                  {['HR@10', 'NDCG@10', 'Precision@10', 'Recall@10', 'F1@10', 'MRR', 'ROC_AUC'].map((f) => (
                    <td key={f} className="py-2.5 pr-4"><Val v={m[f]} /></td>
                  ))}
                  <td className="py-2.5 pr-4">{typeof m.RMSE === 'number' ? num(m.RMSE) : <NotEvaluated />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  )
}

/* ------------------------------------------------------------------ training */
function TrainingTab({ training }) {
  if (training.loading) return <Spinner label="Loading training history…" />
  if (training.error) return <ErrorState message={training.error} onRetry={training.reload} />

  const histories = training.data?.histories || {}
  const entries = [['neumf', 'NeuMF'], ['mf', 'Matrix Factorization'], ['rating', 'Rating predictor']]

  return (
    <div className="space-y-5">
      {entries.map(([key, label]) => {
        const h = histories[key]
        if (!h || h.status === 'Not evaluated' || !h.history) {
          return (
            <ChartCard key={key} title={`${label} — training curve`}>
              <NotEvaluated label="Not trained" />
            </ChartCard>
          )
        }
        const isRating = key === 'rating'
        const data = h.history.map((e) => ({
          epoch: e.epoch,
          train: isRating ? e.train_rmse : e.train_loss,
          validation: isRating ? e.val_rmse : e.val_loss,
          hr: e['val_HR@10'], seconds: e.seconds,
        }))
        return (
          <ChartCard key={key} title={`${label} — training curve`}
            description={isRating
              ? 'Train and validation RMSE per epoch. Early stopping keeps the best validation epoch.'
              : 'Binary cross-entropy per epoch on the training set and on the validation candidate sets.'}
            table={<DataTable columns={['Epoch', isRating ? 'Train RMSE' : 'Train loss', isRating ? 'Val RMSE' : 'Val loss', 'Val HR@10', 'Seconds']}
              rows={h.history.map((e) => [e.epoch,
                isRating ? e.train_rmse : e.train_loss,
                isRating ? e.val_rmse : e.val_loss,
                e['val_HR@10'] ?? '—', e.seconds])} />}
            footnote={`Best epoch ${h.best_epoch} of ${h.epochs_run} run${h.epochs_run === 1 ? '' : 's'} · ${h.early_stopped ? 'stopped early by the patience rule' : 'ran to the configured epoch limit'} · ${h.total_seconds}s total.`}>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="epoch" {...axisProps} label={{ value: 'epoch', fill: AXIS, fontSize: 11, position: 'insideBottom', offset: -2 }} />
                <YAxis {...axisProps} />
                <Tooltip {...tooltipStyle} formatter={(v, n) => [num(v, 5), n]} />
                <Legend wrapperStyle={{ fontSize: 12, color: AXIS }} />
                <Line type="monotone" dataKey="train" name="Train" stroke={CURVE.train} strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="validation" name="Validation" stroke={CURVE.validation} strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        )
      })}

      {histories.neumf?.history && (
        <ChartCard title="NeuMF validation HR@10 by epoch"
          description="The quantity early stopping actually monitors."
          table={<DataTable columns={['Epoch', 'Val HR@10', 'Val NDCG@10']}
            rows={histories.neumf.history.map((e) => [e.epoch, e['val_HR@10'], e['val_NDCG@10']])} />}>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={histories.neumf.history.map((e) => ({ epoch: e.epoch, 'HR@10': e['val_HR@10'], 'NDCG@10': e['val_NDCG@10'] }))}
                       margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="epoch" {...axisProps} />
              <YAxis {...axisProps} domain={['auto', 'auto']} />
              <Tooltip {...tooltipStyle} formatter={(v, n) => [num(v, 5), n]} />
              <Legend wrapperStyle={{ fontSize: 12, color: AXIS }} />
              <Line type="monotone" dataKey="HR@10" stroke={SERIES.NeuMF} strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="NDCG@10" stroke={SERIES.MatrixFactorization} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  )
}

/* ---------------------------------------------------- recommendation analytics */
function RecommendationTab({ metrics }) {
  if (metrics.loading) return <Spinner />
  const analytics = metrics.data?.recommendation_analytics || {}
  if (!Object.keys(analytics).length) {
    return <ChartCard title="Recommendation analytics"><NotEvaluated /></ChartCard>
  }
  const neumf = analytics.NeuMF
  const pop = analytics.Popularity

  const coverage = [
    { name: 'NeuMF', key: 'NeuMF', coverage: neumf?.catalog_coverage_pct, unique: neumf?.unique_movies_recommended, head: neumf?.head_share_pct },
    { name: 'Popularity', key: 'Popularity', coverage: pop?.catalog_coverage_pct, unique: pop?.unique_movies_recommended, head: pop?.head_share_pct },
  ].filter((r) => r.coverage != null)

  const genres = (neumf?.genre_distribution || []).slice(0, 14)
  const scores = neumf?.score_distribution || []

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Users sampled" value={int(neumf?.users_sampled)} hint={`top-${neumf?.top_k} lists analysed`} />
        <StatTile label="Catalog coverage" value={`${neumf?.catalog_coverage_pct}%`} accent
          hint={`${int(neumf?.unique_movies_recommended)} distinct movies recommended`} />
        <StatTile label="Head share" value={`${neumf?.head_share_pct}%`} hint="from the most-rated 20% of the catalog" />
        <StatTile label="Long-tail share" value={`${neumf?.long_tail_share_pct}%`} hint="from the remaining 80%" />
      </div>

      <ChartCard title="Catalog coverage: NeuMF vs popularity"
        description="How much of the catalog each model actually surfaces across the sampled users. Popularity collapses onto a tiny head; NeuMF spreads wider."
        table={<DataTable columns={['Model', 'Coverage %', 'Distinct movies', 'Head share %']}
          rows={coverage.map((c) => [c.name, c.coverage, c.unique?.toLocaleString(), c.head])} />}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={coverage} layout="vertical" margin={{ left: 70, right: 24, top: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRID} horizontal={false} />
            <XAxis type="number" {...axisProps} unit="%" />
            <YAxis type="category" dataKey="name" width={100} {...axisProps} />
            <Tooltip {...tooltipStyle} formatter={(v) => [`${v}%`, 'coverage']} />
            <Bar dataKey="coverage" radius={[0, 4, 4, 0]} maxBarSize={30}>
              {coverage.map((c) => <Cell key={c.key} fill={SERIES[c.key]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Genre mix of NeuMF recommendations"
          description="Genres of the movies NeuMF actually recommended — the model never sees these labels; this is a diagnostic of its output."
          table={<DataTable columns={['Genre', 'Appearances']} rows={genres.map((g) => [g.genre, g.count.toLocaleString()])} />}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={genres} layout="vertical" margin={{ left: 60, right: 16, top: 4, bottom: 4 }}>
              <CartesianGrid stroke={GRID} horizontal={false} />
              <XAxis type="number" {...axisProps} />
              <YAxis type="category" dataKey="genre" width={90} {...axisProps} />
              <Tooltip {...tooltipStyle} formatter={(v) => [v.toLocaleString(), 'appearances']} />
              <Bar dataKey="count" fill={SERIES.NeuMF} radius={[0, 4, 4, 0]} maxBarSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Recommendation score distribution"
          description="Raw NeuMF logits for the movies that made each user's top-10."
          table={<DataTable columns={['Score from', 'Score to', 'Count']}
            rows={scores.map((s) => [s.bin_start, s.bin_end, s.count.toLocaleString()])} />}>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={scores.map((s) => ({ bin: s.bin_start.toFixed(1), count: s.count }))}
                      margin={{ top: 8, right: 8, bottom: 4, left: 8 }}>
              <CartesianGrid stroke={GRID} vertical={false} />
              <XAxis dataKey="bin" {...axisProps} minTickGap={16} />
              <YAxis {...axisProps} />
              <Tooltip {...tooltipStyle} labelFormatter={(l) => `score ≈ ${l}`} formatter={(v) => [v.toLocaleString(), 'items']} />
              <Bar dataKey="count" fill={SERIES.Popularity} radius={[4, 4, 0, 0]} maxBarSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}

/* --------------------------------------------------------------- model info */
function ModelTab({ info }) {
  if (info.loading) return <Spinner label="Loading model information…" />
  if (info.error) return <ErrorState message={info.error} onRetry={info.reload} />
  const d = info.data
  if (!d) return null

  const section = (title, obj) => (
    <ChartCard key={title} title={title}>
      {!obj || obj.status === 'not trained' ? <NotEvaluated label="Not trained" /> : (
        <DataTable columns={['Property', 'Value']}
          rows={Object.entries({ ...obj.config, best_epoch: obj.best_epoch, saved_at: obj.saved_at,
                                 ...Object.fromEntries(Object.entries(obj.training || {}).map(([k, v]) => [`training.${k}`, v])) })
            .map(([k, v]) => [k, Array.isArray(v) ? v.join(' → ') : String(v)])} />
      )}
    </ChartCard>
  )

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Users in model" value={int(d.num_users)} />
        <StatTile label="Movies in model" value={int(d.num_movies)} />
        <StatTile label="Dataset" value={d.dataset} hint={`PRD specifies ${d.prd_dataset}`} accent />
        <StatTile label="Inference device" value={d.device} hint={`loaded ${d.loaded_at}`} />
      </div>
      {d.dataset_deviation_note && (
        <p className="rounded-lg border border-gold-600/25 bg-gold-600/10 px-3 py-2 text-xs text-gold-600">
          {d.dataset_deviation_note}
        </p>
      )}
      {section('NeuMF', d.neumf)}
      {section('Matrix Factorization', d.matrix_factorization)}
      {section('Rating predictor', d.rating_predictor)}
      <ChartCard title="Preprocessing configuration"
        description="The thresholds every artifact was produced under.">
        <DataTable columns={['Setting', 'Value']}
          rows={Object.entries(d.preprocessing || {}).map(([k, v]) => [k, Array.isArray(v) ? v.join(' – ') : String(v)])} />
      </ChartCard>
    </div>
  )
}

/* ------------------------------------------------------------------ hybrid */
function HybridTab({ metrics }) {
  if (metrics.loading) return <Spinner />
  const h = metrics.data?.hybrid
  if (!h || h.status === 'Not evaluated') {
    return (
      <ChartCard title="Hybrid re-ranking (stretch goal)"
        description="Run ml/evaluation/evaluate_hybrid.py to populate this section.">
        <NotEvaluated />
      </ChartCard>
    )
  }
  const grid = (h.grid || []).map((g) => ({
    name: `α=${g.alpha} β=${g.beta} γ=${g.gamma}`,
    'HR@10': g['HR@10'], 'NDCG@10': g['NDCG@10'],
    isPure: g.alpha === 1,
  }))

  return (
    <div className="space-y-5">
      <div className="glass rounded-xl p-4 text-xs leading-relaxed text-plum-500">
        <span className="font-semibold text-plum-700">Experimental.</span> {h.note}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Pure NeuMF NDCG@10" value={num(h.pure_neumf?.['NDCG@10'])} />
        <StatTile label="Best hybrid NDCG@10" value={num(h.best?.['NDCG@10'])} accent
          hint={`α=${h.best?.alpha} β=${h.best?.beta} γ=${h.best?.gamma}`} />
        <StatTile label="NDCG@10 lift" value={`${h.lift_vs_pure_neumf?.['NDCG@10_pct']}%`}
          hint="relative to pure NeuMF on the same candidate sets" />
        <StatTile label="HR@10 lift" value={`${h.lift_vs_pure_neumf?.['HR@10_pct']}%`}
          hint={`${int(h.evaluated_users)} held-out users`} />
      </div>

      <ChartCard title="Weight grid: every blend that was actually evaluated"
        description="Hybrid score = α·normalised NeuMF + β·genre similarity + γ·popularity, normalised within each candidate list. α=1 is pure NeuMF, shown for reference."
        table={<DataTable columns={['Weights', 'HR@10', 'NDCG@10']}
          rows={grid.map((g) => [g.name, num(g['HR@10']), num(g['NDCG@10'])])} />}
        footnote="Genre profiles are built from training-split positives only, so no held-out interaction informs the blend.">
        <ResponsiveContainer width="100%" height={Math.max(260, grid.length * 54)}>
          <BarChart data={grid} layout="vertical" margin={{ left: 60, right: 24, top: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRID} horizontal={false} />
            <XAxis type="number" domain={[0.6, 0.95]} {...axisProps} />
            <YAxis type="category" dataKey="name" width={150} {...axisProps} />
            <Tooltip {...tooltipStyle} formatter={(v, n) => [num(v), n]} />
            <Legend wrapperStyle={{ fontSize: 12, color: AXIS }} />
            <Bar fill={AXIS} dataKey="HR@10" radius={[0, 4, 4, 0]} maxBarSize={16}>
              {grid.map((g, i) => <Cell key={i} fill={g.isPure ? SERIES.MatrixFactorization : SERIES.NeuMF} />)}
            </Bar>
            <Bar fill={AXIS} dataKey="NDCG@10" radius={[0, 4, 4, 0]} maxBarSize={16} fillOpacity={0.55}>
              {grid.map((g, i) => <Cell key={i} fill={g.isPure ? SERIES.MatrixFactorization : SERIES.NeuMF} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

/* -------------------------------------------------------------- experiments */
function ExperimentTab({ experiments }) {
  if (experiments.loading) return <Spinner />
  const list = experiments.data?.experiments || []
  if (!list.length) {
    return (
      <ChartCard title="Experiment comparison"
        description="Only training runs that were actually executed and evaluated appear here.">
        <NotEvaluated label="No experiments recorded yet" />
      </ChartCard>
    )
  }
  const chart = list.map((e) => ({
    name: `${e.model} · d=${e.config.gmf_embedding_dim || e.config.embedding_dim} · ${e.training.negatives_per_positive} neg`,
    key: e.model === 'NeuMF' ? 'NeuMF' : 'MatrixFactorization',
    'HR@10': e['test_HR@10'], 'NDCG@10': e['test_NDCG@10'],
  }))

  return (
    <div className="space-y-5">
      <ChartCard title="Executed experiments"
        description="Each row is a training run that produced a checkpoint and was scored on the shared test candidate sets."
        table={<DataTable
          columns={['Experiment', 'Embedding', 'Negatives', 'Positives', 'Best epoch', 'HR@10', 'NDCG@10']}
          rows={list.map((e) => [e.experiment_id, e.config.gmf_embedding_dim || e.config.embedding_dim,
                                 e.training.negatives_per_positive, e.training.positives?.toLocaleString(),
                                 e.best_epoch, num(e['test_HR@10']), num(e['test_NDCG@10'])])} />}>
        <ResponsiveContainer width="100%" height={Math.max(220, chart.length * 64)}>
          <BarChart data={chart} layout="vertical" margin={{ left: 60, right: 24, top: 4, bottom: 4 }}>
            <CartesianGrid stroke={GRID} horizontal={false} />
            <XAxis type="number" domain={[0, 1]} {...axisProps} />
            <YAxis type="category" dataKey="name" width={220} {...axisProps} />
            <Tooltip {...tooltipStyle} formatter={(v, n) => [num(v), n]} />
            <Legend wrapperStyle={{ fontSize: 12, color: AXIS }} />
            <Bar fill={AXIS} dataKey="HR@10" radius={[0, 4, 4, 0]} maxBarSize={18}>
              {chart.map((c, i) => <Cell key={i} fill={SERIES[c.key]} />)}
            </Bar>
            <Bar fill={AXIS} dataKey="NDCG@10" radius={[0, 4, 4, 0]} maxBarSize={18} fillOpacity={0.55}>
              {chart.map((c, i) => <Cell key={i} fill={SERIES[c.key]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {list.map((e) => (
        <ChartCard key={e.experiment_id} title={e.experiment_id}>
          <DataTable columns={['Property', 'Value']}
            rows={[...Object.entries(e.config), ...Object.entries(e.training).map(([k, v]) => [`training.${k}`, v])]
              .map(([k, v]) => [k, Array.isArray(v) ? v.join(' → ') : String(v)])} />
        </ChartCard>
      ))}
    </div>
  )
}
