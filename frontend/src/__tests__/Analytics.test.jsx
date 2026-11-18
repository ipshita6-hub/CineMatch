import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Analytics from '../pages/Analytics'
import { metricsResponse } from './fixtures'

const api = {
  models: vi.fn(), eda: vi.fn(), training: vi.fn(),
  experiments: vi.fn(), latency: vi.fn(), modelInfo: vi.fn(),
}

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api')
  return { ...actual, metricsApi: new Proxy({}, { get: (_, k) => (...a) => api[k](...a) }) }
})

describe('Analytics dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.models.mockResolvedValue(metricsResponse)
    api.eda.mockResolvedValue({ status: 'Not evaluated', detail: 'Run the preprocessing pipeline.' })
    api.training.mockResolvedValue({ status: 'ok', histories: { neumf: { status: 'Not evaluated' } } })
    api.experiments.mockResolvedValue({ status: 'Not evaluated', count: 0, experiments: [] })
    api.latency.mockResolvedValue({ status: 'ok', live: {}, benchmark: {} })
    api.modelInfo.mockResolvedValue({ num_users: 138493, num_movies: 18345, dataset: 'MovieLens 20M', prd_dataset: 'MovieLens 25M', device: 'cpu' })
  })

  it('discloses the dataset deviation from the PRD', async () => {
    render(<MemoryRouter><Analytics /></MemoryRouter>)
    expect(await screen.findByText(/all experiments use MovieLens 20M/)).toBeInTheDocument()
  })

  it('shows measured metrics for all three models on the performance tab', async () => {
    render(<MemoryRouter><Analytics /></MemoryRouter>)
    await userEvent.click(screen.getByRole('button', { name: /Model performance/ }))
    // each value appears in both the stat tile and the metric table
    expect((await screen.findAllByText('0.9087')).length).toBeGreaterThan(0)  // NeuMF HR@10
    expect(screen.getAllByText('0.8651').length).toBeGreaterThan(0)           // MF HR@10
    expect(screen.getAllByText('0.7916').length).toBeGreaterThan(0)           // Popularity HR@10
  })

  it('labels missing metrics "Not evaluated" instead of inventing them', async () => {
    render(<MemoryRouter><Analytics /></MemoryRouter>)
    await userEvent.click(screen.getByRole('button', { name: /Model performance/ }))
    expect((await screen.findAllByText('Not evaluated')).length).toBeGreaterThan(0)
  })

  it('says so when no experiments have been executed', async () => {
    render(<MemoryRouter><Analytics /></MemoryRouter>)
    await userEvent.click(screen.getByRole('button', { name: /Experiments/ }))
    expect(await screen.findByText(/No experiments recorded yet/)).toBeInTheDocument()
  })

  it('does not crash when the EDA artifact is missing', async () => {
    render(<MemoryRouter><Analytics /></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent(/preprocessing pipeline/)
  })
})
