<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useSwimData } from '../composables/useSwimData'
import { allAgeGroups, allEventKeys, leaderboard } from '../utils/aggregates'
import { shortEvent } from '../utils/format'
import { athleteSlug, teamSlug } from '../utils/slug'
import SectionHead from '../components/ui/SectionHead.vue'
import PlaceBadge from '../components/ui/PlaceBadge.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import SegmentedControl from '../components/ui/SegmentedControl.vue'

const route = useRoute()
const router = useRouter()
const { athletes, meets } = useSwimData()

const events = computed(() => allEventKeys(athletes.value))
const ageGroups = computed(() => allAgeGroups(athletes.value))

const event = ref((route.query.event as string) || '')
const gender = ref((route.query.gender as string) || 'all')
const ageGroup = ref((route.query.age as string) || 'all')

watch(
  events,
  (list) => {
    if (!event.value && list.length) event.value = list[0]
  },
  { immediate: true },
)

// Keep the URL in sync so a filtered leaderboard can be shared.
watch([event, gender, ageGroup], () => {
  router.replace({
    query: {
      event: event.value || undefined,
      gender: gender.value === 'all' ? undefined : gender.value,
      age: ageGroup.value === 'all' ? undefined : ageGroup.value,
    },
  })
})

const rows = computed(() =>
  event.value
    ? leaderboard(athletes.value, event.value, {
        gender: gender.value,
        ageGroup: ageGroup.value,
        limit: 50,
      })
    : [],
)

const meetIdFor = (name: string) => meets.value.find((m) => m.short_name === name)?.id

const gapToLeader = (seconds: number) => {
  if (!rows.value.length) return ''
  const diff = seconds - rows.value[0].timeSeconds
  return diff === 0 ? '—' : `+${diff.toFixed(2)}`
}
</script>

<template>
  <div class="shell stack rise-in">
    <SectionHead
      title="Leaderboards"
      sub="Every swimmer's fastest time of the season in one event, ranked against the whole league."
    />

    <div class="controls card card-pad">
      <div class="control">
        <span class="control-label">Event</span>
        <div class="chips">
          <button
            v-for="key in events"
            :key="key"
            type="button"
            class="chip"
            :class="{ active: event === key }"
            @click="event = key"
          >
            {{ shortEvent(key) }}
          </button>
        </div>
      </div>
      <div class="control-row">
        <div class="control">
          <span class="control-label">Gender</span>
          <SegmentedControl
            v-model="gender"
            size="sm"
            :options="[
              { id: 'all', label: 'All' },
              { id: 'Women', label: 'Women' },
              { id: 'Men', label: 'Men' },
              { id: 'Mixed', label: 'Mixed' },
            ]"
          />
        </div>
        <div class="control">
          <span class="control-label">Age group</span>
          <SegmentedControl
            v-model="ageGroup"
            size="sm"
            :options="[{ id: 'all', label: 'All' }, ...ageGroups.map((g) => ({ id: g, label: g }))]"
          />
        </div>
      </div>
    </div>

    <div v-if="!rows.length" class="card">
      <EmptyState
        title="No swims match these filters"
        message="Open events are not split by age group — try setting age back to All."
      />
    </div>

    <div v-else class="card table-scroll">
      <table class="data">
        <thead>
          <tr>
            <th class="num">#</th>
            <th>Swimmer</th>
            <th>Team</th>
            <th class="num">Age</th>
            <th>Group</th>
            <th class="num">Time</th>
            <th class="num">Gap</th>
            <th>Set at</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.athleteKey">
            <td class="num"><PlaceBadge :place="row.rank" compact /></td>
            <td>
              <RouterLink :to="`/swimmer/${athleteSlug(row.athleteKey)}`" class="link">
                {{ row.name }}
              </RouterLink>
            </td>
            <td>
              <RouterLink v-if="row.team" :to="`/team/${teamSlug(row.team)}`" class="soft-link">
                {{ row.team }}
              </RouterLink>
            </td>
            <td class="num faint">{{ row.age ?? '—' }}</td>
            <td class="faint">{{ row.ageGroup }}</td>
            <td class="num time strong">{{ row.time }}</td>
            <td class="num faint">{{ gapToLeader(row.timeSeconds) }}</td>
            <td>
              <RouterLink
                v-if="meetIdFor(row.meet)"
                :to="`/meet/${meetIdFor(row.meet)}`"
                class="soft-link"
              >
                {{ row.meet }}
              </RouterLink>
              <span v-else>{{ row.meet }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.9rem;
}

.control-label {
  display: block;
  font-size: 0.65rem;
  font-weight: 650;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--ink-faint);
  margin-bottom: 0.35rem;
}

.control-row {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.control {
  min-width: 0;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.chip {
  border: 1px solid var(--hairline-strong);
  background: var(--surface);
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--ink-soft);
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.chip:hover {
  border-color: var(--water-300);
  color: var(--ink);
}

.chip.active {
  background: var(--water-800);
  border-color: var(--water-800);
  color: #fff;
}

.link {
  font-weight: 550;
  color: var(--water-800);
}

.link:hover,
.soft-link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.soft-link {
  color: var(--ink-soft);
}

.strong {
  font-weight: 650;
  color: var(--water-900);
}
</style>
