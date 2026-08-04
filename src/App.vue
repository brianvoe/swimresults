<script setup lang="ts">
import { onMounted } from 'vue'
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import { useSwimData } from './composables/useSwimData'

const { load, loading, error, loaded } = useSwimData()

onMounted(load)
</script>

<template>
  <AppHeader />

  <main class="page">
    <div v-if="loading && !loaded" class="shell state">
      <div class="spinner" aria-hidden="true" />
      <p>Loading season results…</p>
    </div>

    <div v-else-if="error" class="shell">
      <div class="card card-pad error">
        <p class="title">Could not load results</p>
        <p class="detail">{{ error }}</p>
      </div>
    </div>

    <RouterView v-else v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </main>

  <AppFooter />
</template>

<style scoped>
.state {
  display: grid;
  justify-items: center;
  gap: 0.85rem;
  padding: 5rem 0;
  color: var(--ink-soft);
  font-size: 0.9rem;
}

.spinner {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2.5px solid var(--water-100);
  border-top-color: var(--water-500);
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  border-color: #f0c6b8;
  background: var(--loss-bg);
}

.error .title {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--loss);
}

.error .detail {
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: var(--ink-soft);
}
</style>
