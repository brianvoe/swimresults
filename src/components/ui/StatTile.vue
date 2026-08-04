<script setup lang="ts">
defineProps<{
  value: string | number
  label: string
  hint?: string
  tone?: 'default' | 'gold' | 'gain' | 'accent'
}>()
</script>

<template>
  <div class="tile" :class="tone ?? 'default'">
    <p class="value num">{{ value }}</p>
    <p class="label">{{ label }}</p>
    <p v-if="hint" class="hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.tile {
  padding: 0.75rem 0.9rem;
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--hairline);
}

.value {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.03em;
  color: var(--water-900);
}

.gold .value {
  color: var(--gold);
}
.gain .value {
  color: var(--gain);
}
.accent .value {
  color: var(--water-500);
}

.label {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  font-weight: 550;
  color: var(--ink-soft);
}

.hint {
  margin-top: 0.15rem;
  font-size: 0.7rem;
  color: var(--ink-faint);
  line-height: 1.35;
}
</style>
