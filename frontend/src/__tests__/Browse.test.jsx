import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Browse from '../pages/Browse'
import { movie } from './fixtures'

const list = vi.fn()
const genres = vi.fn()

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api')
  return { ...actual, movieApi: { list: (...a) => list(...a), genres: (...a) => genres(...a) } }
})

describe('Browse page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    genres.mockResolvedValue(['Action', 'Sci-Fi'])
    list.mockResolvedValue({ items: [movie], total: 1, page: 1, page_size: 24, pages: 1 })
  })

  it('searches by title after debouncing', async () => {
    render(<MemoryRouter><Browse /></MemoryRouter>)
    await screen.findByRole('heading', { name: 'Matrix, The (1999)' })
    await userEvent.type(screen.getByLabelText(/Search movies by title/), 'matrix')
    await waitFor(() => {
      expect(list).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'matrix' }))
    }, { timeout: 2000 })
  })

  it('filters by genre', async () => {
    render(<MemoryRouter><Browse /></MemoryRouter>)
    await screen.findByRole('heading', { name: 'Matrix, The (1999)' })
    await userEvent.selectOptions(screen.getByLabelText(/Filter by genre/), 'Sci-Fi')
    await waitFor(() => {
      expect(list).toHaveBeenLastCalledWith(expect.objectContaining({ genre: 'Sci-Fi' }))
    })
  })

  it('reports an empty result set', async () => {
    list.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 24, pages: 1 })
    render(<MemoryRouter><Browse /></MemoryRouter>)
    expect(await screen.findByText(/No movies match/)).toBeInTheDocument()
  })
})
