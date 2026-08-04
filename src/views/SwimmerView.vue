<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import {
  athleteEventSummaries,
  athleteEvents,
  athleteHeadline,
  improvementSeries,
} from '../utils/aggregates'
import { formatSeconds, ordinal, shortEvent, shortMeet, splitRankDisplay } from '../utils/format'
import { teamSlug } from '../utils/slug'
import { CHART, categoryAxis, legendStyle, tooltipStyle, valueAxis } from '../utils/chart'
import BaseChart from '../components/charts/BaseChart.vue'
import SectionHead from '../components/ui/SectionHead.vue'
import StatTile from '../components/ui/StatTile.vue'
import PlaceBadge from '../components/ui/PlaceBadge.vue'
import Sparkline from '../components/ui/Sparkline.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import SegmentedControl from '../components/ui/SegmentedControl.vue'
import SuspectTimeMark from '../components/ui/SuspectTimeMark.vue'

const route = useRoute()
const { findAthlete, meets, loaded } = useSwimData()

const athlete = computed(() => findAthlete(route.params.slug as string))

watchEffect(() => {
  if (athlete.value) {
    document.title = `${athlete.value.first_name} ${athlete.value.last_name} — NASH Results`
  }
})

/** Only meets this swimmer actually raced, so the grid stays readable. */
const meetNames = computed(() => {
  if (!athlete.value) return []
  const raced = new Set<string>([
    ...athlete.value.results.map((r) => r.meet),
    ...athlete.value.relays.map((r) => r.meet),
  ])
  const ordered = meets.value.filter((m) => raced.has(m.short_name)).map((m) => m.short_name)
  return ordered.length ? ordered : [...raced]
})

const events = computed(() => (athlete.value ? athleteEvents(athlete.value) : []))
const eventSummaries = computed(() =>
  athlete.value ? athleteEventSummaries(athlete.value, meetNames.value) : [],
)
const improvement = computed(() => (athlete.value ? improvementSeries(athlete.value) : []))
const headline = computed(() => (athlete.value ? athleteHeadline(athlete.value) : ''))

const totalDrop = computed(() =>
  improvement.value.reduce((sum, r) => sum + r.delta, 0),
)

const resultMap = computed(() => {
  const map = new Map<string, NonNullable<typeof athlete.value>['results'][number]>()
  for (const r of athlete.value?.results ?? []) map.set(`${r.meet}|${r.event_key}`, r)
  return map
})

function cellFor(meet: string, event: string) {
  return resultMap.value.get(`${meet}|${event}`) ?? null
}

const meetIdFor = (name: string) => meets.value.find((m) => m.short_name === name)?.id

/* ---------------------------------------------------------------- charts */

/**
 * A 25 Free and a 100 IM share no useful y-axis, so the default view plots each
 * event as a percentage off that swimmer's own first swim. 'actual' shows raw
 * seconds for anyone who wants the real numbers.
 */
const timeMode = ref('relative')

const timeChart = computed(() => {
  const relative = timeMode.value === 'relative'

  const series = eventSummaries.value.map((summary, idx) => {
    const baseline = summary.first?.time_seconds ?? null
    return {
      name: shortEvent(summary.eventKey),
      type: 'line' as const,
      smooth: 0.25,
      symbolSize: 7,
      connectNulls: true,
      data: summary.series.map((p) => {
        if (p.seconds == null) return null
        if (!relative) return p.seconds
        if (!baseline) return null
        return Number((((p.seconds - baseline) / baseline) * 100).toFixed(2))
      }),
      lineStyle: { width: 2.25 },
      itemStyle: { color: CHART.series[idx % CHART.series.length] },
    }
  })

  return {
    color: CHART.series,
    tooltip: {
      trigger: 'axis' as const,
      ...tooltipStyle,
      valueFormatter: (v: unknown) => {
        if (typeof v !== 'number') return '—'
        return relative ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : formatSeconds(v)
      },
    },
    legend: {
      top: 0,
      type: 'scroll' as const,
      // The zero baseline is drawn by a dummy series; keep it out of the legend.
      data: series.map((s) => s.name),
      ...legendStyle,
    },
    grid: { left: 4, right: 14, top: 34, bottom: 0, containLabel: true },
    xAxis: categoryAxis(meetNames.value.map(shortMeet)),
    yAxis: {
      ...valueAxis(),
      scale: true,
      axisLabel: {
        ...valueAxis().axisLabel,
        formatter: (v: number) => (relative ? `${v > 0 ? '+' : ''}${v}%` : formatSeconds(v)),
      },
    },
    series: relative
      ? [
          ...series,
          {
            name: 'First swim',
            type: 'line' as const,
            data: [],
            markLine: {
              silent: true,
              symbol: 'none',
              label: { show: false },
              lineStyle: { color: CHART.inkFaint, type: 'dashed', width: 1 },
              data: [{ yAxis: 0 }],
            },
          },
        ]
      : series,
  }
})

