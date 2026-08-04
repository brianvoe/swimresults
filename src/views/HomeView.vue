<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import { seasonBestSwims } from '../utils/aggregates'
import { shortEvent } from '../utils/format'
import { athleteSlug, teamSlug } from '../utils/slug'
import { CHART, axisLabelStyle, legendStyle, tooltipStyle, valueAxis } from '../utils/chart'
import BaseChart from '../components/charts/BaseChart.vue'
import GlobalSearch from '../components/GlobalSearch.vue'
import SectionHead from '../components/ui/SectionHead.vue'
import SegmentedControl from '../components/ui/SegmentedControl.vue'

const { meets, athletes, stats, teamStandings, leaderCategories, seasonLabel } = useSwimData()

const championship = computed(() => meets.value.find((m) => m.division === 'Combined') ?? null)

/** The title is won at the Championship, not on cumulative season points. */
const podium = computed(() => championship.value?.team_scores.slice(0, 3) ?? [])

const champMargin = computed(() =>
  podium.value.length >= 2 ? podium.value[0].points - podium.value[1].points : 0,
)

/** Championship points per team, for the season table's final column. */
const champPoints = computed(
  () => new Map((championship.value?.team_scores ?? []).map((t) => [t.team, t.points])),
)

/**
 * Worth calling out because the two tables disagree: the team that scored the
 * most all season is not the team holding the trophy.
 */
const seasonLeader = computed(() => teamStandings.value[0]?.team ?? null)
const upsetNote = computed(() => {
  const champ = podium.value[0]?.team
  const leader = seasonLeader.value
  if (!champ || !leader || champ === leader) return null
  return `${leader} scored the most points across the season, but the title goes to ${champ}.`
})

const quickStats = computed(() => [
  { value: stats.value.athleteCount, label: 'Swimmers', tone: '' },
  { value: stats.value.teamCount, label: 'Teams', tone: '' },
  { value: stats.value.meetCount, label: 'Meets', tone: '' },
  { value: stats.value.improvedCount, label: 'Got faster', tone: 'gain' },
])

const activeLeaderboard = ref('wins')
const currentLeaders = computed(
  () =>
    leaderCategories.value.find((c) => c.id === activeLeaderboard.value) ??
    leaderCategories.value[0],
)

/**
 * D1 and D2 raced on the same days, so the season reads as three double-headers
 * plus the combined Championship rather than seven loose cards.
 */
const rounds = computed(() => {
  const byDate = new Map<string, typeof meets.value>()
  for (const meet of meets.value) {
    if (meet.division === 'Combined') continue
    const list = byDate.get(meet.date) ?? []
    list.push(meet)
    byDate.set(meet.date, list)
  }
  return [...byDate.entries()].map(([date, list], i) => ({
    date,
    label: `Round ${i + 1}`,
    dateDisplay: list[0].date_display,
    meets: [...list].sort((a, b) => a.division.localeCompare(b.division)),
  }))
})

const bestSwims = computed(() => seasonBestSwims(athletes.value))

const standingsChart = computed(() => {
  const top = teamStandings.value.slice(0, 10)
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...tooltipStyle },
    legend: { data: ['Individual', 'Relay'], top: 0, ...legendStyle },
    grid: { left: 4, right: 16, top: 34, bottom: 0, containLabel: true },
    xAxis: valueAxis(),
    yAxis: {
      type: 'category' as const,
      data: top.map((t) => t.team).reverse(),
      axisLabel: { ...axisLabelStyle, width: 116, overflow: 'truncate' as const },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: [
      {
        name: 'Individual',
        type: 'bar' as const,
        stack: 'total',
        data: top.map((t) => t.individual_points).reverse(),
        barWidth: 14,
        itemStyle: { color: CHART.individual, borderRadius: [4, 0, 0, 4] },
      },
      {
        name: 'Relay',
        type: 'bar' as const,
        stack: 'total',
        data: top.map((t) => t.relay_points).reverse(),
        barWidth: 14,
        itemStyle: { color: CHART.relay, borderRadius: [0, 4, 4, 0] },
      },
    ],
  }
})

function divisionTone(division: string) {
  if (division === 'D2') return 'amber'
  if (division === 'Combined') return 'solid'
  return ''
}
</script>

