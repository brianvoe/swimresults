export interface MeetInfo {
  id: string
  short_name: string
  division: 'D1' | 'D2' | 'Combined'
  name: string
  venue: string
  date: string
  date_display: string
  source_pdf: string
  event_count: number
  result_count: number
  /** Precomputed so the home page can rank teams without the full result file. */
  team_scores: TeamStanding[]
  file: string
}

export interface MeetsIndex {
  meets: MeetInfo[]
}

export interface AthleteResult {
  meet_id: string
  meet: string
  meet_division: 'D1' | 'D2' | 'Combined'
  date: string
  event_code: string
  event_name: string
  event_key: string
  gender: string
  age_group: string
  distance: string | null
  stroke: string | null
  is_open: boolean
  place: number | null
  age_group_field: number | null
  overall_place: number | null
  overall_field: number | null
  overall_label: string | null
  rank_display: string
  age: number | null
  team: string | null
  team_code: string | null
  seed: string | null
  time: string | null
  time_seconds: number | null
  /** Faster than anyone has ever swum it — a timing error the meet still scored. */
  suspect_time?: boolean
  points: number | null
  status: string
}

export interface AthleteRelay {
  meet_id: string
  meet: string
  meet_division: 'D1' | 'D2' | 'Combined'
  date: string
  event_code: string
  event_name: string
  event_key: string
  leg: number | null
  place: number | null
  team: string | null
  relay: string | null
  division: string | null
  time: string | null
  time_seconds: number | null
  points: number | null
  status: string
}

export interface BestTime {
  time: string
  time_seconds: number
  meet: string
  date: string
  place: number | null
  age_group: string
  age_group_field: number | null
  overall_place: number | null
  overall_field: number | null
  overall_label: string | null
  rank_display: string
}

export interface AthleteSummary {
  races: number
  age_group_wins: number
  age_group_podiums: number
  age_group_races: number
  avg_age_group_finish: number | null
  avg_overall_finish: number | null
  best_overall_finish: number | null
  events_improved: number
  best_times: Record<string, BestTime>
}

export interface Athlete {
  key: string
  name: string
  first_name: string
  last_name: string
  search_names: string[]
  ages: number[]
  teams: string[]
  team_codes: string[]
  individual_result_count: number
  relay_count: number
  summary: AthleteSummary
  results: AthleteResult[]
  relays: AthleteRelay[]
}

export interface AthletesIndex {
  generated_from_meets: string[]
  athlete_count: number
  athletes: Athlete[]
}

export interface TeamStanding {
  team: string
  team_code: string | null
  points: number
  individual_points: number
  relay_points: number
  swimmers: number
  races: number
}

export interface TopPerformer {
  key: string
  name: string
  team: string | null
  value: number
  label: string
  detail?: string
}

/* ---------- Full meet results (data/meets/*.json) ---------- */

export interface MeetEventResult {
  place: number | null
  name: string
  first_name: string
  last_name: string
  age: number | null
  team: string | null
  team_code: string | null
  seed: string | null
  time: string | null
  time_seconds: number | null
  suspect_time?: boolean
  points: number | null
  status: string
  age_group_field: number | null
  overall_place: number | null
  overall_field: number | null
  overall_label: string | null
  athlete_key: string
}

export interface MeetRelaySwimmer {
  leg: number | null
  name: string
  first_name: string
  last_name: string
  age: number | null
  athlete_key: string
}

export interface MeetRelayResult {
  place: number | null
  team: string | null
  team_code: string | null
  relay: string | null
  division: string | null
  seed: string | null
  time: string | null
  time_seconds: number | null
  points: number | null
  status: string
  swimmers: MeetRelaySwimmer[]
  field_size: number | null
  overall_place: number | null
  overall_field: number | null
  overall_label: string | null
}

export interface MeetEvent {
  code: string
  number: number
  name: string
  gender: string
  age_group: string
  distance: string | null
  stroke: string | null
  event_key: string
  is_relay: boolean
  is_open: boolean
  results: (MeetEventResult | MeetRelayResult)[]
}

export interface MeetDetail extends Omit<MeetInfo, 'file'> {
  events: MeetEvent[]
}

/* ---------- Derived view models ---------- */

export interface LeaderboardRow {
  rank: number
  eventKey: string
  athleteKey: string
  name: string
  team: string | null
  age: number | null
  ageGroup: string
  gender: string
  time: string
  timeSeconds: number
  meet: string
  meetId: string
  date: string
}

export interface EventSummary {
  eventKey: string
  races: number
  /** Null when every swim in the event had a suspect clock. */
  best: AthleteResult | null
  first: AthleteResult | null
  delta: number
  wins: number
  podiums: number
  bestOverall: number | null
  series: { meet: string; seconds: number | null }[]
}