<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import { athletesForTeam, improvementSeries, teamPointsByMeet } from '../utils/aggregates'
import { ordinal, shortMeet } from '../utils/format'
import { athleteSlug } from '../utils/slug'
import { CHART, categoryAxis, legendStyle, tooltipStyle, valueAxis } from '../utils/chart'
import BaseChart from '../components/charts/BaseChart.vue'
import SectionHead from '../components/ui/SectionHead.vue'
import StatTile from '../components/ui/StatTile.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import SegmentedControl from '../components/ui/SegmentedControl.vue'

const route = useRoute()
const { findTeam, athletes, teamStandings, meets, loaded } = useSwimData()

const team = computed(() => findTeam(route.params.slug as string))

watchEffect(() => {
  if (team.value) document.title = `${team.value} — NASH Results`
})

const standing = computed(() => teamStandings.value.find((t) => t.team === team.value) ?? null)
const rank = computed(() => {
  const i = teamStandings.value.findIndex((t) => t.team === team.value)
  return i === -1 ? null : i + 1
})

const roster = computed(() => (team.value ? athletesForTeam(athletes.value, team.value) : []))

const sortBy = ref('points')
const sortOptions = [
  { id: 'points', label: 'Points' },
  { id: 'wins', label: 'Wins' },
  { id: 'improved', label: 'Time dropped' },
  { id: 'name', label: 'Name' },
]

const rosterRows = computed(() => {
  const rows = roster.value.map((a) => {
    const drops = improvementSeries(a)
    return {
      athlete: a,
      points: a.results.reduce((s, r) => s + (r.points ?? 0), 0),
      wins: a.summary.age_group_wins,
      podiums: a.summary.age_group_podiums,
      races: a.summary.races + a.relay_count,
      dropped: Number(drops.reduce((s, d) => s + d.delta, 0).toFixed(2)),
      bestOverall: a.summary.best_overall_finish,
    }
  })

  const sorters: Record<string, (a: (typeof rows)[number], b: (typeof rows)[number]) => number> = {
    points: (a, b) => b.points - a.points,
    wins: (a, b) => b.wins - a.wins || b.points - a.points,
    improved: (a, b) => b.dropped - a.dropped,
    name: (a, b) => a.athlete.last_name.localeCompare(b.athlete.last_name),
  }

  return [...rows].sort(sorters[sortBy.value] ?? sorters.points)
})

const teamTotals = computed(() => {
  const rows = rosterRows.value
  return {
    wins: rows.reduce((s, r) => s + r.wins, 0),
    podiums: rows.reduce((s, r) => s + r.podiums, 0),
    dropped: Number(rows.reduce((s, r) => s + Math.max(r.dropped, 0), 0).toFixed(2)),
  }
})

const meetChart = computed(() => {
  if (!team.value) return {}
  // A D1 team never appears at D2 meets, so drop the meets they sat out.
  const rows = teamPointsByMeet(athletes.value, team.value, meets.value).filter((r) => r.total > 0)
  return {
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' }, ...tooltipStyle },
    legend: { top: 0, ...legendStyle },
    grid: { left: 4, right: 14, top: 32, bottom: 0, containLabel: true },
    xAxis: categoryAxis(rows.map((r) => shortMeet(r.meet))),
    yAxis: valueAxis('points'),
    series: [
      {
        name: 'Individual',
        type: 'bar' as const,
        stack: 'pts',
        data: rows.map((r) => r.individual),
        barMaxWidth: 34,
        itemStyle: { color: CHART.individual, borderRadius: [0, 0, 0, 0] },
      },
      {
        name: 'Relay',
        type: 'bar' as const,
        stack: 'pts',
        data: rows.map((r) => r.relay),
        barMaxWidth: 34,
        itemStyle: { color: CHART.relay, borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
})
</script>

<template>
  <div v-if="!team && loaded" class="shell">
    <EmptyState title="Team not found" message="That team is not part of this season's results.">
      <RouterLink to="/" class="btn primary back">Back to the season</RouterLink>
    </EmptyState>
  </div>

  <div v-else-if="team" class="shell stack rise-in">
    <section class="hero card">
      <div>
        <p class="eyebrow">
          <RouterLink to="/" class="crumb">Season</RouterLink> · Team
        </p>
        <h1>{{ team }}</h1>
        <p v-if="rank" class="rank-line">
          <span class="badge" :class="rank <= 3 ? ['gold', 'silver', 'bronze'][rank - 1] : 'neutral'">
            {{ ordinal(rank) }} of {{ teamStandings.length }}
          </span>
          <span class="muted">in the season standings</span>
        </p>
      </div>

      <div v-if="standing" class="tiles">
        <StatTile :value="standing.points.toLocaleString()" label="Total points" tone="accent" />
        <StatTile :value="standing.individual_points.toLocaleString()" label="Individual" />
        <StatTile :value="standing.relay_points.toLocaleString()" label="Relay" />
        <StatTile :value="roster.length" label="Swimmers" />
        <StatTile :value="teamTotals.wins" label="Age-group wins" :tone="teamTotals.wins ? 'gold' : 'default'" />
        <StatTile
          :value="teamTotals.dropped > 0 ? `−${teamTotals.dropped.toFixed(1)}s` : '—'"
          label="Time dropped"
          tone="gain"
        />
      </div>
    </section>

    <section>
      <SectionHead title="Points by meet" sub="How the season total was built, meet by meet." />
      <div class="card card-pad">
        <BaseChart :option="meetChart" height="260px" />
      </div>
    </section>

    <section>
      <SectionHead title="Roster" :sub="`${roster.length} swimmers raced for ${team} this season.`">
        <template #actions>
          <SegmentedControl v-model="sortBy" :options="sortOptions" size="sm" />
        </template>
      </SectionHead>

      <div class="card table-scroll">
        <table class="data">
          <thead>
            <tr>
              <th>Swimmer</th>
              <th class="num">Races</th>
              <th class="num">Wins</th>
              <th class="num">Podiums</th>
              <th class="num">Points</th>
              <th class="num">Dropped</th>
              <th class="num">Best vs field</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rosterRows" :key="row.athlete.key">
              <td>
                <RouterLink :to="`/swimmer/${athleteSlug(row.athlete.key)}`" class="link">
                  {{ row.athlete.first_name }} {{ row.athlete.last_name }}
                </RouterLink>
                <span v-if="row.athlete.ages.length" class="sub-line">
                  Age {{ row.athlete.ages.join('/') }}
                </span>
              </td>
              <td class="num">{{ row.races }}</td>
              <td class="num">
                <span v-if="row.wins" class="badge gold">{{ row.wins }}</span>
                <span v-else class="faint">—</span>
              </td>
              <td class="num">{{ row.podiums || '—' }}</td>
              <td class="num strong">{{ row.points }}</td>
              <td class="num">
                <span v-if="row.dropped > 0" class="badge gain">−{{ row.dropped.toFixed(2) }}s</span>
                <span v-else class="faint">—</span>
              </td>
              <td class="num">{{ row.bestOverall ? ordinal(row.bestOverall) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
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
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  font-weight: 800;
  letter-spacing: -0.035em;
  margin-top: 0.3rem;
}

.crumb:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.rank-line {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.7rem;
  font-size: 0.85rem;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 0.5rem;
}

.link {
  font-weight: 550;
  color: var(--water-800);
}

.link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.sub-line {
  display: block;
  font-size: 0.7rem;
  color: var(--ink-faint);
}

.strong {
  font-weight: 650;
  color: var(--water-900);
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .tiles {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