<template>
  <div class="shell stack rise-in">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-main">
        <p class="eyebrow">Nashville adult summer league · {{ seasonLabel }}</p>
        <h1>
          Every swim, every&nbsp;place,<br />
          <span class="accent">all season long.</span>
        </h1>
        <p class="lede">
          {{ stats.raceCount.toLocaleString() }} official swims from
          {{ stats.athleteCount }} swimmers across {{ stats.meetCount }} meets — including how
          everyone stacked up against the whole field, not just their age group.
        </p>
      </div>

      <aside class="hero-aside">
        <div class="aside-search">
          <GlobalSearch size="lg" placeholder="Find a swimmer, team or meet…" />
        </div>
        <dl class="quick-stats">
          <div v-for="stat in quickStats" :key="stat.label" class="stat" :class="stat.tone">
            <dd class="num">{{ stat.value.toLocaleString() }}</dd>
            <dt>{{ stat.label }}</dt>
          </div>
        </dl>
      </aside>
    </section>

    <!-- Championship podium -->
    <section v-if="podium.length === 3" class="crown">
      <SectionHead
        title="League champions"
        sub="The Championship meet decides the title — every team, both divisions, one afternoon."
      >
        <template #actions>
          <RouterLink v-if="championship" :to="`/meet/${championship.id}`" class="btn">
            Full results
          </RouterLink>
        </template>
      </SectionHead>

      <ol class="podium">
        <li
          v-for="(team, i) in podium"
          :key="team.team"
          class="spot"
          :class="['first', 'second', 'third'][i]"
        >
          <RouterLink :to="`/team/${teamSlug(team.team)}`" class="plaque">
            <span class="medal">{{ ['Champions', 'Runner-up', 'Third'][i] }}</span>
            <span class="team">{{ team.team }}</span>
            <span class="pts num">{{ team.points.toLocaleString() }}</span>
            <span class="pts-label">championship points</span>

            <span class="split">
              <span class="bar ind" :style="{ flex: team.individual_points }" />
              <span class="bar rel" :style="{ flex: team.relay_points }" />
            </span>
            <span class="split-legend">
              <span><i class="dot ind" />{{ team.individual_points.toLocaleString() }} ind</span>
              <span><i class="dot rel" />{{ team.relay_points.toLocaleString() }} relay</span>
            </span>
          </RouterLink>
          <div class="pedestal">
            <span class="place num">{{ i + 1 }}</span>
          </div>
        </li>
      </ol>

      <p v-if="champMargin > 0" class="margin-note">
        Decided by <strong class="num">{{ champMargin }}</strong> points —
        {{ podium[0].team }} over {{ podium[1].team }}.
      </p>
    </section>

    <!-- Standings -->
    <section>
      <SectionHead
        title="Season points"
        sub="Every point scored across all seven meets. A measure of depth and turnout, not the title."
      />
      <p v-if="upsetNote" class="note">{{ upsetNote }}</p>
      <div class="standings">
        <div class="card card-pad">
          <BaseChart :option="standingsChart" height="330px" />
        </div>
        <div class="card table-scroll">
          <table class="data">
            <thead>
              <tr>
                <th class="num">#</th>
                <th>Team</th>
                <th class="num">Season</th>
                <th class="num">Champs</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(team, i) in teamStandings"
                :key="team.team"
                :class="{ 'is-champ': team.team === podium[0]?.team }"
              >
                <td class="num rank-cell">{{ i + 1 }}</td>
                <td>
                  <RouterLink :to="`/team/${teamSlug(team.team)}`" class="team-link">
                    {{ team.team }}
                  </RouterLink>
                  <span v-if="team.team === podium[0]?.team" class="champ-tag">Champions</span>
                  <span class="sub-line">{{ team.swimmers }} swimmers</span>
                </td>
                <td class="num total">{{ team.points.toLocaleString() }}</td>
                <td class="num champs-cell">
                  {{ champPoints.get(team.team)?.toLocaleString() ?? '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Meets -->
    <section>
      <SectionHead
        title="The season"
        sub="Divisions raced separately for Meets 1–3, then everyone met at the Championship."
      />
      <div class="timeline">
        <div v-for="round in rounds" :key="round.date" class="round">
          <p class="round-head">
            <span class="round-label">{{ round.label }}</span>
            <span class="round-date">{{ round.dateDisplay }}</span>
          </p>
          <RouterLink
            v-for="meet in round.meets"
            :key="meet.id"
            :to="`/meet/${meet.id}`"
            class="card card-pad card-link meet"
          >
            <div class="meet-top">
              <span class="badge" :class="divisionTone(meet.division)">{{ meet.division }}</span>
              <span class="venue">{{ meet.venue }}</span>
            </div>
            <p v-if="meet.team_scores[0]" class="meet-winner">
              Won by {{ meet.team_scores[0].team }}
            </p>
            <p class="meet-meta num">
              {{ meet.result_count }} results · {{ meet.event_count }} events
            </p>
          </RouterLink>
        </div>

        <div v-if="championship" class="round">
          <p class="round-head">
            <span class="round-label finale">Finale</span>
            <span class="round-date">{{ championship.date_display }}</span>
          </p>
          <RouterLink :to="`/meet/${championship.id}`" class="card card-pad card-link champ">
            <span class="badge solid">Both divisions</span>
            <h3>Championship</h3>
            <p class="venue">{{ championship.venue }}</p>
            <p v-if="podium[0]" class="meet-winner first-text">Won by {{ podium[0].team }}</p>
            <p class="meet-meta num">
              {{ championship.result_count }} results · {{ championship.event_count }} events
            </p>
          </RouterLink>
        </div>
      </div>
    </section>

    <!-- Leaders -->
    <section>
      <SectionHead title="Season leaders" :sub="currentLeaders?.hint">
        <template #actions>
          <SegmentedControl
            v-model="activeLeaderboard"
            :options="leaderCategories.map((c) => ({ id: c.id, label: c.label }))"
          />
        </template>
      </SectionHead>

      <ol class="leaders card">
        <li v-for="(row, i) in currentLeaders?.rows ?? []" :key="row.key">
          <RouterLink :to="`/swimmer/${athleteSlug(row.key)}`" class="leader">
            <span class="lead-rank num" :class="{ top: i < 3 }">{{ i + 1 }}</span>
            <span class="lead-name">
              <span class="name">{{ row.name }}</span>
              <span class="team">{{ row.team }}</span>
            </span>
            <span class="lead-value">
              <span class="v num">{{ row.label }}</span>
              <span class="d">{{ row.detail }}</span>
            </span>
          </RouterLink>
        </li>
      </ol>
    </section>

    <!-- Fastest swims -->
    <section>
      <SectionHead
        title="Fastest swim of the season"
        sub="The quickest time recorded in each event by anyone in the league."
      >
        <template #actions>
          <RouterLink to="/leaderboards" class="btn">All leaderboards</RouterLink>
        </template>
      </SectionHead>

      <div class="fastest">
        <RouterLink
          v-for="swim in bestSwims"
          :key="swim.athleteKey + swim.time"
          :to="`/swimmer/${athleteSlug(swim.athleteKey)}`"
          class="card card-pad card-link swim"
        >
          <p class="swim-event">{{ shortEvent(swim.eventKey) }}</p>
          <p class="swim-time num">{{ swim.time }}</p>
          <p class="swim-who">{{ swim.name }}</p>
          <p class="swim-meta">{{ swim.team }} · {{ swim.meet }}</p>
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* Hero */
.hero {
  display: grid;
  /* Percentage aside so the headline column absorbs the leftover space at wide
     sizes and the panel gives space back on narrow laptops. */
  grid-template-columns: minmax(0, 1fr) minmax(0, 34%);
  gap: 2.5rem;
  align-items: center;
  padding: 1.5rem 0 0.5rem;
}

.hero h1 {
  margin-top: 0.5rem;
  /* Scales off the viewport but the headline sits in a ~65% column, so the
     middle term stays well under the old 5.2vw to avoid a stray third line. */
  font-size: clamp(2.1rem, 4.2vw, 3.4rem);
  font-weight: 800;
  letter-spacing: -0.038em;
  line-height: 1.03;
}

.hero h1 .accent {
  color: var(--water-500);
}

.lede {
  margin-top: 0.9rem;
  color: var(--ink-soft);
  font-size: 1rem;
  max-width: 38rem;
  line-height: 1.6;
}

.quick-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  column-gap: 1rem;
  margin-top: 1.5rem;
  padding: 0 0.15rem;
}

/* Each figure sits under its own short rule with a coloured cap on the left —
   a nod to the lane markings on a pool floor, and quieter than four boxes. */
.stat {
  position: relative;
  padding-top: 0.6rem;
  border-top: 1px solid var(--hairline);
}

.stat::before {
  content: '';
  position: absolute;
  top: -1px;
  left: 0;
  width: 22px;
  height: 2px;
  border-radius: 999px;
  background: var(--water-400);
}

.stat.gain::before {
  background: var(--gain);
}

.stat dd {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: var(--water-900);
}

.stat.gain dd {
  color: var(--gain);
}

.stat dt {
  margin-top: 0.05rem;
  font-size: 0.68rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--ink-faint);
}

