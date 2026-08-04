<script setup lang="ts">
import { computed, provide } from 'vue'
import VChart, { THEME_KEY } from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import type { EChartsCoreOption } from 'echarts/core'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DatasetComponent,
  MarkLineComponent,
])

const props = defineProps<{
  option: EChartsCoreOption
  height?: string
}>()

provide(THEME_KEY, 'light')

const style = computed(() => ({
  height: props.height ?? '300px',
  width: '100%',
}))
</script>

<template>
  <VChart class="chart" :option="option" :style="style" autoresize />
</template>

<style scoped>
.chart {
  min-height: 200px;
}
</style>
