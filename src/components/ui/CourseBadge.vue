<script setup lang="ts">
import type { Course } from '../../types/swim'
import { courseDetail, courseLabel } from '../../utils/format'

defineProps<{
  course: Course | string
  /** Show "25m" / "25y" instead of "Meters" / "Yards". */
  compact?: boolean
}>()
</script>

<template>
  <span
    class="badge course"
    :class="course === 'SCM' ? 'meters' : 'yards'"
    :title="courseDetail(course)"
  >
    {{ compact ? (course === 'SCM' ? '25m' : '25y') : courseLabel(course) }}
  </span>
</template>

<style scoped>
.course.yards {
  background: var(--accent-bg);
  color: var(--water-700);
}

.course.meters {
  background: var(--amber-bg);
  color: var(--amber);
}
</style>