/* Championship podium */
.podium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.7rem;
  /* Plaques sit at different heights, so anchor every column to the pedestal
     line at the bottom rather than the top of the card. */
  align-items: end;
}

.spot {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* Ranks read 1,2,3 in the markup for screen readers; on screen the winner
   takes the centre plinth with second left and third right. */
.spot.first {
  order: 2;
}
.spot.second {
  order: 1;
}
.spot.third {
  order: 3;
}

.plaque {
  display: block;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-bottom: 0;
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 1rem 1.05rem 0.9rem;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.plaque:hover {
  box-shadow: var(--shadow);
  transform: translateY(-2px);
}

.first .plaque {
  border-color: var(--first-edge);
  background: linear-gradient(180deg, var(--first-bg) 0%, var(--surface) 55%);
  padding-top: 1.35rem;
}
.second .plaque {
  background: linear-gradient(180deg, var(--second-bg) 0%, var(--surface) 55%);
}
.third .plaque {
  background: linear-gradient(180deg, var(--third-bg) 0%, var(--surface) 55%);
}

.medal {
  display: block;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--ink-faint);
}

.first .medal {
  color: var(--first);
}
.second .medal {
  color: var(--second);
}
.third .medal {
  color: var(--third);
}

.team {
  display: block;
  margin-top: 0.3rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.02rem;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--water-900);
}

