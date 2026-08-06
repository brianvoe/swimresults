<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import { athleteSlug, teamSlug } from '../utils/slug'

const props = withDefaults(
  defineProps<{
    placeholder?: string
    /** The hero search is large and always expanded; the header one is compact. */
    size?: 'sm' | 'lg'
    autofocus?: boolean
  }>(),
  { placeholder: 'Search swimmers, teams, meets…', size: 'sm', autofocus: false },
)

type Hit = {
  id: string
  kind: 'swimmer' | 'team' | 'meet'
  label: string
  detail: string
  to: string
}

const router = useRouter()
const { athletes, teamStandings, meets, loaded } = useSwimData()

const query = ref('')
const open = ref(false)
const active = ref(0)
const root = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)

const haystack = computed<Hit[]>(() => {
  const swimmers: Hit[] = athletes.value.map((a) => ({
    id: `s:${a.key}`,
    kind: 'swimmer',
    label: `${a.first_name} ${a.last_name}`,
    detail: [a.teams[0], a.ages.length ? `Age ${a.ages.join('/')}` : null]
      .filter(Boolean)
      .join(' · '),
    to: `/swimmer/${athleteSlug(a.key)}`,
  }))

  const teams: Hit[] = teamStandings.value.map((t) => ({
    id: `t:${t.team}`,
    kind: 'team',
    label: t.team,
    detail: `${t.swimmers} swimmers · ${t.points} pts`,
    to: `/team/${teamSlug(t.team)}`,
  }))

  const meetHits: Hit[] = meets.value.map((m) => ({
    id: `m:${m.id}`,
    kind: 'meet',
    label: m.short_name,
    detail: `${m.venue} · ${m.date_display} · ${m.course === 'SCM' ? '25m' : '25y'}`,
    to: `/meet/${m.id}`,
  }))

  return [...swimmers, ...teams, ...meetHits]
})

/** Cheap subsequence-tolerant scoring: prefix beats word-start beats contains. */
function score(hit: Hit, needle: string): number {
  const label = hit.label.toLowerCase()
  const detail = hit.detail.toLowerCase()
  if (label === needle) return 0
  if (label.startsWith(needle)) return 1
  if (label.split(/\s+/).some((w) => w.startsWith(needle))) return 2
  if (label.includes(needle)) return 3
  if (detail.includes(needle)) return 5
  return -1
}

const results = computed<Hit[]>(() => {
  const needle = query.value.trim().toLowerCase()
  if (!needle) return []

  const kindWeight = { swimmer: 0, team: 0.3, meet: 0.4 }
  return haystack.value
    .map((hit) => ({ hit, s: score(hit, needle) }))
    .filter((r) => r.s >= 0)
    .sort(
      (a, b) =>
        a.s + kindWeight[a.hit.kind] - (b.s + kindWeight[b.hit.kind]) ||
        a.hit.label.localeCompare(b.hit.label),
    )
    .slice(0, 12)
    .map((r) => r.hit)
})

const grouped = computed(() => {
  const order: Hit['kind'][] = ['swimmer', 'team', 'meet']
  const labels = { swimmer: 'Swimmers', team: 'Teams', meet: 'Meets' }
  return order
    .map((kind) => ({ kind, label: labels[kind], hits: results.value.filter((h) => h.kind === kind) }))
    .filter((g) => g.hits.length)
})

watch(results, () => {
  active.value = 0
})

watch(query, (v) => {
  open.value = v.trim().length > 0
})

function go(hit: Hit) {
  query.value = ''
  open.value = false
  input.value?.blur()
  router.push(hit.to)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    open.value = false
    input.value?.blur()
    return
  }
  if (!results.value.length) return

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    active.value = (active.value + 1) % results.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    active.value = (active.value - 1 + results.value.length) % results.value.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const hit = results.value[active.value]
    if (hit) go(hit)
  }
}

function onDocumentClick(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false
}

