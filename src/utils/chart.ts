/** Series palette, kept mutable because ECharts option types reject readonly arrays. */
const SERIES_COLORS: string[] = ['#0e8798', '#c8901b', '#0b7f63', '#b6472a', '#5b6fd8', '#8a5bbf', '#17a8bb']

/** Chart colors mirror the CSS tokens so charts and UI stay in sync. */
export const CHART = {
  ink: '#0b1f26',
  inkSoft: '#4a6570',
  inkFaint: '#7b939c',
  grid: 'rgba(14, 135, 152, 0.12)',
  axis: 'rgba(14, 135, 152, 0.25)',
  series: SERIES_COLORS,
  individual: '#0e8798',
  relay: '#c8901b',
  gain: '#0b7f63',
} as const

export const axisLabelStyle = {
  color: CHART.inkSoft,
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: 11,
}

export const tooltipStyle = {
  backgroundColor: '#ffffff',
  borderColor: '#dde9ed',
  borderWidth: 1,
  padding: [8, 10] as [number, number],
  textStyle: { color: CHART.ink, fontSize: 12, fontFamily: 'Inter, system-ui, sans-serif' },
  extraCssText: 'box-shadow: 0 8px 24px -12px rgba(4,34,44,0.28); border-radius: 8px;',
}

export const legendStyle = {
  textStyle: { color: CHART.inkSoft, fontSize: 11, fontFamily: 'Inter, system-ui, sans-serif' },
  itemWidth: 10,
  itemHeight: 10,
  icon: 'roundRect' as const,
}

export function valueAxis(name?: string) {
  return {
    type: 'value' as const,
    name,
    nameTextStyle: { color: CHART.inkFaint, fontSize: 11, padding: [0, 0, 0, 4] },
    axisLabel: axisLabelStyle,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: CHART.grid } },
  }
}

export function categoryAxis(data: string[]) {
  return {
    type: 'category' as const,
    data,
    axisLabel: axisLabelStyle,
    axisLine: { lineStyle: { color: CHART.axis } },
    axisTick: { show: false },
  }
}
