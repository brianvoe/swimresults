<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import { improvementSeries } from '../utils/aggregates'
import { ordinal } from '../utils/format'
import { athleteSlug, teamSlug } from '../utils/slug'
import SectionHead from '../components/ui/SectionHead.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import SegmentedControl from '../components/ui/SegmentedControl.vue'

const { athletes, teamStandings } = useSwimData()

const query = ref('')
const teamFilter = ref('all')
const sortBy = ref('name')

const teamOptions = computed(() => [
  { id: 'all', label: 'All teams' },
  ...teamStandings.value.map((t) => ({ id: t.team, label: t.team })),
])

const sortOptions = [
  { id: 'name', label: 'A–Z' },
  { id: 'wins', label: 'Wins' },
  { id: 'points', label: 'Points' },
  { id: 'races', label: 'Races' },
]

const rows = computed(() => {
  const needle = query.value.trim().toLowerCase()

  const mapped = athletes.value
    .filter((a) => {
      if (teamFilter.value !== 'all' && !a.teams.includes(teamFilter.value)) return false
      if (!needle) return true
      return (
        `${a.first_name} ${a.last_name}`.toLowerCase().includes(needle) ||
        a.search_names.some((n) => n.toLowerCase().includes(needle)) ||
        a.teams.some((t) => t.toLowerCase().includes(needle))
      )
    })
    .map((a) => ({
      athlete: a,
      points: a.results.reduce((s, r) => s + (r.points ?? 0), 0),
      races: a.summary.races + a.relay_count,
      dropped: Number(
        improvementSeries(a)
          .reduce((s, d) => s + d.delta, 0)
          .toFixed(2),
      ),
    }))

  const sorters: Record<string, (a: (typeof mapped)[number], b: (typeof mapped)[number]) => number> = {
    name: (a, b) =>
      a.athlete.last_name.localeCompare(b.athlete.last_name) ||
      a.athlete.first_name.localeCompare(b.athlete.first_name),
    wins: (a, b) => b.athlete.summary.age_group_wins - a.athlete.summary.age_group_wins || b.points - a.points,
    points: (a, b) => b.points - a.points,
    races: (a, b) => b.races - a.races,
  }

  return mapped.sort(sorters[sortBy.value] ?? sorters.name)
})
</script>

<template>
  <div class="shell stack rise-in">
    <SectionHead
      title="All swimmers"
      :sub="`${athletes.length} swimmers raced this season. Search, filter by team, or sort to find someone.`"
    />

    <div class="controls card card-pad">
      <input v-model="query" type="search" class="search" placeholder="Search by name or team…" />
      <div class="control-row">
        <SegmentedControl v-model="sortBy" :options="sortOptions" size="sm" />
        <select v-model="teamFilter" class="team-select" aria-label="Filter by team">
          <option v-for="option in teamOptions" :key="option.id" :value="option.id">
            {{ option.label }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="!rows.length" class="card">
      <EmptyState title="No swimmers match" message="Try a different name or clear the team filter." />
    </div>

    <div v-else class="grid">
      <RouterLink
        v-for="row in rows"
        :key="row.athlete.key"
        :to="`/swimmer/${athleteSlug(row.athlete.key)}`"
        class="card card-pad card-link person"
      >
        <p class="name">{{ row.athlete.first_name }} {{ row.athlete.last_name }}</p>
        <p class="team">{{ row.athlete.teams.join(' · ') || 'Unaffiliated' }}</p>
        <dl class="mini-stats">
          <div>
            <dt>Races</dt>
            <dd>{{ row.races }}</dd>
          </div>
          <div>
            <dt>Wins</dt>
            <dd :class="{ zero: !row.athlete.summary.age_group_wins }">
              {{ row.athlete.summary.age_group_wins }}
            </dd>
          </div>
          <div>
            <dt>Best</dt>
            <dd>
              {{
                row.athlete.summary.best_overall_finish
                  ? ordinal(row.athlete.summary.best_overall_finish)
                  : '—'
              }}
            </dd>
          </div>
        </dl>
        <p class="drop" :class="{ flat: row.dropped <= 0 }">
          {{ row.dropped > 0 ? `−${row.dropped.toFixed(2)}s dropped` : 'No repeat swims to compare' }}
        </p>
      </RouterLink>
    </div>

    <p class="count muted">
      Showing {{ rows.length }} of {{ athletes.length }} swimmers
      <template v-if="teamFilter !== 'all'">
        ·
        <RouterLink :to="`/team/${teamSlug(teamFilter)}`" class="link">
          View {{ teamFilter }} team page
        </RouterLink>
      </template>
    </p>
  </div>
</template>

<style scoped>
.controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.6rem;
}

.search {
  width: 100%;
  border: 1px solid var(--hairline-strong);
  border-radius: var(--radius-sm);
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
}

.search:focus {
  outline: none;
  border-color: var(--water-400);
  box-shadow: 0 0 0 3px rgba(23, 168, 187, 0.15);
}

.control-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.team-select {
  border: 1px solid var(--hairline-strong);
  border-radius: 999px;
  padding: 0.32rem 0.7rem;
  font-size: 0.8125rem;
  background: var(--surface);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(216px, 1fr));
  gap: 0.65rem;
}

.name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.95rem;
  letter-spacing: -0.02em;
  color: var(--water-900);
}

.team {
  font-size: 0.75rem;
  color: var(--ink-faint);
  margin-top: 0.1rem;
}

.person {
  display: flex;
  flex-direction: column;
}

.mini-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.35rem;
  margin-top: auto;
  padding-top: 0.7rem;
}

.mini-stats dt {
  font-size: 0.6rem;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.mini-stats dd {
  margin-inline-start: 0;
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--water-900);
  line-height: 1.1;
}

.mini-stats dd.zero {
  color: var(--ink-faint);
  font-weight: 600;
}

.drop {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--hairline);
  font-size: 0.7rem;
  font-weight: 550;
  color: var(--gain);
}

.drop.flat {
  color: var(--ink-faint);
  font-weight: 450;
}

.count {
  font-size: 0.8125rem;
  text-align: center;
}

.link {
  color: var(--water-700);
  font-weight: 550;
}

.link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
