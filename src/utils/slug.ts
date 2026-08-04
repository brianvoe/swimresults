/**
 * Athlete keys are "last|first" and team names are free text; both need to
 * survive a round trip through the URL bar.
 */

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/** Keys are stored "last|first" but URLs read better as first-last. */
export function athleteSlug(key: string): string {
  const [last, first] = key.split('|')
  return slugify(first ? `${first} ${last}` : last)
}

export function teamSlug(team: string): string {
  return slugify(team)
}
