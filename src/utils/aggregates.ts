import type {
  Athlete,
  AthleteResult,
  EventSummary,
  LeaderboardRow,
  MeetDetail,
  MeetEventResult,
  MeetInfo,
  MeetRelayResult,
  TeamStanding,
  TopPerformer,
} from '../types/swim'

/** Preferred display order for the league's standard event lineup. */
const EVENT_ORDER = [
  '25yd Freestyle',
  '25yd Backstroke',
  '25yd Breaststroke',
  '25yd Butterfly',
  '50yd IM',
  '100yd IM',
  'Open 50 Free',
  '100yd Medley Relay',
  '100yd Freestyle Relay',
]

export function sortEventKeys(keys: Iterable<string>): string[] {
  return [...new Set(keys)].sort((a, b) => {
    const ia = EVENT_ORDER.indexOf(a)
    const ib = EVENT_ORDER.indexOf(b)
    if (ia !== -1 && ib !== -1) return ia - ib
    if (ia !== -1) return -1
    if (ib !== -1) return 1
    return a.localeCompare(b)
  })
}

function fullName(a: Athlete): string {
  return `${a.first_name} ${a.last_name}`.trim()
}

/**
 * A swim whose clock we trust. Suspect times still count as races and keep the
 * points the meet awarded, but they never set a record or a personal best.
 */
export function isTimed<
  T extends { status: string; time_seconds: number | null; suspect_time?: boolean },
>(r: T): r is T & { time_seconds: number } {
  return r.status === 'official' && r.time_seconds != null && !r.suspect_time
}

/* ---------------------------------------------------------------- teams */

export function buildTeamStandings(athletes: Athlete[]): TeamStanding[] {
  const map = new Map<string, TeamStanding & { swimmerKeys: Set<string> }>()

  const ensure = (team: string, code: string | null = null) => {
    let row = map.get(team)
    if (!row) {
      row = {
        team,
        team_code: code,
        points: 0,
        individual_points: 0,
        relay_points: 0,
        swimmers: 0,
        races: 0,
        swimmerKeys: new Set(),
      }
      map.set(team, row)
    } else if (!row.team_code && code) {
      row.team_code = code
    }
    return row
  }

  for (const athlete of athletes) {
    for (const team of athlete.teams) {
      ensure(team, athlete.team_codes[0] ?? null).swimmerKeys.add(athlete.key)
    }

    for (const result of athlete.results) {
      if (!result.team) continue
      const row = ensure(result.team, result.team_code)
      row.swimmerKeys.add(athlete.key)
      if (result.status === 'official') row.races += 1
      if (result.points != null) row.individual_points += result.points
    }
  }

  // Count each relay once (same meet/event/team/letter/time).
  const relaySeen = new Set<string>()
  for (const athlete of athletes) {
    for (const relay of athlete.relays) {
      if (!relay.team || relay.points == null || relay.status !== 'official') continue
      const key = `${relay.meet_id}|${relay.event_code}|${relay.team}|${relay.relay}|${relay.time}`
      if (relaySeen.has(key)) continue
      relaySeen.add(key)
      ensure(relay.team).relay_points += relay.points
    }
  }

  return [...map.values()]
    .map(({ swimmerKeys, ...rest }) => ({
      ...rest,
      swimmers: swimmerKeys.size,
      points: rest.individual_points + rest.relay_points,
    }))
    .filter((row) => row.points > 0 || row.swimmers > 0)
    .sort((a, b) => b.points - a.points)
}

export function athletesForTeam(athletes: Athlete[], team: string): Athlete[] {
  return athletes
    .filter((a) => a.teams.includes(team) || a.results.some((r) => r.team === team))
    .sort((a, b) => {
      const pa = a.results.reduce((s, r) => s + (r.points ?? 0), 0)
      const pb = b.results.reduce((s, r) => s + (r.points ?? 0), 0)
      if (pa !== pb) return pb - pa
      return a.last_name.localeCompare(b.last_name)
    })
}