const placeChart = computed(() => {
  const avg = (rows: (number | null)[]) => {
    const nums = rows.filter((n): n is number => n != null)
    if (!nums.length) return null
    return Number((nums.reduce((a, b) => a + b, 0) / nums.length).toFixed(2))
  }

  const ageGroup = meetNames.value.map((meet) =>
    avg(
      (athlete.value?.results ?? [])
        .filter((r) => r.meet === meet && r.status === 'official' && !r.is_open)
        .map((r) => r.place),
    ),
  )
  const overall = meetNames.value.map((meet) =>
    avg(
      (athlete.value?.results ?? [])
        .filter((r) => r.meet === meet && r.status === 'official')
        .map((r) => r.overall_place),
    ),
  )

  return {
    tooltip: { trigger: 'axis' as const, ...tooltipStyle },
    legend: { top: 0, ...legendStyle },
    grid: { left: 4, right: 14, top: 34, bottom: 0, containLabel: true },
    xAxis: categoryAxis(meetNames.value.map(shortMeet)),
    yAxis: { ...valueAxis(), inverse: true, min: 1 },
    series: [
      {
        name: 'In age group',
        type: 'line' as const,
        smooth: 0.25,
        symbolSize: 8,
        connectNulls: true,
        data: ageGroup,
        itemStyle: { color: CHART.individual },
        lineStyle: { width: 2.25 },
      },
      {
        name: 'Vs whole field',
        type: 'line' as const,
        smooth: 0.25,
        symbolSize: 8,
        connectNulls: true,
        data: overall,
        itemStyle: { color: CHART.relay },
        lineStyle: { width: 2.25 },
      },
    ],
  }
})

/* ----------------------------------------------------------------- share */

const copied = ref(false)

async function share() {
  const url = window.location.href
  const title = athlete.value
    ? `${athlete.value.first_name} ${athlete.value.last_name} — NASH Results`
    : 'NASH Results'

  if (navigator.share) {
    try {
      await navigator.share({ title, url })
      return
    } catch {
      // User dismissed the sheet; fall through to clipboard.
    }
  }

  try {
    await navigator.clipboard.writeText(url)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    copied.value = false
  }
}
</script>

