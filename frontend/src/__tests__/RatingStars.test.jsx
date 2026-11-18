import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import RatingStars from '../components/RatingStars'

describe('RatingStars', () => {
  it('submits a half-star rating on the MovieLens scale', async () => {
    const onChange = vi.fn()
    render(<RatingStars value={null} onChange={onChange} />)
    await userEvent.click(screen.getByLabelText('Rate 3.5 out of 5'))
    expect(onChange).toHaveBeenCalledWith(3.5)
  })

  it('shows the current value', () => {
    render(<RatingStars value={4.5} onChange={() => {}} />)
    expect(screen.getByText('4.5')).toBeInTheDocument()
  })

  it('exposes no controls when disabled', () => {
    render(<RatingStars value={3} disabled />)
    expect(screen.queryByLabelText(/Rate 3 out of 5/)).not.toBeInTheDocument()
  })
})