/** Points a team scored at each meet, for the team page trend. */
export function teamPointsByMeet(
  athletes: Athlete[],
  team: string,
  meets: MeetInfo[],
): { meet: string; individual: number; relay: number; total: number }[] {
  const byMeet = new Map<string, { individual: number; relay: number }>()
  for (const m of meets) byMeet.set(m.short_name, { individual: 0, relay: 0 })

  for (const athlete of athletes) {
    for (const r of athlete.results) {
      if (r.team !== team || r.points == null) continue
      const row = byMeet.get(r.meet)
      if (row) row.individual += r.points
    }
  }

  const seen = new Set<string>()
  for (const athlete of athletes) {
    for (const r of athlete.relays) {
      if (r.team !== team || r.points == null || r.status !== 'official') continue
      const dedupe = `${r.meet_id}|${r.event_code}|${r.relay}|${r.time}`
      if (seen.has(dedupe)) continue
      seen.add(dedupe)
      const row = byMeet.get(r.meet)
      if (row) row.relay += r.points
    }
  }

  return [...byMeet.entries()].map(([meet, v]) => ({
    meet,
    ...v,
    total: v.individual + v.relay,
  }))
}

/* --------------------------------------------------------- leaderboards */

export function topAgeGroupWinners(athletes: Athlete[], limit = 8): TopPerformer[] {
  return athletes
    .filter((a) => a.summary.age_group_wins > 0)
    .sort(
      (a, b) =>
        b.summary.age_group_wins - a.summary.age_group_wins ||
        (a.summary.avg_age_group_finish ?? 99) - (b.summary.avg_age_group_finish ?? 99),
    )
    .slice(0, limit)
    .map((a) => ({
      key: a.key,
      name: fullName(a),
      team: a.teams[0] ?? null,
      value: a.summary.age_group_wins,
      label: `${a.summary.age_group_wins}`,
      detail: `first place${a.summary.age_group_wins === 1 ? '' : 's'}`,
    }))
}

export function bestOverallFinishers(athletes: Athlete[], limit = 8): TopPerformer[] {
  return athletes
    .filter((a) => a.summary.best_overall_finish != null)
    .sort((a, b) => {
      const ba = a.summary.best_overall_finish ?? 999
      const bb = b.summary.best_overall_finish ?? 999
      if (ba !== bb) return ba - bb
      return (a.summary.avg_overall_finish ?? 999) - (b.summary.avg_overall_finish ?? 999)
    })
    .slice(0, limit)
    .map((a) => ({
      key: a.key,
      name: fullName(a),
      team: a.teams[0] ?? null,
      value: a.summary.best_overall_finish ?? 0,
      label: `${a.summary.best_overall_finish}`,
      detail: 'vs the whole field',
    }))
}

/** Swimmers who dropped the most total time across their events. */
export function biggestImprovers(athletes: Athlete[], limit = 8): TopPerformer[] {
  return athletes
    .map((a) => {
      const rows = improvementSeries(a)
      const total = rows.reduce((s, r) => s + r.delta, 0)
      return { athlete: a, total, events: rows.length }
    })
    .filter((r) => r.total > 0 && r.events > 0)
    .sort((a, b) => b.total - a.total)
    .slice(0, limit)
    .map(({ athlete, total, events }) => ({
      key: athlete.key,
      name: fullName(athlete),
      team: athlete.teams[0] ?? null,
      value: Number(total.toFixed(2)),
      label: `−${total.toFixed(2)}s`,
      detail: `across ${events} event${events === 1 ? '' : 's'}`,
    }))
}

export function busiestSwimmers(athletes: Athlete[], limit = 8): TopPerformer[] {
  return athletes
    .map((a) => ({ a, races: a.summary.races + a.relay_count }))
    .filter((r) => r.races > 0)
    .sort((x, y) => y.races - x.races)
    .slice(0, limit)
    .map(({ a, races }) => ({
      key: a.key,
      name: fullName(a),
      team: a.teams[0] ?? null,
      value: races,
      label: `${races}`,
      detail: 'races swum',
    }))
}

export function mostPoints(athletes: Athlete[], limit = 8): TopPerformer[] {
  return athletes
    .map((a) => ({
      a,
      points: a.results.reduce((s, r) => s + (r.points ?? 0), 0),
    }))
    .filter((r) => r.points > 0)
    .sort((x, y) => y.points - x.points)
    .slice(0, limit)
    .map(({ a, points }) => ({
      key: a.key,
      name: fullName(a),
      team: a.teams[0] ?? null,
      value: points,
      label: `${points}`,
      detail: 'individual points',
    }))
}

/**
 * Season-best time for every athlete in one event, ranked. Age group and
 * gender narrow the field the way the meet program would.
 */
