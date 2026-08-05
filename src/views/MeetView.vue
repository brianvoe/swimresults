<script setup lang="ts">
import { computed, ref, watch, watchEffect } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import { isRelayResult, meetStats, meetTeamScores } from '../utils/aggregates'
import type { MeetDetail, MeetEvent, MeetEventResult, MeetRelayResult } from '../types/swim'
import { ordinal, shortEvent } from '../utils/format'
import { athleteSlug, teamSlug } from '../utils/slug'
import SectionHead from '../components/ui/SectionHead.vue'
import StatTile from '../components/ui/StatTile.vue'
import PlaceBadge from '../components/ui/PlaceBadge.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import SegmentedControl from '../components/ui/SegmentedControl.vue'
import SuspectTimeMark from '../components/ui/SuspectTimeMark.vue'

const route = useRoute()
const { findMeet, loadMeetDetail, loaded } = useSwimData()

const detail = ref<MeetDetail | null>(null)
const loadingDetail = ref(false)
const detailError = ref<string | null>(null)

const info = computed(() => findMeet(route.params.id as string))

watch(
  () => route.params.id,
  async (id) => {
    if (typeof id !== 'string') return
    detail.value = null
    detailError.value = null
    loadingDetail.value = true
    try {
      detail.value = await loadMeetDetail(id)
    } catch (e) {
      detailError.value = e instanceof Error ? e.message : 'Could not load this meet'
    } finally {
      loadingDetail.value = false
    }
  },
  { immediate: true },
)

watchEffect(() => {
  if (detail.value) document.title = `${detail.value.name} — NASH Results`
})

const stats = computed(() => (detail.value ? meetStats(detail.value) : null))
const scores = computed(() => (detail.value ? meetTeamScores(detail.value) : []))

/* ------------------------------------------------------------- filtering */

const strokeFilter = ref('all')
const genderFilter = ref('all')
const ageFilter = ref('all')
const query = ref('')

watch(() => route.params.id, () => {
  strokeFilter.value = 'all'
  genderFilter.value = 'all'
  ageFilter.value = 'all'
  query.value = ''
})

const strokeOptions = computed(() => {
  const keys = new Set<string>()
  for (const e of detail.value?.events ?? []) keys.add(e.event_key)
  return [
    { id: 'all', label: 'All events' },
    ...[...keys].sort().map((k) => ({ id: k, label: shortEvent(k) })),
  ]
})

const genderOptions = computed(() => {
  const keys = new Set<string>()
  for (const e of detail.value?.events ?? []) keys.add(e.gender)
  return [{ id: 'all', label: 'All' }, ...[...keys].sort().map((g) => ({ id: g, label: g }))]
})

const ageOptions = computed(() => {
  const keys = new Set<string>()
  for (const e of detail.value?.events ?? []) keys.add(e.age_group)
  return [{ id: 'all', label: 'All ages' }, ...[...keys].sort().map((g) => ({ id: g, label: g }))]
})

function matchesQuery(event: MeetEvent, needle: string) {
  if (event.name.toLowerCase().includes(needle)) return true
  return event.results.some((r) => {
    if (isRelayResult(r)) {
      return (
        (r.team ?? '').toLowerCase().includes(needle) ||
        r.swimmers.some((s) => s.name.toLowerCase().includes(needle))
      )
    }
    return r.name.toLowerCase().includes(needle) || (r.team ?? '').toLowerCase().includes(needle)
  })
}

const visibleEvents = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return (detail.value?.events ?? []).filter((e) => {
    if (strokeFilter.value !== 'all' && e.event_key !== strokeFilter.value) return false
    if (genderFilter.value !== 'all' && e.gender !== genderFilter.value) return false
    if (ageFilter.value !== 'all' && e.age_group !== ageFilter.value) return false
    if (needle && !matchesQuery(e, needle)) return false
    return true
  })
})

/* --------------------------------------------------------------- helpers */

const open = ref<Set<string>>(new Set())

function toggle(code: string) {
  const next = new Set(open.value)
  if (next.has(code)) next.delete(code)
  else next.add(code)
  open.value = next
}

function isOpen(code: string) {
  // A single filtered-down event expands automatically.
  return open.value.has(code) || visibleEvents.value.length <= 3
}

function winnerOf(event: MeetEvent): string {
  const first = event.results.find((r) => r.place === 1)
  if (!first) return ''
  if (isRelayResult(first)) return `${first.team} ${first.relay ?? ''}`.trim()
  return first.name.split(',').reverse().join(' ').trim()
}

function winningTime(event: MeetEvent): string {
  return event.results.find((r) => r.place === 1)?.time ?? ''
}

function winnerSuspect(event: MeetEvent): boolean {
  const first = event.results.find((r) => r.place === 1)
  return !!first && !isRelayResult(first) && !!first.suspect_time
}

const individualResults = (event: MeetEvent) =>
  event.results.filter((r): r is MeetEventResult => !isRelayResult(r))

const relayResults = (event: MeetEvent) =>
  event.results.filter((r): r is MeetRelayResult => isRelayResult(r))

