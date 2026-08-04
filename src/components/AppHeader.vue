<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import GlobalSearch from './GlobalSearch.vue'

const route = useRoute()
const menuOpen = ref(false)

const links = [
  { to: '/', label: 'Season' },
  { to: '/swimmers', label: 'Swimmers' },
  { to: '/leaderboards', label: 'Leaderboards' },
]

watch(() => route.fullPath, () => {
  menuOpen.value = false
})
</script>

<template>
  <header class="header">
    <div class="shell bar">
      <RouterLink to="/" class="brand">
        <svg class="mark" viewBox="0 0 64 64" aria-hidden="true">
          <rect width="64" height="64" rx="14" fill="#0a2a46" />
          <g fill="none" stroke-linecap="round" stroke-width="5">
            <path d="M8 26c6 0 6-5 12-5s6 5 12 5 6-5 12-5 6 5 12 5" stroke="#79c4ee" />
            <path d="M8 38c6 0 6-5 12-5s6 5 12 5 6-5 12-5 6 5 12 5" stroke="#40a5e3" />
            <path d="M8 50c6 0 6-5 12-5s6 5 12 5 6-5 12-5 6 5 12 5" stroke="#1a72b2" />
          </g>
        </svg>
        <span class="wordmark">NASH<span class="light">Results</span></span>
      </RouterLink>

      <nav class="nav" :class="{ open: menuOpen }" aria-label="Main">
        <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link">
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="search-slot">
        <GlobalSearch placeholder="Search swimmers, teams…" />
      </div>

      <button
        type="button"
        class="menu-toggle"
        :aria-expanded="menuOpen"
        aria-label="Toggle navigation"
        @click="menuOpen = !menuOpen"
      >
        <span :class="{ x: menuOpen }" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid var(--hairline);
}

.bar {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  height: var(--header-h);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-shrink: 0;
}

.mark {
  width: 26px;
  height: 26px;
  border-radius: 7px;
}

.wordmark {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.0625rem;
  letter-spacing: -0.03em;
  color: var(--water-900);
}

.wordmark .light {
  font-weight: 500;
  color: var(--water-500);
  margin-left: 0.22em;
}

.nav {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.nav-link {
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--ink-soft);
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-link:hover {
  background: var(--surface-sunk);
  color: var(--ink);
}

.nav-link.router-link-active {
  color: var(--water-800);
  font-weight: 600;
  background: var(--accent-bg);
}

.search-slot {
  margin-left: auto;
  width: min(320px, 38vw);
}

.menu-toggle {
  display: none;
  width: 34px;
  height: 34px;
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
  position: relative;
  flex-shrink: 0;
}

.menu-toggle span,
.menu-toggle span::before,
.menu-toggle span::after {
  position: absolute;
  left: 50%;
  width: 15px;
  height: 1.75px;
  background: var(--ink);
  border-radius: 2px;
  transform: translateX(-50%);
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.menu-toggle span {
  top: 50%;
  margin-top: -0.875px;
}

.menu-toggle span::before,
.menu-toggle span::after {
  content: '';
  left: 0;
  transform: none;
}

.menu-toggle span::before {
  top: -5px;
}
.menu-toggle span::after {
  top: 5px;
}

.menu-toggle span.x {
  background: transparent;
}
.menu-toggle span.x::before {
  transform: translateY(5px) rotate(45deg);
}
.menu-toggle span.x::after {
  transform: translateY(-5px) rotate(-45deg);
}

@media (max-width: 880px) {
  .bar {
    gap: 0.55rem;
  }

  /* Search shares the single bar row; nav drops out into an overlay panel so
     the sticky header never costs more than one row of screen. */
  .search-slot {
    flex: 1;
    width: auto;
    min-width: 0;
    margin-left: 0;
  }

  .menu-toggle {
    display: block;
  }

  .nav {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 0.1rem;
    padding: 0.4rem 1.25rem 0.6rem;
    background: var(--surface);
    border-bottom: 1px solid var(--hairline);
    box-shadow: var(--shadow-lg);
  }

  .nav.open {
    display: flex;
  }

  .nav-link {
    padding: 0.6rem 0.7rem;
  }
}

@media (max-width: 420px) {
  .wordmark .light {
    display: none;
  }
}
</style>
