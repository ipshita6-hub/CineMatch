/**
 * Chart tokens.
 *
 * The three categorical slots below were validated with the dataviz palette
 * validator against this app's chart surface (#10131d) on the all-pairs
 * pairlist: CVD ΔE 9.4, normal-vision ΔE 20.9, contrast ≥ 3:1 — all checks
 * pass. Hues are assigned to entities in fixed order and never cycled; a
 * filter that drops a model must not repaint the survivors.
 */
export const SERIES = {
  Popularity: '#3987e5',          // slot 1 · blue
  MatrixFactorization: '#d95926', // slot 2 · orange
  NeuMF: '#199e70',               // slot 3 · aqua
}

export const SERIES_ORDER = ['Popularity', 'MatrixFactorization', 'NeuMF']

export const LABELS = {
  Popularity: 'Popularity',
  MatrixFactorization: 'Matrix Factorization',
  NeuMF: 'NeuMF',
  RatingPredictor: 'Rating predictor',
}

export const CURVE = { train: '#3987e5', validation: '#d95926' }

// Sequential ramp: one hue, light → dark (used for magnitude, never identity)
export const SEQ = ['#9fd0f5', '#6cb2ee', '#3987e5', '#2a66b4', '#1c4680']

export const AXIS = '#8b93a7'
export const GRID = 'rgba(139,147,167,0.14)'
export const SURFACE = '#10131d'
export const TEXT = '#d3d8e4'

export const axisProps = {
  stroke: AXIS,
  tick: { fill: AXIS, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: GRID },
}

export const tooltipStyle = {
  contentStyle: {
    background: '#161a26',
    border: '1px solid rgba(139,147,167,0.22)',
    borderRadius: 10,
    fontSize: 12,
    color: TEXT,
  },
  labelStyle: { color: '#aab2c5', fontWeight: 600, marginBottom: 2 },
  cursor: { fill: 'rgba(139,147,167,0.08)' },
}
