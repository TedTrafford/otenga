import React, { useState } from 'react'
import { Calendar, Loader2 } from 'lucide-react'

export const TIME_PRESETS = [
  { id: 'yesterday', label: 'Yesterday' },
  { id: '7d', label: '1 week' },
  { id: '30d', label: '1 month' },
  { id: '180d', label: '6 months' },
  { id: '365d', label: '1 year' },
  { id: 'custom', label: 'Custom' },
]

export const DEFAULT_TIME_FILTER = { preset: 'yesterday', startDate: '', endDate: '' }

const EAT = 'Africa/Nairobi'

function pad2(n) {
  return String(n).padStart(2, '0')
}

/** YYYY-MM-DD for a given instant in EAT. */
function getEatYmd(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: EAT,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const get = (type) => parts.find(p => p.type === type)?.value
  return `${get('year')}-${get('month')}-${get('day')}`
}

function addDaysYmd(ymd, days) {
  const anchor = new Date(`${ymd}T12:00:00+03:00`)
  anchor.setUTCDate(anchor.getUTCDate() + days)
  return getEatYmd(anchor)
}

/** Format YYYY-MM-DD as DD-MM-YYYY. */
function formatDdMmYyyyFromYmd(ymd) {
  const [y, m, d] = ymd.split('-')
  return `${d}-${m}-${y}`
}

/** Format an instant as DD-MM-YYYY HH:MM in EAT. */
function formatEatDateTime(date) {
  const datePart = formatDdMmYyyyFromYmd(getEatYmd(date))
  const timePart = new Intl.DateTimeFormat('en-GB', {
    timeZone: EAT,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
  return `${datePart} ${timePart}`
}

/** Resolve the active [start, end) filter bounds — mirrors backend resolve_date_range (EAT). */
export function resolveActiveRangeLabel(filter) {
  const now = new Date()
  const todayYmd = getEatYmd(now)

  if (filter.preset === 'custom') {
    if (!filter.startDate || !filter.endDate) return null
    return {
      start: formatDdMmYyyyFromYmd(filter.startDate),
      end: formatDdMmYyyyFromYmd(addDaysYmd(filter.endDate, 1)),
    }
  }

  if (filter.preset === 'yesterday') {
    return {
      start: formatDdMmYyyyFromYmd(addDaysYmd(todayYmd, -1)),
      end: formatDdMmYyyyFromYmd(todayYmd),
    }
  }

  const days = { '7d': 7, '30d': 30, '180d': 180, '365d': 365 }[filter.preset]
  if (days) {
    return {
      start: formatDdMmYyyyFromYmd(addDaysYmd(todayYmd, -days)),
      end: formatEatDateTime(now),
    }
  }

  return null
}

function yesterdayYmdEat() {
  return addDaysYmd(getEatYmd(new Date()), -1)
}

export default function DashboardTimeFilter({ value, onChange, onApply, loading }) {
  const [customStart, setCustomStart] = useState(value.startDate || yesterdayYmdEat())
  const [customEnd, setCustomEnd] = useState(value.endDate || yesterdayYmdEat())
  const rangeLabel = resolveActiveRangeLabel(value)

  const selectPreset = (preset) => {
    if (preset === 'custom') {
      onChange({ preset: 'custom', startDate: customStart, endDate: customEnd })
      return
    }
    onChange({ preset, startDate: '', endDate: '' })
    onApply?.({ preset, startDate: '', endDate: '' })
  }

  const applyCustom = () => {
    if (!customStart || !customEnd) return
    const next = { preset: 'custom', startDate: customStart, endDate: customEnd }
    onChange(next)
    onApply?.(next)
  }

  return (
    <div
      className="flex flex-wrap items-center gap-2 px-6 py-2.5 border-b border-white/5 flex-shrink-0"
      style={{ background: 'rgba(5,5,21,0.45)' }}
    >
      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 mr-1">
        <Calendar size={12} />
        <span>Time range</span>
      </div>

      {TIME_PRESETS.filter(p => p.id !== 'custom').map(({ id, label }) => (
        <button
          key={id}
          type="button"
          disabled={loading}
          onClick={() => selectPreset(id)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all disabled:opacity-50"
          style={{
            background: value.preset === id ? 'rgba(0,212,255,0.15)' : 'rgba(255,255,255,0.04)',
            color: value.preset === id ? '#00D4FF' : '#94A3B8',
            border: `1px solid ${value.preset === id ? 'rgba(0,212,255,0.35)' : 'rgba(255,255,255,0.08)'}`,
          }}
        >
          {label}
        </button>
      ))}

      <div
        className="flex items-center gap-2 ml-1 pl-2"
        style={{ borderLeft: '1px solid rgba(255,255,255,0.08)' }}
      >
        <span className="text-[11px] text-slate-500">From</span>
        <input
          type="date"
          value={customStart}
          onChange={e => setCustomStart(e.target.value)}
          className="input-field text-xs py-1 px-2 w-[132px]"
          disabled={loading}
        />
        <span className="text-[11px] text-slate-500">To</span>
        <input
          type="date"
          value={customEnd}
          onChange={e => setCustomEnd(e.target.value)}
          className="input-field text-xs py-1 px-2 w-[132px]"
          disabled={loading}
        />
        <button
          type="button"
          disabled={loading || !customStart || !customEnd}
          onClick={applyCustom}
          className="btn-ghost py-1 px-2.5 text-xs disabled:opacity-50"
        >
          Apply
        </button>
      </div>

      {rangeLabel && (
        <span
          className="ml-auto flex items-center gap-1.5 text-[11px] font-mono text-slate-400"
          title="Date column filter applied to dashboard queries (EAT / Africa-Nairobi)"
        >
          <span className="text-slate-600 hidden sm:inline">Filtering (EAT)</span>
          <span>
            ≥ {rangeLabel.start}
            <span className="text-slate-600 mx-1">·</span>
            &lt; {rangeLabel.end}
          </span>
        </span>
      )}

      {loading && (
        <span className={`flex items-center gap-1.5 text-xs text-slate-500${rangeLabel ? ' ml-2' : ' ml-auto'}`}>
          <Loader2 size={13} className="animate-spin text-primary" />
          Loading data…
        </span>
      )}
    </div>
  )
}