.first .team {
  font-size: 1.25rem;
}

.pts {
  display: block;
  margin-top: 0.55rem;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.5rem;
  line-height: 1;
  letter-spacing: -0.03em;
  color: var(--water-800);
}

.first .pts {
  font-size: 1.9rem;
  color: var(--water-900);
}

.pts-label {
  display: block;
  margin-top: 0.15rem;
  font-size: 0.65rem;
  color: var(--ink-faint);
}

.split {
  display: flex;
  height: 5px;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.8rem;
  background: var(--surface-sunk);
}

.bar.ind {
  background: var(--water-500);
}
.bar.rel {
  background: var(--relay);
}

.split-legend {
  display: flex;
  gap: 0.85rem;
  margin-top: 0.4rem;
  font-size: 0.68rem;
  color: var(--ink-faint);
}

.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 0.3rem;
}

.dot.ind {
  background: var(--water-500);
}
.dot.rel {
  background: var(--relay);
}

.pedestal {
  display: grid;
  place-items: center;
  border-radius: 0 0 var(--radius) var(--radius);
  color: #fff;
}

.first .pedestal {
  height: 74px;
  background: linear-gradient(180deg, #2b8ede 0%, #0b5ea8 100%);
}
.second .pedestal {
  height: 52px;
  background: linear-gradient(180deg, #6fa3c9 0%, #3d7ba3 100%);
}
.third .pedestal {
  height: 38px;
  background: linear-gradient(180deg, #9dbdd2 0%, #6b93ad 100%);
}

.place {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 800;
  line-height: 1;
  color: rgba(255, 255, 255, 0.95);
}

.first .place {
  font-size: 2rem;
}

.margin-note {
  margin-top: 0.9rem;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--ink-soft);
}

.margin-note strong {
  color: var(--water-900);
  font-weight: 700;
}

.note {
  margin-bottom: 0.8rem;
  padding: 0.55rem 0.8rem;
  border-left: 3px solid var(--water-400, var(--water-500));
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--water-050);
  font-size: 0.8125rem;
  color: var(--ink-soft);
}

/* Standings */
.standings {
  display: grid;
  /* minmax(0,…) so the table's min-content width can't widen the column and
     push the whole page sideways on phones. */
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.standings .table-scroll {
  max-height: 380px;
  overflow-y: auto;
}

.rank-cell {
  color: var(--ink-faint);
  width: 1%;
}

.team-link {
  font-weight: 600;
  color: var(--water-800);
}

.team-link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.sub-line {
  display: block;
  font-size: 0.7rem;
  color: var(--ink-faint);
  margin-top: 0.05rem;
}

.total {
  font-weight: 700;
  color: var(--water-900);
}

.champs-cell {
  color: var(--ink-soft);
}

.is-champ .champs-cell {
  font-weight: 700;
  color: var(--first);
}

.champ-tag {
  display: inline-block;
  margin-left: 0.4rem;
  padding: 0.05rem 0.36rem;
  border-radius: 999px;
  background: var(--first-bg);
  color: var(--first);
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  vertical-align: 1px;
}

/* Season timeline */
.timeline {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.7rem;
  align-items: start;
}

.round {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.5rem;
  align-content: start;
}

.round-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.15rem;
  border-bottom: 2px solid var(--hairline);
}

.round-label {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--water-700);
}

