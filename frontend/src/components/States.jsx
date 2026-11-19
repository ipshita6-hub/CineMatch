import { AlertTriangle, Inbox, Loader2, RefreshCw } from 'lucide-react'

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-plum-500">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div role="alert" className="glass flex flex-col items-center gap-3 rounded-xl p-8 text-center">
      <AlertTriangle className="h-7 w-7 text-rose-600" aria-hidden />
      <p className="max-w-md text-sm text-plum-600">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-2 rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-600"
        >
          <RefreshCw className="h-4 w-4" /> Try again
        </button>
      )}
    </div>
  )
}

export function EmptyState({ title = 'Nothing here yet', hint, action }) {
  return (
    <div className="glass flex flex-col items-center gap-2 rounded-xl p-10 text-center">
      <Inbox className="h-7 w-7 text-plum-500" aria-hidden />
      <p className="font-semibold text-plum-700">{title}</p>
      {hint && <p className="max-w-md text-sm text-plum-500">{hint}</p>}
      {action}
    </div>
  )
}

export function SkeletonRow({ count = 6, height = 'h-64' }) {
  return (
    <div className="flex gap-4 overflow-hidden">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`skeleton w-44 shrink-0 rounded-xl ${height}`} />
      ))}
    </div>
  )
}

export function NotEvaluated({ label = 'Not evaluated' }) {
  return (
    <span className="rounded-md bg-blush-200 px-2 py-0.5 text-xs font-medium text-plum-500">
      {label}
    </span>
  )
}
