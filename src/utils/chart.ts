/** Series palette, kept mutable because ECharts option types reject readonly arrays. */
const SERIES_COLORS: string[] = ['#2189cf', '#6a5cd0', '#0d7c60', '#b7492b', '#94630d', '#0f4068', '#40a5e3']

/** Chart colors mirror the CSS tokens so charts and UI stay in sync. */
export const CHART = {
  ink: '#0b2338',
  inkSoft: '#44637d',
  inkFaint: '#6e8ca6',
  grid: 'rgba(33, 137, 207, 0.13)',
  axis: 'rgba(33, 137, 207, 0.28)',
  series: SERIES_COLORS,
  individual: '#2189cf',
  relay: '#6a5cd0',
  gain: '#0d7c60',
} as const

export const axisLabelStyle = {
  color: CHART.inkSoft,
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: 11,
}

export const tooltipStyle = {
  backgroundColor: '#ffffff',
  borderColor: '#d7e6f2',
  borderWidth: 1,
  padding: [8, 10] as [number, number],
  textStyle: { color: CHART.ink, fontSize: 12, fontFamily: 'Inter, system-ui, sans-serif' },
  extraCssText: 'box-shadow: 0 8px 24px -12px rgba(10,42,70,0.3); border-radius: 8px;',
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
