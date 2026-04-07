import React, { lazy, Suspense } from 'react'

const Plot = lazy(() =>
  Promise.all([
    import('react-plotly.js/factory'),
    import('plotly.js-dist-min'),
  ]).then(([{ default: createPlotlyComponent }, { default: Plotly }]) => ({
    default: createPlotlyComponent(Plotly),
  }))
)

const darkLayout = {
  paper_bgcolor: 'transparent',
  plot_bgcolor:  'rgba(255,255,255,0.015)',
  font: { color: '#94A3B8', family: 'Inter, sans-serif', size: 11 },
  margin: { t: 40, b: 50, l: 60, r: 20 },
  xaxis: { gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.08)', zerolinecolor: 'rgba(255,255,255,0.08)', tickfont: { size: 10 } },
  yaxis: { gridcolor: 'rgba(255,255,255,0.05)', linecolor: 'rgba(255,255,255,0.08)', zerolinecolor: 'rgba(255,255,255,0.08)', tickfont: { size: 10 } },
  legend: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(255,255,255,0.08)', font: { size: 11 } },
  hoverlabel: { bgcolor: 'rgba(10,10,37,0.95)', bordercolor: 'rgba(0,212,255,0.3)', font: { color: '#E2E8F0', size: 12 } },
  colorway: ['#00D4FF', '#7C3AED', '#06FFA5', '#FF4D6D', '#FFB800', '#EC4899', '#34D399', '#F97316'],
}

export default function ChartRenderer({ figData, height = 320, config: extraConfig = {} }) {
  if (!figData || !figData.data) return (
    <div className="flex items-center justify-center h-full text-slate-600 text-sm">
      No chart data
    </div>
  )

  const layout = {
    ...darkLayout,
    ...(figData.layout || {}),
    paper_bgcolor: 'transparent',
    plot_bgcolor:  darkLayout.plot_bgcolor,
    font:   { ...darkLayout.font,   ...(figData.layout?.font   || {}) },
    margin: { ...darkLayout.margin, ...(figData.layout?.margin || {}) },
    xaxis:  { ...darkLayout.xaxis,  ...(figData.layout?.xaxis  || {}) },
    yaxis:  { ...darkLayout.yaxis,  ...(figData.layout?.yaxis  || {}) },
    colorway: darkLayout.colorway,
    autosize: true,
  }

  const plotConfig = {
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
    responsive: true,
    ...extraConfig,
  }

  return (
    <Suspense fallback={<div className="skeleton w-full rounded-lg" style={{ height }} />}>
      <Plot
        data={figData.data}
        layout={layout}
        config={plotConfig}
        style={{ width: '100%', height }}
        useResizeHandler
      />
    </Suspense>
  )
}
