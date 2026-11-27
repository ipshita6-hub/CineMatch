import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8011'
export const TOKEN_KEY = 'cineneumf.token'

// 90s, not 20s: a free-tier Render instance sleeps after 15 minutes idle and
// takes roughly a minute to wake. At 20s the first request after a sleep
// always failed, so a healthy backend looked like a broken site.
export const api = axios.create({ baseURL, timeout: 90000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY)
    }
    return Promise.reject(error)
  },
)

/** Turns any axios failure into a short sentence a user can act on. */
export function errorMessage(error, fallback = 'Something went wrong.') {
  if (error?.code === 'ECONNABORTED') return 'The request timed out. Is the backend running?'
  if (error?.message === 'Network Error') {
    return `Cannot reach the API at ${baseURL}. Start the backend and try again.`
  }
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) return detail[0].msg || fallback
  return error?.response?.data?.error || fallback
}

export const authApi = {
  register: (body) => api.post('/auth/register', body).then((r) => r.data),
  login: (body) => api.post('/auth/login', body).then((r) => r.data),
  logout: () => api.post('/auth/logout').then((r) => r.data),
  me: () => api.get('/auth/me').then((r) => r.data),
}

export const movieApi = {
  list: (params) => api.get('/movies', { params }).then((r) => r.data),
  detail: (id) => api.get(`/movies/${id}`).then((r) => r.data),
  genres: () => api.get('/movies/genres').then((r) => r.data),
}

export const recommendationApi = {
  mine: (params) => api.get('/recommendations/me', { params }).then((r) => r.data),
  forDatasetUser: (userId, params) =>
    api.get(`/recommendations/${userId}`, { params }).then((r) => r.data),
  predict: (body) => api.post('/predict', body).then((r) => r.data),
}

export const userApi = {
  preferences: () => api.get('/users/me/preferences').then((r) => r.data),
  savePreferences: (body) => api.put('/users/me/preferences', body).then((r) => r.data),
  rate: (body) => api.post('/users/me/ratings', body).then((r) => r.data),
  deleteRating: (movieId) => api.delete(`/users/me/ratings/${movieId}`).then((r) => r.data),
  ratings: () => api.get('/users/me/ratings').then((r) => r.data),
  history: () => api.get('/users/me/history').then((r) => r.data),
  status: () => api.get('/users/me/status').then((r) => r.data),
  onboarding: (body) => api.post('/users/me/onboarding', body).then((r) => r.data),
}

export const metricsApi = {
  models: () => api.get('/metrics').then((r) => r.data),
  eda: () => api.get('/metrics/eda').then((r) => r.data),
  training: () => api.get('/metrics/training').then((r) => r.data),
  experiments: () => api.get('/metrics/experiments').then((r) => r.data),
  latency: () => api.get('/metrics/latency').then((r) => r.data),
  app: () => api.get('/metrics/app').then((r) => r.data),
  modelInfo: () => api.get('/model/info').then((r) => r.data),
  health: () => api.get('/health').then((r) => r.data),
}
