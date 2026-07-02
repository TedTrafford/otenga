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

function yesterdayIso() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

export default function DashboardTimeFilter({ value, onChange, onApply, loading }) {
  const [customStart, setCustomStart] = useState(value.startDate || yesterdayIso())
  const [customEnd, setCustomEnd] = useState(value.endDate || yesterdayIso())

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

      {loading && (
        <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-500">
          <Loader2 size={13} className="animate-spin text-primary" />
          Loading data…
        </span>
      )}
    </div>
  )
}
