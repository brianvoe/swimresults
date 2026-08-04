<script setup lang="ts">
const NOTE =
  'Time under review: faster than any swim ever recorded in this event, and out of line with this swimmer’s other results, so the clock most likely caught a split. The placing and points stand as the meet scored them, but the time is excluded from records and personal bests.'
</script>

<template>
  <span class="mark" role="img" :aria-label="NOTE" :title="NOTE">?</span>
</template>

<style scoped>
.mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  margin-left: 0.3rem;
  border-radius: 50%;
  background: var(--loss-bg);
  color: var(--loss);
  font-family: var(--font-body);
  font-size: 0.6rem;
  font-weight: 700;
  line-height: 1;
  vertical-align: 1px;
  cursor: help;
}
</style>