const pdfHref = computed(() =>
  info.value ? `${import.meta.env.BASE_URL}${info.value.source_pdf}` : null,
)

/** The venue already has its own line, so drop the "@ Venue" suffix from the title. */
const title = computed(() => info.value?.name.replace(/\s*@\s*.+$/, '') ?? '')

function divisionTone(division: string | undefined) {
  if (division === 'D2') return 'amber'
  if (division === 'Combined') return 'solid'
  return ''
}
</script>

<template>
  <div v-if="!info && loaded" class="shell">
    <EmptyState title="Meet not found" message="That meet is not part of this season's results.">
      <RouterLink to="/" class="btn primary back">Back to the season</RouterLink>
    </EmptyState>
  </div>

  <div v-else-if="info" class="shell stack rise-in">
    <!-- Header -->
    <section class="hero card">
      <div>
        <p class="eyebrow">
          <RouterLink to="/" class="crumb">Season</RouterLink> · {{ info.date_display }}
        </p>
        <h1>{{ title }}</h1>
        <p class="meta">
          <span class="badge" :class="divisionTone(info.division)">
            {{ info.division === 'Combined' ? 'Both divisions' : `Division ${info.division.slice(1)}` }}
          </span>
          <span class="venue">{{ info.venue }}</span>
        </p>
        <div class="hero-actions">
          <a v-if="pdfHref" :href="pdfHref" target="_blank" rel="noopener" class="btn">
            Official PDF
            <svg viewBox="0 0 16 16" class="ext" aria-hidden="true">
              <path
                d="M6 3h7v7M13 3 6.5 9.5M11 10.5V13H3V5h2.5"
                fill="none"
                stroke="currentColor"
                stroke-width="1.4"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </a>
        </div>
      </div>

      <div v-if="stats" class="tiles">
        <StatTile :value="stats.events" label="Events" />
        <StatTile :value="stats.officialSwims" label="Individual swims" />
        <StatTile :value="stats.relays" label="Relays" />
        <StatTile :value="stats.swimmers" label="Swimmers" />
        <StatTile :value="stats.teams" label="Teams" />
      </div>
    </section>

    <div v-if="loadingDetail" class="loading card card-pad">Loading full results…</div>
    <div v-else-if="detailError" class="card card-pad error">{{ detailError }}</div>

    <template v-else-if="detail">
      <!-- Team scores -->
      <section v-if="scores.length">
        <SectionHead title="Team scores" :sub="`Points earned at ${info.short_name} only.`" />
        <div class="card table-scroll">
          <table class="data">
            <thead>
              <tr>
                <th class="num">#</th>
                <th>Team</th>
                <th class="num">Swimmers</th>
                <th class="num">Individual</th>
                <th class="num">Relay</th>
                <th class="num">Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(team, i) in scores" :key="team.team">
                <td class="num faint">{{ i + 1 }}</td>
                <td>
                  <RouterLink :to="`/team/${teamSlug(team.team)}`" class="link">
                    {{ team.team }}
                  </RouterLink>
                </td>
                <td class="num">{{ team.swimmers }}</td>
                <td class="num">{{ team.individual_points }}</td>
                <td class="num">{{ team.relay_points }}</td>
                <td class="num total">{{ team.points }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Events -->
      <section>
        <SectionHead
          title="Results"
          :sub="`${visibleEvents.length} of ${detail.events.length} events shown.`"
        />

        <div class="filters card card-pad">
          <input v-model="query" type="search" class="search" placeholder="Filter by swimmer or team…" />
          <div class="filter-row">
            <SegmentedControl v-model="genderFilter" :options="genderOptions" size="sm" />
            <SegmentedControl v-model="ageFilter" :options="ageOptions" size="sm" />
          </div>
          <SegmentedControl v-model="strokeFilter" :options="strokeOptions" size="sm" />
        </div>

        <div v-if="!visibleEvents.length" class="card">
          <EmptyState title="No events match" message="Try clearing a filter or searching a different name." />
        </div>

        <div v-else class="events">
          <article v-for="event in visibleEvents" :key="event.code" class="card event">
            <button type="button" class="event-head" @click="toggle(event.code)">
              <span class="event-id num">#{{ event.code }}</span>
              <span class="event-title">
                <span class="event-name">{{ event.name }}</span>
                <span v-if="winnerOf(event)" class="event-winner">
                  Won by {{ winnerOf(event) }} · <span class="time">{{ winningTime(event) }}</span>
                  <SuspectTimeMark v-if="winnerSuspect(event)" />
                </span>
              </span>
              <span class="event-count faint num">{{ event.results.length }}</span>
              <svg class="chev" :class="{ up: isOpen(event.code) }" viewBox="0 0 16 16" aria-hidden="true">
                <path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
              </svg>
            </button>

            <div v-if="isOpen(event.code)" class="table-scroll">
              <!-- Individual -->
              <table v-if="!event.is_relay" class="data">
                <thead>
                  <tr>
                    <th class="num">Pl</th>
                    <th>Swimmer</th>
                    <th>Team</th>
                    <th class="num">Age</th>
                    <th class="num">Time</th>
                    <th class="num">Pts</th>
                    <th>Vs field</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, i) in individualResults(event)" :key="r.athlete_key + i">
                    <td class="num">
                      <PlaceBadge :place="r.place" :status="r.status" compact />
                    </td>
                    <td>
                      <RouterLink :to="`/swimmer/${athleteSlug(r.athlete_key)}`" class="link">
                        {{ r.first_name }} {{ r.last_name }}
                      </RouterLink>
                    </td>
                    <td class="faint">{{ r.team }}</td>
                    <td class="num faint">{{ r.age ?? '—' }}</td>
                    <td class="num time">
                      {{ r.time ?? r.status }}
                      <SuspectTimeMark v-if="r.suspect_time" />
                    </td>
                    <td class="num faint">{{ r.points ?? '—' }}</td>
                    <td class="faint">
                      <span v-if="r.overall_place">
                        {{ ordinal(r.overall_place) }} of {{ r.overall_field }}
                      </span>
                      <span v-else>—</span>
                    </td>
                  </tr>
                </tbody>
              </table>

              <!-- Relay -->
              <table v-else class="data">
                <thead>
                  <tr>
                    <th class="num">Pl</th>
                    <th>Squad</th>
                    <th>Swimmers</th>
                    <th class="num">Time</th>
                    <th class="num">Pts</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, i) in relayResults(event)" :key="(r.team ?? '') + i">
                    <td class="num"><PlaceBadge :place="r.place" :status="r.status" compact /></td>
                    <td>
                      <RouterLink v-if="r.team" :to="`/team/${teamSlug(r.team)}`" class="link">
                        {{ r.team }} {{ r.relay }}
                      </RouterLink>
                      <span v-if="r.division" class="badge neutral div">{{ r.division }}</span>
                    </td>
                    <td class="legs">
                      <RouterLink
                        v-for="s in r.swimmers"
                        :key="s.athlete_key + s.leg"
                        :to="`/swimmer/${athleteSlug(s.athlete_key)}`"
                        class="leg"
                      >
                        {{ s.first_name }} {{ s.last_name }}
                      </RouterLink>
                    </td>
                    <td class="num time">{{ r.time ?? r.status }}</td>
                    <td class="num faint">{{ r.points ?? '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.back {
  margin-top: 1rem;
  display: inline-flex;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1.5rem;
  align-items: center;
  padding: 1.4rem 1.5rem;
  background: linear-gradient(135deg, var(--water-050) 0%, var(--surface) 55%);
}

.hero h1 {
  font-size: clamp(1.6rem, 3.4vw, 2.2rem);
  font-weight: 800;
  letter-spacing: -0.032em;
  margin-top: 0.3rem;
}

.crumb:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.meta {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin-top: 0.6rem;
  flex-wrap: wrap;
}

.venue {
  font-size: 0.85rem;
  color: var(--ink-soft);
}

.hero-actions {
  margin-top: 1rem;
}

.ext {
  width: 13px;
  height: 13px;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(5, minmax(84px, 1fr));
  gap: 0.5rem;
}

.loading,
.error {
  text-align: center;
  color: var(--ink-soft);
  font-size: 0.9rem;
}

.error {
  border-color: var(--loss-edge);
  background: var(--loss-bg);
  color: var(--loss);
}

.link {
  font-weight: 550;
  color: var(--water-800);
}

.link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.total {
  font-weight: 700;
  color: var(--water-900);
}

/* Filters */
.filters {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.6rem;
  margin-bottom: 0.85rem;
}

.search {
  width: 100%;
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  padding: 0.45rem 0.7rem;
  font-size: 0.875rem;
  background: var(--surface);
}

.search:focus {
  outline: none;
  border-color: var(--water-400);
  box-shadow: 0 0 0 3px rgba(23, 168, 187, 0.15);
}

.filter-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Events */
.events {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.55rem;
}

.event-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  border: 0;
  background: transparent;
  padding: 0.7rem 0.95rem;
  text-align: left;
  border-radius: var(--radius);
}

.event-head:hover {
  background: var(--water-050);
}

.event-id {
  font-size: 0.7rem;
  font-weight: 650;
  color: var(--ink-faint);
  min-width: 2rem;
}

.event-title {
  flex: 1;
  min-width: 0;
}

.event-name {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--water-900);
}

.event-winner {
  display: block;
  font-size: 0.72rem;
  color: var(--ink-faint);
  margin-top: 0.1rem;
}

.event-count {
  font-size: 0.75rem;
}

.chev {
  width: 15px;
  height: 15px;
  color: var(--ink-faint);
  transition: transform 0.18s ease;
  flex-shrink: 0;
}

.chev.up {
  transform: rotate(180deg);
}

.event .table-scroll {
  border-top: 1px solid var(--hairline);
}

.legs {
  white-space: normal;
  min-width: 15rem;
}

.leg {
  font-size: 0.78rem;
  color: var(--ink-soft);
}

.leg:not(:last-child)::after {
  content: ' · ';
  color: var(--hairline-strong);
}

.leg:hover {
  color: var(--water-700);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.div {
  margin-left: 0.4rem;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .tiles {
    grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  }
}
</style>
