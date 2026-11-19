import { useState } from 'react'
import { Table2, LineChart as LineIcon } from 'lucide-react'

/**
 * Wrapper giving every chart a title, an explanation, and a table view —
 * so identity is never conveyed by colour alone.
 */
export default function ChartCard({ title, description, children, table, footnote }) {
  const [showTable, setShowTable] = useState(false)
  return (
    <section className="glass rounded-xl p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-plum-700">{title}</h3>
          {description && <p className="mt-0.5 max-w-2xl text-xs leading-relaxed text-plum-500">{description}</p>}
        </div>
        {table && (
          <button type="button" onClick={() => setShowTable((s) => !s)}
            aria-pressed={showTable}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-blush-300 px-2.5 py-1.5 text-[11px] font-semibold text-plum-500 transition hover:border-rose-500 hover:text-plum-700">
            {showTable ? <LineIcon className="h-3.5 w-3.5" /> : <Table2 className="h-3.5 w-3.5" />}
            {showTable ? 'Chart' : 'Table'}
          </button>
        )}
      </div>
      {showTable && table ? table : children}
      {footnote && <p className="mt-3 text-[11px] text-plum-500">{footnote}</p>}
    </section>
  )
}

export function DataTable({ columns, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[420px] text-left text-sm">
        <thead className="text-[11px] uppercase tracking-wider text-plum-500">
          <tr>{columns.map((c) => <th key={c} className="pb-2 pr-4">{c}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-blush-200/60 text-plum-600">
          {rows.map((r, i) => (
            <tr key={i}>{r.map((cell, j) => <td key={j} className="py-2 pr-4">{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function StatTile({ label, value, hint, accent = false }) {
  return (
    <div className="glass rounded-xl p-4">
      <p className="text-[11px] uppercase tracking-wider text-plum-500">{label}</p>
      <p className={`mt-1.5 text-2xl font-extrabold ${accent ? 'text-rose-700' : 'text-plum-900'}`}>{value}</p>
      {hint && <p className="mt-1 text-[11px] text-plum-500">{hint}</p>}
    </div>
  )
}
