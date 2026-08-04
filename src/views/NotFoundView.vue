<script setup lang="ts">
import { RouterLink } from 'vue-router'
import EmptyState from '../components/ui/EmptyState.vue'
</script>

<template>
  <div class="shell">
    <EmptyState
      title="That page doesn't exist"
      message="The link may be out of date, or the swimmer or team is not part of this season."
    >
      <div class="actions">
        <RouterLink to="/" class="btn primary">Season overview</RouterLink>
        <RouterLink to="/swimmers" class="btn">All swimmers</RouterLink>
      </div>
    </EmptyState>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 1.1rem;
  flex-wrap: wrap;
}
</style>
