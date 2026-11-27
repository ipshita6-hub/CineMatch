import { Link } from 'react-router-dom'

/**
 * The one CineMatch wordmark.
 *
 * It was previously copy-pasted into AppLayout, AuthShell and Landing in three
 * different styles, so the logo changed shape depending on where you were.
 *
 * `to` renders it as a link; omit it for a plain mark.
 */
export default function Brand({ to, onClick, className = '', showMark = true }) {
  const inner = (
    <>
      {showMark && <span className="brand-symbol"><span>C</span></span>}
      <span>Cine<span className="brand-accent">Match</span></span>
    </>
  )
  if (!to) return <span className={`editorial-brand ${className}`}>{inner}</span>
  return (
    <Link to={to} onClick={onClick} className={`editorial-brand ${className}`}>
      {inner}
    </Link>
  )
}
