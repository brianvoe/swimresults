<script setup lang="ts">
import { computed } from 'vue'
import { ordinal, podiumClass } from '../../utils/format'

const props = defineProps<{
  place: number | null | undefined
  field?: number | null
  /** Non-finishing status such as NS or DQ. */
  status?: string
  compact?: boolean
}>()

const tone = computed(() => podiumClass(props.place) ?? 'neutral')
const isPodium = computed(() => podiumClass(props.place) != null)
</script>

<template>
  <span v-if="place == null" class="badge neutral">{{ status ?? '—' }}</span>
  <span v-else class="badge place" :class="[tone, { podium: isPodium }]">
    <span class="num">{{ ordinal(place) }}</span>
    <span v-if="field && !compact" class="field num">/ {{ field }}</span>
  </span>
</template>

<style scoped>
.place {
  font-variant-numeric: tabular-nums;
}

.podium {
  font-weight: 650;
}

.field {
  opacity: 0.65;
  font-weight: 500;
}
</style>
