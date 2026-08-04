import { computed, ref, shallowRef } from 'vue'
import type {
  Athlete,
  AthletesIndex,
  MeetDetail,
  MeetInfo,
  MeetsIndex,
} from '../types/swim'
import {
  bestOverallFinishers,
  biggestImprovers,
  buildTeamStandings,
  busiestSwimmers,
  mostPoints,
  seasonStats,
  topAgeGroupWinners,
} from '../utils/aggregates'
import { athleteSlug, teamSlug } from '../utils/slug'

const meets = shallowRef<MeetInfo[]>([])
const athletes = shallowRef<Athlete[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const loaded = ref(false)

const meetDetails = shallowRef<Record<string, MeetDetail>>({})
const meetDetailPromises = new Map<string, Promise<MeetDetail>>()

let loadPromise: Promise<void> | null = null

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load ${url} (${res.status})`)
  return res.json() as Promise<T>
}

async function load() {
  if (loaded.value) return
  if (loadPromise) return loadPromise

  loadPromise = (async () => {
    loading.value = true
    error.value = null
    try {
      const [meetsIndex, athletesIndex] = await Promise.all([
        fetchJson<MeetsIndex>('/data/meets.json'),
        fetchJson<AthletesIndex>('/data/athletes.json'),
      ])
      meets.value = [...meetsIndex.meets].sort((a, b) => a.date.localeCompare(b.date))
      athletes.value = athletesIndex.athletes
      loaded.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load swim data'
    } finally {
      loading.value = false
    }
  })()

  return loadPromise
}

/** Meet result files are large, so they load on demand and stay cached. */
async function loadMeetDetail(id: string): Promise<MeetDetail> {
  const cached = meetDetails.value[id]
  if (cached) return cached

  const inflight = meetDetailPromises.get(id)
  if (inflight) return inflight

  const promise = fetchJson<MeetDetail>(`/data/meets/${id}.json`).then((detail) => {
    meetDetails.value = { ...meetDetails.value, [id]: detail }
    meetDetailPromises.delete(id)
    return detail
  })

  meetDetailPromises.set(id, promise)
  return promise
}

export function useSwimData() {
  const teamStandings = computed(() => buildTeamStandings(athletes.value))
  const stats = computed(() => seasonStats(athletes.value, meets.value))

  const leaderCategories = computed(() => [
    {
      id: 'wins',
      label: 'Age-group wins',
      hint: 'Most first-place finishes within their own age group.',
      rows: topAgeGroupWinners(athletes.value, 10),
    },
    {
      id: 'overall',
      label: 'Best overall finish',
      hint: 'Highest placing against every swimmer in the event, not just their age group.',
      rows: bestOverallFinishers(athletes.value, 10),
    },
    {
      id: 'improved',
      label: 'Most improved',
      hint: 'Total time dropped between a first swim and a season best.',
      rows: biggestImprovers(athletes.value, 10),
    },
    {
      id: 'points',
      label: 'Points scored',
      hint: 'Individual points contributed to their team total.',
      rows: mostPoints(athletes.value, 10),
    },
    {
      id: 'races',
      label: 'Most races',
      hint: 'Individual swims plus relay legs.',
      rows: busiestSwimmers(athletes.value, 10),
    },
  ])

  const athleteBySlug = computed(() => {
    const map = new Map<string, Athlete>()
    for (const a of athletes.value) map.set(athleteSlug(a.key), a)
    return map
  })

  const teamBySlug = computed(() => {
    const map = new Map<string, string>()
    for (const t of teamStandings.value) map.set(teamSlug(t.team), t.team)
    return map
  })

  function findAthlete(slug: string | undefined): Athlete | null {
    if (!slug) return null
    return athleteBySlug.value.get(slug) ?? null
  }

  function findAthleteByKey(key: string | undefined): Athlete | null {
    if (!key) return null
    return athletes.value.find((a) => a.key === key) ?? null
  }

  function findTeam(slug: string | undefined): string | null {
    if (!slug) return null
    return teamBySlug.value.get(slug) ?? null
  }

  function findMeet(id: string | undefined): MeetInfo | null {
    if (!id) return null
    return meets.value.find((m) => m.id === id) ?? null
  }

  const seasonLabel = computed(() => {
    if (!meets.value.length) return ''
    const first = meets.value[0]
    const last = meets.value[meets.value.length - 1]
    return first.id === last.id
      ? first.date_display
      : `${first.date_display} – ${last.date_display}`
  })

  return {
    meets,
    athletes,
    loading,
    error,
    loaded,
    meetDetails,
    teamStandings,
    stats,
    leaderCategories,
    seasonLabel,
    load,
    loadMeetDetail,
    findAthlete,
    findAthleteByKey,
    findTeam,
    findMeet,
  }
}
