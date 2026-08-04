export function ordinal(n: number | null | undefined): string {
  if (n == null) return '—'
  const v = Math.abs(n)
  const mod100 = v % 100
  if (mod100 >= 10 && mod100 <= 20) return `${n}th`
  const suffix = ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[v % 10] ?? 'th'
  return `${n}${suffix}`
}

export function formatRank(
  place: number | null | undefined,
  field: number | null | undefined,
): string {
  if (place == null || field == null) return '—'
  return `${ordinal(place)} of ${field}`
}

export function formatSeconds(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return '—'
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60)
    const secs = seconds - mins * 60
    return `${mins}:${secs.toFixed(2).padStart(5, '0')}`
  }
  return seconds.toFixed(2)
}

/** Signed time delta, e.g. "-1.24s" for an improvement. */
export function formatDelta(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds) || seconds === 0) return '—'
  const sign = seconds > 0 ? '−' : '+'
  return `${sign}${Math.abs(seconds).toFixed(2)}s`
}

export function displayName(last: string, first: string): string {
  return `${first} ${last}`.trim()
}

export function splitRankDisplay(rankDisplay: string): string[] {
  return rankDisplay
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

/** 'first' | 'second' | 'third' for a podium place, otherwise null. */
export function podiumClass(place: number | null | undefined): string | null {
  if (place === 1) return 'first'
  if (place === 2) return 'second'
  if (place === 3) return 'third'
  return null
}

/** Short, human event label: "25 Free" rather than "25yd Freestyle". */
export function shortEvent(eventKey: string): string {
  return eventKey
    .replace(/yd\b/g, '')
    .replace('Freestyle Relay', 'Free Relay')
    .replace('Freestyle', 'Free')
    .replace('Butterfly', 'Fly')
    .replace('Backstroke', 'Back')
    .replace('Breaststroke', 'Breast')
    .replace(/\s+/g, ' ')
    .trim()
}

/** "Meet 1 D1" → "M1 D1", for tight table headers. */
export function shortMeet(meet: string): string {
  return meet.replace(/^Meet\s+/, 'M').replace('Championship', 'Champs')
}

export function pluralize(n: number, word: string, plural = `${word}s`): string {
  return `${n} ${n === 1 ? word : plural}`
}