function onGlobalKey(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null
  const typing = target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)
  if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing)) {
    e.preventDefault()
    input.value?.focus()
    input.value?.select()
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onGlobalKey)
  if (props.autofocus) nextTick(() => input.value?.focus())
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onGlobalKey)
})

const flatIndex = (kind: Hit['kind'], i: number) =>
  results.value.findIndex((h) => h === grouped.value.find((g) => g.kind === kind)!.hits[i])
</script>

<template>
  <div ref="root" class="search" :class="size">
    <div class="field">
      <svg class="icon" viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" stroke-width="1.8" />
        <path d="M13.5 13.5 17 17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      </svg>
      <input
        ref="input"
        v-model="query"
        type="search"
        role="combobox"
        aria-label="Search swimmers, teams and meets"
        :aria-expanded="open"
        aria-controls="search-results"
        autocomplete="off"
        :placeholder="loaded ? placeholder : 'Loading results…'"
        :disabled="!loaded"
        @keydown="onKeydown"
        @focus="open = query.trim().length > 0"
      />
      <kbd v-if="size === 'sm'" class="hint">/</kbd>
    </div>

    <div v-if="open" id="search-results" class="results" role="listbox">
      <template v-if="grouped.length">
        <div v-for="group in grouped" :key="group.kind" class="group">
          <p class="group-label">{{ group.label }}</p>
          <button
            v-for="(hit, i) in group.hits"
            :key="hit.id"
            type="button"
            role="option"
            :aria-selected="flatIndex(group.kind, i) === active"
            class="hit"
            :class="{ active: flatIndex(group.kind, i) === active }"
            @click="go(hit)"
            @mousemove="active = flatIndex(group.kind, i)"
          >
            <span class="hit-label">{{ hit.label }}</span>
            <span class="hit-detail">{{ hit.detail }}</span>
          </button>
        </div>
      </template>
      <p v-else class="no-hits">No swimmers, teams or meets match “{{ query }}”.</p>
    </div>
  </div>
</template>

<style scoped>
.search {
  position: relative;
  width: 100%;
}

.field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--surface);
  border: 1px solid var(--hairline-strong);
  border-radius: 999px;
  padding: 0 0.75rem;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.field:focus-within {
  border-color: var(--water-400);
  box-shadow: 0 0 0 3px rgba(23, 168, 187, 0.15);
}

.icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: var(--ink-faint);
}

input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  padding: 0.45rem 0;
  font-size: 0.875rem;
}

input::-webkit-search-cancel-button {
  -webkit-appearance: none;
}

.lg .field {
  padding: 0.2rem 1.1rem;
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.lg .icon {
  width: 19px;
  height: 19px;
}

.lg input {
  padding: 0.7rem 0;
  font-size: 1rem;
}

.hint {
  font-family: var(--font-body);
  font-size: 0.7rem;
  color: var(--ink-faint);
  border: 1px solid var(--hairline);
  border-radius: 5px;
  padding: 0.05rem 0.3rem;
  background: var(--surface-sunk);
}

.results {
  position: absolute;
  z-index: 60;
  top: calc(100% + 0.4rem);
  left: 0;
  right: 0;
  max-height: min(60vh, 420px);
  overflow-y: auto;
  background: var(--surface);
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  padding: 0.35rem;
}

.group + .group {
  margin-top: 0.25rem;
  border-top: 1px solid var(--hairline);
  padding-top: 0.35rem;
}

.group-label {
  font-size: 0.65rem;
  font-weight: 650;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--ink-faint);
  padding: 0.3rem 0.55rem 0.25rem;
}

.hit {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  border: 0;
  background: transparent;
  text-align: left;
  padding: 0.42rem 0.55rem;
  border-radius: var(--radius-sm);
}

.hit.active {
  background: var(--water-050);
}

.hit-label {
  font-size: 0.875rem;
  font-weight: 550;
  color: var(--water-900);
}

.hit-detail {
  font-size: 0.75rem;
  color: var(--ink-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.no-hits {
  padding: 0.9rem 0.6rem;
  font-size: 0.85rem;
  color: var(--ink-soft);
  text-align: center;
}
</style>
