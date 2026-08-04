<script setup lang="ts">
defineProps<{
  options: { id: string; label: string }[]
  modelValue: string
  size?: 'sm' | 'md'
}>()

defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="segmented" :class="size ?? 'md'" role="tablist">
    <button
      v-for="option in options"
      :key="option.id"
      type="button"
      role="tab"
      :aria-selected="modelValue === option.id"
      :class="{ active: modelValue === option.id }"
      @click="$emit('update:modelValue', option.id)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: var(--surface-sunk);
  border: 1px solid var(--hairline);
  border-radius: 999px;
  overflow-x: auto;
  max-width: 100%;
  min-width: 0;
  scrollbar-width: none;
}

.segmented::-webkit-scrollbar {
  display: none;
}

button {
  border: 0;
  background: transparent;
  padding: 0.35rem 0.8rem;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 550;
  color: var(--ink-soft);
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}

.sm button {
  padding: 0.25rem 0.65rem;
  font-size: 0.75rem;
}

button:hover {
  color: var(--ink);
}

button.active {
  background: var(--surface);
  color: var(--water-800);
  box-shadow: var(--shadow-sm);
}
</style>
