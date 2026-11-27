/**
 * Technical furniture, in the voice of the IRIS_AI reference.
 *
 * The reference frames its content with small monospace marks — (IRIS_AI),
 * [ v.01b ], ( A ), [ 001 /004 ]. They carry most of its character while
 * taking almost no space, and they read as instrumentation rather than
 * decoration, which suits a page backed by a real model.
 *
 * Every value passed in must be real. These render what they are given; they
 * never invent a count or an index.
 */

/** `( A )` — marks a section of the page. */
export function SectionMarker({ letter, className = '' }) {
  return (
    <span className={`section-marker ${className}`} aria-hidden="true">
      ( {letter} )
    </span>
  )
}

/**
 * `[ 001 /004 ]` — position within a set. `index` is zero-based.
 * Hidden from assistive tech: the surrounding control announces position.
 */
export function Counter({ index, total, className = '' }) {
  if (!Number.isFinite(index) || !Number.isFinite(total) || total <= 0) return null
  const pad = (n) => String(n).padStart(3, '0')
  return (
    <span className={`counter ${className}`} aria-hidden="true">
      [ {pad(index + 1)} /{pad(total)} ]
    </span>
  )
}

/** `[ v.01b ]` — a small bracketed label for a version, model or dataset note. */
export function MetaTag({ children, className = '' }) {
  return <span className={`mono-tag ${className}`}>[ {children} ]</span>
}
