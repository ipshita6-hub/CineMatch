import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Recommendations from '../pages/Recommendations'
import { fallbackResponse, recommendationResponse } from './fixtures'

const mine = vi.fn()
const genres = vi.fn()
const status = vi.fn()

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api')
  return {
    ...actual,
    recommendationApi: { mine: (...a) => mine(...a) },
    movieApi: { genres: (...a) => genres(...a) },
    userApi: { status: (...a) => status(...a) },
  }
})

const renderPage = () => render(<MemoryRouter><Recommendations /></MemoryRouter>)

describe('Recommendations page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    genres.mockResolvedValue(['Action', 'Sci-Fi'])
    status.mockResolvedValue({ method: 'fold-in user embedding' })
  })

  it('renders personalised recommendations with rank and score', async () => {
    mine.mockResolvedValue(recommendationResponse)
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Matrix, The (1999)' })).toBeInTheDocument()
    expect(screen.getByText('#1')).toBeInTheDocument()
    expect(screen.getByText(/score 4.560/)).toBeInTheDocument()
    expect(screen.getByText(/Served by/)).toHaveTextContent('neumf')
  })

  it('states plainly when a fallback was served instead', async () => {
    mine.mockResolvedValue(fallbackResponse)
    renderPage()
    expect(await screen.findByText(/no trained MovieLens profile/)).toBeInTheDocument()
  })

  it('refetches when the model is switched', async () => {
    mine.mockResolvedValue(recommendationResponse)
    renderPage()
    await screen.findByRole('heading', { name: 'Matrix, The (1999)' })
    await userEvent.click(screen.getByRole('button', { name: 'Matrix Factorization' }))
    await waitFor(() => {
      expect(mine).toHaveBeenLastCalledWith(expect.objectContaining({ model: 'mf' }))
    })
  })

  it('requests a larger list when Top 50 is chosen', async () => {
    mine.mockResolvedValue(recommendationResponse)
    renderPage()
    await screen.findByRole('heading', { name: 'Matrix, The (1999)' })
    await userEvent.click(screen.getByRole('button', { name: 'Top 50' }))
    await waitFor(() => {
      expect(mine).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 50 }))
    })
  })

  it('surfaces an API failure with a retry affordance', async () => {
    mine.mockRejectedValue({ message: 'Network Error' })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/Cannot reach the API/)
    expect(screen.getByRole('button', { name: /Try again/ })).toBeInTheDocument()
  })

  it('shows an empty state rather than a blank page', async () => {
    mine.mockResolvedValue({ ...recommendationResponse, items: [], count: 0 })
    renderPage()
    expect(await screen.findByText(/No recommendations yet/)).toBeInTheDocument()
  })
})