.round-label.finale {
  color: var(--first);
}

.round-date {
  font-size: 0.68rem;
  color: var(--ink-faint);
  font-variant-numeric: tabular-nums;
}

.meet-top {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.venue {
  font-size: 0.8125rem;
  font-weight: 550;
  color: var(--water-900);
}

.meet-winner {
  margin-top: 0.35rem;
  font-size: 0.72rem;
  font-weight: 550;
  color: var(--water-700);
}

.meet-winner.first-text {
  color: var(--first);
}

.meet-meta {
  margin-top: 0.15rem;
  font-size: 0.7rem;
  color: var(--ink-faint);
}

.champ {
  background: linear-gradient(160deg, var(--first-bg) 0%, var(--surface) 60%);
  border-color: var(--first-edge);
  min-height: 100%;
}

.champ h3 {
  font-size: 1.15rem;
  margin-top: 0.5rem;
}

.champ .venue {
  display: block;
  margin-top: 0.1rem;
  font-weight: 400;
  color: var(--ink-soft);
}

/* Leaders */
.leaders {
  padding: 0.3rem;
  /* Column-major so ranks 1–5 read down the left, 6–10 down the right. */
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(5, auto);
  grid-auto-columns: 1fr;
  column-gap: 0.5rem;
}

.leaders li:nth-child(-n + 5) {
  border-right: 1px solid var(--hairline);
}

.leader {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.5rem 0.6rem;
  border-radius: var(--radius-sm);
}

.leader:hover {
  background: var(--water-050);
}

.lead-rank {
  width: 1.4rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--ink-faint);
  text-align: right;
  flex-shrink: 0;
}

.lead-rank.top {
  color: var(--first);
}

.lead-name {
  flex: 1;
  min-width: 0;
}

.lead-name .name {
  display: block;
  font-weight: 550;
  color: var(--water-900);
  font-size: 0.9rem;
}

.lead-name .team {
  display: block;
  font-size: 0.72rem;
  color: var(--ink-faint);
}

.lead-value {
  text-align: right;
  flex-shrink: 0;
}

.lead-value .v {
  display: block;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--water-800);
  font-size: 0.95rem;
}

.lead-value .d {
  display: block;
  font-size: 0.68rem;
  color: var(--ink-faint);
}

/* Fastest swims */
.fastest {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(178px, 1fr));
  gap: 0.7rem;
}

.swim-event {
  font-size: 0.7rem;
  font-weight: 650;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--water-600);
}

.swim-time {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--water-900);
  margin-top: 0.3rem;
  line-height: 1;
}

.swim-who {
  margin-top: 0.5rem;
  font-weight: 550;
  font-size: 0.875rem;
}

.swim-meta {
  font-size: 0.72rem;
  color: var(--ink-faint);
  margin-top: 0.1rem;
}

@media (max-width: 900px) {
  .standings {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* Below this the sticky header exposes its own search, so the hero panel drops
   under the headline and keeps only the stats. */
@media (max-width: 880px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.5rem;
  }

  .aside-search {
    display: none;
  }

  .quick-stats {
    margin-top: 0;
  }
}

@media (max-width: 860px) {
  .timeline {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .podium,
  .timeline {
    grid-template-columns: 1fr;
  }

  /* Stacked, the staggered plinths lose their meaning, so fall back to a
     ranked list with a uniform base strip in 1-2-3 order. */
  .spot.first,
  .spot.second,
  .spot.third {
    order: 0;
  }

  .first .plaque {
    padding-top: 1rem;
  }

  .first .team {
    font-size: 1.1rem;
  }

  .first .pts {
    font-size: 1.6rem;
  }

  .first .pedestal,
  .second .pedestal,
  .third .pedestal {
    height: 30px;
  }

  .place,
  .first .place {
    font-size: 1.05rem;
  }

  .leaders {
    grid-auto-flow: row;
    grid-template-rows: none;
  }

  .leaders li:nth-child(-n + 5) {
    border-right: 0;
  }

  .fastest {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}
</style>
