<script setup lang="ts">
defineProps<{
  title: string
  message?: string
}>()
</script>

<template>
  <div class="empty">
    <p class="title">{{ title }}</p>
    <p v-if="message" class="message">{{ message }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  padding: 2rem 1.25rem;
  text-align: center;
  color: var(--ink-soft);
}

.title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--water-800);
}

.message {
  margin-top: 0.3rem;
  font-size: 0.875rem;
  max-width: 28rem;
  margin-inline: auto;
}
</style>
