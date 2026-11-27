/**
 * Chart tokens.
 *
 * The three categorical slots below are unchanged from the dark theme: they
 * were re-validated with the dataviz palette validator against the blush
 * chart surface (#fbf1f3) on the all-pairs pairlist and still pass every
 * check — lightness band, chroma floor, CVD ΔE 9.4 (deutan), normal-vision
 * ΔE 26.5, contrast ≥ 3:1. Hues are assigned to entities in fixed order and
 * never cycled; a filter that drops a model must not repaint the survivors.
 *
 * Model identity stays blue/orange/green rather than following the pink UI
 * theme on purpose: three tints of one hue would fail CVD separation.
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

/**
 * Sequential ramp: one hue, light → dark (magnitude, never identity).
 * Re-stepped for the light theme — the dark theme's two palest steps sat at
 * 1.5:1 and 2.1:1 against the blush card and read as empty bars.
 */
export const SEQ = ['#a8cdf2', '#6fa3df', '#3e82cc', '#2a5d9e', '#1a3d6b']

export const AXIS = '#aab8d1'
export const GRID = 'rgba(170,200,255,0.14)'
export const SURFACE = '#12182a'
export const TEXT = '#e8efff'

export const axisProps = {
  stroke: AXIS,
  tick: { fill: AXIS, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: GRID },
}

export const tooltipStyle = {
  contentStyle: {
    background: '#192137',
    border: '1px solid rgba(107,74,85,0.18)',
    borderRadius: 10,
    // A white tooltip needs a shadow to separate from a near-white card.
    boxShadow: '0 10px 30px -12px rgba(74,47,56,0.28)',
    fontSize: 12,
    color: TEXT,
  },
  labelStyle: { color: '#eeeeee', fontWeight: 600, marginBottom: 2 },
  cursor: { fill: 'rgba(107,74,85,0.07)' },
}
