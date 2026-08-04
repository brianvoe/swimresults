<script setup lang="ts">
import { useSwimData } from '../composables/useSwimData'

const { seasonLabel, stats } = useSwimData()
</script>

<template>
  <footer class="footer">
    <div class="shell inner">
      <div>
        <p class="title">NASH Results</p>
        <p class="line">
          Nashville adult summer swim league · {{ seasonLabel }}
        </p>
      </div>
      <p class="line source">
        Parsed from {{ stats.meetCount }} official Meet Maestro result PDFs. Overall placings are
        computed across every age group in the same event, so they will not appear on the official
        heat sheets.
      </p>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  border-top: 1px solid var(--hairline);
  background: var(--surface);
  padding: 1.5rem 0 2rem;
}

.inner {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.title {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--water-900);
  font-size: 0.95rem;
}

.line {
  font-size: 0.8125rem;
  color: var(--ink-soft);
  margin-top: 0.2rem;
}

.source {
  max-width: 34rem;
  color: var(--ink-faint);
}
</style>
