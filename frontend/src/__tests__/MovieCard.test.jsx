import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import MovieCard from '../components/MovieCard'
import { movie } from './fixtures'

const renderCard = (props) =>
  render(<MemoryRouter><MovieCard {...props} /></MemoryRouter>)

describe('MovieCard', () => {
  it('shows title, year and dataset statistics', () => {
    renderCard({ movie })
    // the title also appears inside the placeholder artwork, so scope to the heading
    expect(screen.getByRole('heading', { name: 'Matrix, The (1999)' })).toBeInTheDocument()
    expect(screen.getByText('1999')).toBeInTheDocument()
    expect(screen.getByText('4.18')).toBeInTheDocument()
    expect(screen.getByText('63,366')).toBeInTheDocument()
  })

  it('falls back to a genre placeholder when no poster exists', () => {
    renderCard({ movie })
    expect(screen.getByRole('img', { name: /no poster available/i })).toBeInTheDocument()
  })

  it('uses the real poster when TMDB metadata is present', () => {
    renderCard({ movie: { ...movie, poster_url: 'https://image.tmdb.org/t/p/w500/x.jpg', poster_source: 'tmdb' } })
    expect(screen.getByAltText(/Poster for Matrix/)).toBeInTheDocument()
  })

  it('renders the recommendation score only when asked', () => {
    const { rerender } = renderCard({ movie: { ...movie, score: 4.561 } })
    expect(screen.queryByText(/score 4.561/)).not.toBeInTheDocument()
    rerender(<MemoryRouter><MovieCard movie={{ ...movie, score: 4.561 }} showScore /></MemoryRouter>)
    expect(screen.getByText(/score 4.561/)).toBeInTheDocument()
  })

  it('links to the movie detail route', () => {
    renderCard({ movie })
    expect(screen.getByRole('link')).toHaveAttribute('href', '/app/movies/2571')
  })
})
