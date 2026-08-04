<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Nulls are gaps (meets the swimmer skipped). */
    values: (number | null)[]
    width?: number
    height?: number
    /** Swim times improve downward, so a falling line is good. */
    lowerIsBetter?: boolean
  }>(),
  { width: 96, height: 28, lowerIsBetter: true },
)

const points = computed(() => {
  const present = props.values
    .map((v, i) => ({ v, i }))
    .filter((p): p is { v: number; i: number } => p.v != null)

  if (present.length < 2) return null

  const vals = present.map((p) => p.v)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const span = max - min || 1
  const pad = 3
  const w = props.width - pad * 2
  const h = props.height - pad * 2
  const lastIndex = props.values.length - 1 || 1

  return present.map((p) => ({
    x: pad + (p.i / lastIndex) * w,
    y: pad + ((p.v - min) / span) * h,
    value: p.v,
  }))
})

const path = computed(() =>
  points.value ? points.value.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ') : '',
)

const trend = computed(() => {
  if (!points.value) return 'flat'
  const first = points.value[0].value
  const last = points.value[points.value.length - 1].value
  if (first === last) return 'flat'
  const better = props.lowerIsBetter ? last < first : last > first
  return better ? 'good' : 'bad'
})
</script>

<template>
  <svg
    v-if="points"
    class="spark"
    :class="trend"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    aria-hidden="true"
  >
    <path :d="path" fill="none" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
    <circle
      :cx="points[points.length - 1].x"
      :cy="points[points.length - 1].y"
      r="2.5"
      class="tip"
    />
  </svg>
  <span v-else class="empty" aria-hidden="true">—</span>
</template>

<style scoped>
.spark path {
  stroke: var(--ink-faint);
}
.spark .tip {
  fill: var(--ink-faint);
}

.spark.good path,
.spark.good .tip {
  stroke: var(--gain);
  fill: var(--gain);
}
.spark.good path {
  fill: none;
}

.spark.bad path,
.spark.bad .tip {
  stroke: var(--loss);
  fill: var(--loss);
}
.spark.bad path {
  fill: none;
}

.empty {
  color: var(--ink-faint);
  font-size: 0.8rem;
}
</style>