export function leaderboard(
  athletes: Athlete[],
  eventKey: string,
  options: { gender?: string; ageGroup?: string; limit?: number } = {},
): LeaderboardRow[] {
  const { gender = 'all', ageGroup = 'all', limit = 25 } = options
  const rows: { athlete: Athlete; result: AthleteResult }[] = []

  for (const athlete of athletes) {
    let best: AthleteResult | null = null
    for (const r of athlete.results) {
      if (r.event_key !== eventKey) continue
      if (!isTimed(r)) continue
      if (gender !== 'all' && r.gender !== gender) continue
      if (ageGroup !== 'all' && r.age_group !== ageGroup) continue
      if (!best || r.time_seconds < best.time_seconds!) best = r
    }
    if (best) rows.push({ athlete, result: best })
  }

  return rows
    .sort((a, b) => a.result.time_seconds! - b.result.time_seconds!)
    .slice(0, limit)
    .map(({ athlete, result }, i) => ({
      rank: i + 1,
      eventKey,
      athleteKey: athlete.key,
      name: fullName(athlete),
      team: result.team ?? athlete.teams[0] ?? null,
      age: result.age,
      ageGroup: result.age_group,
      gender: result.gender,
      time: result.time!,
      timeSeconds: result.time_seconds!,
      meet: result.meet,
      meetId: result.meet_id,
      date: result.date,
    }))
}

export function allEventKeys(athletes: Athlete[]): string[] {
  const keys = new Set<string>()
  for (const a of athletes) {
    for (const r of a.results) if (r.status === 'official') keys.add(r.event_key)
  }
  return sortEventKeys(keys)
}

export function allAgeGroups(athletes: Athlete[]): string[] {
  const groups = new Set<string>()
  for (const a of athletes) {
    for (const r of a.results) if (!r.is_open) groups.add(r.age_group)
  }
  return [...groups].sort()
}

/** The single fastest swim of the season in each event. */
export function seasonBestSwims(athletes: Athlete[]): LeaderboardRow[] {
  return allEventKeys(athletes)
    .flatMap((key) => leaderboard(athletes, key, { limit: 1 }))
    .filter(Boolean)
}

/* --------------------------------------------------------------- season */

export function seasonStats(athletes: Athlete[], meets: MeetInfo[]) {
  const officialRaces = athletes.reduce(
    (sum, a) => sum + a.results.filter((r) => r.status === 'official').length,
    0,
  )
  const teams = new Set(athletes.flatMap((a) => a.teams))
  const improved = athletes.filter((a) => a.summary.events_improved > 0).length
  return {
    meetCount: meets.length,
    athleteCount: athletes.length,
    teamCount: teams.size,
    raceCount: officialRaces,
    improvedCount: improved,
  }
}

/* -------------------------------------------------------------- athlete */

export function athleteEvents(athlete: Athlete): string[] {
  const keys = new Set<string>()
  for (const r of athlete.results) {
    if (r.status === 'official' || r.status === 'NS') keys.add(r.event_key)
  }
  return sortEventKeys(keys)
}

export function improvementSeries(athlete: Athlete) {
  const byEvent = new Map<string, { first: number; best: number; meet: string }>()
  const official = [...athlete.results]
    .filter(isTimed)
    .sort((a, b) => a.date.localeCompare(b.date))

  for (const r of official) {
    const cur = byEvent.get(r.event_key)
    if (!cur) {
      byEvent.set(r.event_key, {
        first: r.time_seconds!,
        best: r.time_seconds!,
        meet: r.meet,
      })
    } else if (r.time_seconds! < cur.best) {
      cur.best = r.time_seconds!
      cur.meet = r.meet
    }
  }

  return [...byEvent.entries()]
    .map(([event, v]) => ({
      event,
      delta: Number((v.first - v.best).toFixed(2)),
      first: v.first,
      best: v.best,
      meet: v.meet,
    }))
    .filter((row) => row.delta > 0)
    .sort((a, b) => b.delta - a.delta)
}