<template>
  <div v-if="!athlete && loaded" class="shell">
    <EmptyState title="Swimmer not found" message="That link may be out of date.">
      <RouterLink to="/swimmers" class="btn primary back">Browse all swimmers</RouterLink>
    </EmptyState>
  </div>

  <div v-else-if="athlete" class="shell stack rise-in">
    <!-- Identity -->
    <section class="hero card">
      <div class="hero-main">
        <p class="eyebrow">Swimmer</p>
        <h1>{{ athlete.first_name }} {{ athlete.last_name }}</h1>
        <p class="teams">
          <RouterLink
            v-for="team in athlete.teams"
            :key="team"
            :to="`/team/${teamSlug(team)}`"
            class="team-chip"
          >
            {{ team }}
          </RouterLink>
          <span v-if="athlete.ages.length" class="age">Age {{ athlete.ages.join(' / ') }}</span>
        </p>
        <p class="headline">{{ headline }}</p>

        <div class="hero-actions">
          <button type="button" class="btn" @click="share">
            {{ copied ? 'Link copied' : 'Share' }}
          </button>
        </div>
      </div>

      <div class="tiles">
        <StatTile
          :value="athlete.summary.age_group_wins"
          label="Age-group wins"
          :tone="athlete.summary.age_group_wins > 0 ? 'first' : 'default'"
        />
        <StatTile
          :value="`${athlete.summary.age_group_podiums}/${athlete.summary.age_group_races}`"
          label="Podium finishes"
        />
        <StatTile
          :value="ordinal(athlete.summary.best_overall_finish)"
          label="Best vs field"
          hint="Against every age group"
          tone="accent"
        />
        <StatTile
          :value="totalDrop > 0 ? `−${totalDrop.toFixed(2)}s` : '—'"
          label="Time dropped"
          :tone="totalDrop > 0 ? 'gain' : 'default'"
        />
        <StatTile :value="athlete.summary.races" label="Individual swims" />
        <StatTile :value="athlete.relay_count" label="Relay legs" />
      </div>
    </section>

    <!-- Per-event breakdown -->
    <section>
      <SectionHead
        title="Event by event"
        sub="Season best, how the time moved across meets, and the best finish achieved in each."
      />
      <div class="event-grid">
        <article v-for="summary in eventSummaries" :key="summary.eventKey" class="card card-pad ev">
          <div class="ev-top">
            <h3>{{ shortEvent(summary.eventKey) }}</h3>
            <Sparkline :values="summary.series.map((p) => p.seconds)" :width="72" :height="24" />
          </div>

          <p class="ev-time num">{{ summary.best?.time ?? '—' }}</p>
          <p class="ev-time-meta">
            <template v-if="summary.best">season best · {{ summary.best.meet }}</template>
            <template v-else>no verified time</template>
          </p>

          <div class="ev-stats">
            <span v-if="summary.delta > 0" class="badge gain">−{{ summary.delta.toFixed(2) }}s</span>
            <span v-else-if="summary.races > 1" class="badge neutral">no drop</span>
            <span v-if="summary.wins" class="badge first">
              {{ summary.wins }} win{{ summary.wins === 1 ? '' : 's' }}
            </span>
            <span v-if="summary.bestOverall" class="badge">
              {{ ordinal(summary.bestOverall) }} vs field
            </span>
            <span class="badge neutral">{{ summary.races }} swum</span>
          </div>
        </article>
      </div>
    </section>

    <!-- Rank grid -->
    <section>
      <SectionHead
        title="Race by race"
        sub="Official age-group placing on top, placing against the whole field underneath."
      />

      <div class="card table-scroll grid-wrap">
        <table class="data rank-table">
          <thead>
            <tr>
              <th class="sticky-col">Event</th>
              <th v-for="meet in meetNames" :key="meet">
                <RouterLink v-if="meetIdFor(meet)" :to="`/meet/${meetIdFor(meet)}`" class="meet-head">
                  {{ shortMeet(meet) }}
                </RouterLink>
                <span v-else>{{ shortMeet(meet) }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in events" :key="event">
              <th class="sticky-col ev-name">{{ shortEvent(event) }}</th>
              <td v-for="meet in meetNames" :key="meet + event">
                <template v-if="cellFor(meet, event)">
                  <template v-if="cellFor(meet, event)!.status === 'official'">
                    <PlaceBadge
                      :place="cellFor(meet, event)!.is_open
                        ? cellFor(meet, event)!.overall_place
                        : cellFor(meet, event)!.place"
                      :field="cellFor(meet, event)!.is_open
                        ? cellFor(meet, event)!.overall_field
                        : cellFor(meet, event)!.age_group_field"
                    />
                    <span class="cell-time time">
                      {{ cellFor(meet, event)!.time }}
                      <SuspectTimeMark v-if="cellFor(meet, event)!.suspect_time" />
                    </span>
                    <span
                      v-if="!cellFor(meet, event)!.is_open && cellFor(meet, event)!.overall_place"
                      class="cell-overall"
                    >
                      {{ ordinal(cellFor(meet, event)!.overall_place) }} of
                      {{ cellFor(meet, event)!.overall_field }} overall
                    </span>
                  </template>
                  <span v-else class="badge neutral">{{ cellFor(meet, event)!.status }}</span>
                </template>
                <span v-else class="faint">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Mobile: one card per meet -->
      <div class="meet-cards">
        <article v-for="meet in meetNames" :key="meet" class="card meet-card">
          <div class="meet-card-head">
            <RouterLink v-if="meetIdFor(meet)" :to="`/meet/${meetIdFor(meet)}`">{{ meet }}</RouterLink>
            <span v-else>{{ meet }}</span>
          </div>
          <ul>
            <li v-for="event in events" :key="meet + event">
              <template v-if="cellFor(meet, event)">
                <span class="mc-event">{{ shortEvent(event) }}</span>
                <span class="mc-right">
                  <template v-if="cellFor(meet, event)!.status === 'official'">
                    <span class="time">
                      {{ cellFor(meet, event)!.time }}
                      <SuspectTimeMark v-if="cellFor(meet, event)!.suspect_time" />
                    </span>
                    <span
                      v-for="(line, i) in splitRankDisplay(cellFor(meet, event)!.rank_display)"
                      :key="i"
                      class="mc-rank"
                      :class="{ soft: i > 0 }"
                    >
                      {{ line }}
                    </span>
                  </template>
                  <span v-else class="badge neutral">{{ cellFor(meet, event)!.status }}</span>
                </span>
              </template>
            </li>
          </ul>
        </article>
      </div>
    </section>

    <!-- Charts -->
    <section class="charts">
      <div>
        <SectionHead
          title="Time progression"
          :sub="timeMode === 'relative'
            ? 'Each event as a percentage off its first swim, so short and long races compare directly. Below the dashed line is faster.'
            : 'Raw times in seconds. A line heading down means getting faster.'"
        >
          <template #actions>
            <SegmentedControl
              v-model="timeMode"
              size="sm"
              :options="[
                { id: 'relative', label: 'Relative' },
                { id: 'actual', label: 'Actual' },
              ]"
            />
          </template>
        </SectionHead>
        <div class="card card-pad">
          <BaseChart :option="timeChart" height="290px" />
        </div>
      </div>
      <div>
        <SectionHead title="Placing trend" sub="Axis is inverted — higher on the chart is a better finish." />
        <div class="card card-pad">
          <BaseChart :option="placeChart" height="290px" />
        </div>
      </div>
    </section>

    <!-- Relays -->
    <section>
      <SectionHead title="Relays" :sub="`${athlete.relay_count} relay legs swum this season.`" />
      <div v-if="athlete.relays.length" class="card table-scroll">
        <table class="data">
          <thead>
            <tr>
              <th>Meet</th>
              <th>Event</th>
              <th>Squad</th>
              <th class="num">Leg</th>
              <th>Place</th>
              <th class="num">Time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(relay, i) in athlete.relays" :key="i">
              <td>{{ relay.meet }}</td>
              <td>{{ shortEvent(relay.event_key) }}</td>
              <td>{{ relay.team }} {{ relay.relay }}</td>
              <td class="num">{{ relay.leg ?? '—' }}</td>
              <td><PlaceBadge :place="relay.place" :status="relay.status" compact /></td>
              <td class="num time">{{ relay.time ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="card">
        <EmptyState title="No relay appearances" message="This swimmer raced individual events only." />
      </div>
    </section>
  </div>
</template>

<style scoped>
.back {
  margin-top: 1rem;
  display: inline-flex;
}

/* Hero */
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
  gap: 1.5rem;
  padding: 1.4rem 1.5rem;
  background: linear-gradient(135deg, var(--water-050) 0%, var(--surface) 55%);
}

.hero h1 {
  font-size: clamp(1.9rem, 4vw, 2.6rem);
  font-weight: 800;
  letter-spacing: -0.035em;
  margin-top: 0.25rem;
}

.teams {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-top: 0.6rem;
}

.team-chip {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--water-700);
  background: var(--accent-bg);
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
}