/** Per-event rollup powering the swimmer page event cards. */
export function athleteEventSummaries(athlete: Athlete, meetNames: string[]): EventSummary[] {
  const byEvent = new Map<string, AthleteResult[]>()
  for (const r of athlete.results) {
    if (r.status !== 'official' || r.time_seconds == null) continue
    const list = byEvent.get(r.event_key) ?? []
    list.push(r)
    byEvent.set(r.event_key, list)
  }

  return sortEventKeys(byEvent.keys()).map((eventKey) => {
    const races = [...byEvent.get(eventKey)!].sort((a, b) => a.date.localeCompare(b.date))
    // Every race counts towards the tally; only trusted clocks shape the times.
    const timed = races.filter(isTimed)
    const first = timed[0] ?? null
    const best = timed.length
      ? timed.reduce((acc, r) => (r.time_seconds! < acc.time_seconds! ? r : acc), timed[0])
      : null
    const overallPlaces = races
      .map((r) => r.overall_place)
      .filter((p): p is number => p != null)

    return {
      eventKey,
      races: races.length,
      best,
      first,
      delta: first && best ? Number((first.time_seconds! - best.time_seconds!).toFixed(2)) : 0,
      wins: races.filter((r) => !r.is_open && r.place === 1).length,
      podiums: races.filter((r) => !r.is_open && r.place != null && r.place <= 3).length,
      bestOverall: overallPlaces.length ? Math.min(...overallPlaces) : null,
      series: meetNames.map((meet) => ({
        meet,
        seconds: timed.find((r) => r.meet === meet)?.time_seconds ?? null,
      })),
    }
  })
}

/** One-sentence season summary shown at the top of a swimmer page. */
export function athleteHeadline(athlete: Athlete): string {
  const s = athlete.summary
  const parts: string[] = []
  const races = s.races + athlete.relay_count
  parts.push(`${races} race${races === 1 ? '' : 's'} across ${athlete.teams.length ? athlete.teams[0] : 'the season'}`)

  if (s.age_group_wins > 0) {
    parts.push(`${s.age_group_wins} age-group win${s.age_group_wins === 1 ? '' : 's'}`)
  } else if (s.age_group_podiums > 0) {
    parts.push(`${s.age_group_podiums} podium${s.age_group_podiums === 1 ? '' : 's'}`)
  }

  const drops = improvementSeries(athlete)
  if (drops.length) {
    const total = drops.reduce((sum, d) => sum + d.delta, 0)
    parts.push(`${total.toFixed(2)}s dropped over ${drops.length} event${drops.length === 1 ? '' : 's'}`)
  }

  if (s.best_overall_finish != null && s.best_overall_finish <= 10) {
    parts.push(`a top-${s.best_overall_finish <= 3 ? '3' : '10'} finish against the full field`)
  }

  return parts.join(' · ')
}

/* --------------------------------------------------------- meet detail */

export function isRelayResult(
  result: MeetEventResult | MeetRelayResult,
): result is MeetRelayResult {
  return 'swimmers' in result
}

/** Team scores for a single meet, computed from that meet's own results. */
export function meetTeamScores(meet: MeetDetail): TeamStanding[] {
  const map = new Map<string, TeamStanding>()
  const ensure = (team: string, code: string | null) => {
    let row = map.get(team)
    if (!row) {
      row = {
        team,
        team_code: code,
        points: 0,
        individual_points: 0,
        relay_points: 0,
        swimmers: 0,
        races: 0,
      }
      map.set(team, row)
    }
    return row
  }

  const swimmers = new Map<string, Set<string>>()

  for (const event of meet.events) {
    for (const result of event.results) {
      if (!result.team) continue
      const row = ensure(result.team, result.team_code)
      if (isRelayResult(result)) {
        if (result.status === 'official' && result.points != null) {
          row.relay_points += result.points
        }
        for (const s of result.swimmers) {
          const set = swimmers.get(result.team) ?? new Set()
          set.add(s.athlete_key)
          swimmers.set(result.team, set)
        }
      } else {
        if (result.status === 'official') row.races += 1
        if (result.points != null) row.individual_points += result.points
        const set = swimmers.get(result.team) ?? new Set()
        set.add(result.athlete_key)
        swimmers.set(result.team, set)
      }
    }
  }

  return [...map.values()]
    .map((row) => ({
      ...row,
      swimmers: swimmers.get(row.team)?.size ?? 0,
      points: row.individual_points + row.relay_points,
    }))
    .sort((a, b) => b.points - a.points)
}

export function meetStats(meet: MeetDetail) {
  let official = 0
  let swimmers = new Set<string>()
  let relays = 0

  for (const event of meet.events) {
    for (const result of event.results) {
      if (isRelayResult(result)) {
        if (result.status === 'official') relays += 1
        for (const s of result.swimmers) swimmers.add(s.athlete_key)
      } else {
        if (result.status === 'official') official += 1
        swimmers.add(result.athlete_key)
      }
    }
  }

  return {
    events: meet.events.length,
    officialSwims: official,
    relays,
    swimmers: swimmers.size,
    teams: new Set(
      meet.events.flatMap((e) => e.results.map((r) => r.team).filter(Boolean) as string[]),
    ).size,
  }
}