.team-chip:hover {
  background: var(--water-200);
}

.age {
  font-size: 0.78rem;
  color: var(--ink-faint);
}

.headline {
  margin-top: 0.7rem;
  color: var(--ink-soft);
  font-size: 0.9rem;
  line-height: 1.55;
  max-width: 30rem;
}

.hero-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.55rem;
  align-content: center;
}

/* Event cards */
.event-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 0.7rem;
}

.ev-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.ev h3 {
  font-size: 0.95rem;
}

.ev-time {
  font-family: var(--font-display);
  font-size: 1.65rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--water-900);
  line-height: 1;
  margin-top: 0.5rem;
}

.ev-time-meta {
  font-size: 0.7rem;
  color: var(--ink-faint);
  margin-top: 0.2rem;
}

.ev-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.75rem;
}

/* Rank grid */
.grid-wrap {
  overflow: auto;
  max-height: 70vh;
}

.rank-table td {
  vertical-align: top;
  line-height: 1.35;
}

.rank-table .sticky-col {
  position: sticky;
  left: 0;
  background: var(--surface);
  z-index: 2;
  border-right: 1px solid var(--hairline);
}

.rank-table thead .sticky-col {
  z-index: 3;
  background: var(--surface-sunk);
}

.ev-name {
  font-family: var(--font-body);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--water-800);
  text-align: left;
}

.meet-head {
  color: var(--ink-faint);
}

.meet-head:hover {
  color: var(--water-600);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.cell-time {
  display: block;
  margin-top: 0.28rem;
  font-size: 0.8125rem;
  color: var(--water-800);
}

.cell-overall {
  display: block;
  font-size: 0.7rem;
  color: var(--ink-faint);
  margin-top: 0.05rem;
}

/* Mobile meet cards */
.meet-cards {
  display: none;
  gap: 0.7rem;
}

.meet-card-head {
  padding: 0.6rem 0.85rem;
  border-bottom: 1px solid var(--hairline);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--water-800);
  background: var(--surface-sunk);
  border-radius: var(--radius) var(--radius) 0 0;
}

.meet-card li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.55rem 0.85rem;
  border-bottom: 1px solid var(--hairline);
}

.meet-card li:last-child {
  border-bottom: 0;
}

.mc-event {
  font-size: 0.8125rem;
  font-weight: 550;
}

.mc-right {
  text-align: right;
}

.mc-right .time {
  display: block;
  font-size: 0.875rem;
  color: var(--water-900);
}

.mc-rank {
  display: block;
  font-size: 0.72rem;
  color: var(--ink-soft);
}

.mc-rank.soft {
  color: var(--ink-faint);
}

/* Charts */
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .charts {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .tiles {
    grid-template-columns: repeat(2, 1fr);
  }

  .grid-wrap {
    display: none;
  }

  .meet-cards {
    display: grid;
  }
}
</style>
