const rtf = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' });

const DIVISIONS: { amount: number; name: Intl.RelativeTimeFormatUnit }[] = [
  { amount: 60, name: 'seconds' },
  { amount: 60, name: 'minutes' },
  { amount: 24, name: 'hours' },
  { amount: 7, name: 'days' },
  { amount: 4.34524, name: 'weeks' },
  { amount: 12, name: 'months' },
  { amount: Number.POSITIVE_INFINITY, name: 'years' },
];

export function formatRelativeTime(dateStr: string): string {
  let duration = (new Date(dateStr).getTime() - Date.now()) / 1000;

  for (const division of DIVISIONS) {
    if (Math.abs(duration) < division.amount) {
      return rtf.format(Math.round(duration), division.name);
    }
    duration /= division.amount;
  }
  return dateStr;
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '--:--';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function formatDurationMs(ms: number): string {
  const totalSec = Math.round(ms / 1000);
  return formatDuration(totalSec);
}

export function formatNumber(n: number | null): string {
  if (n === null || n === undefined) return '-';
  return n.toLocaleString('pt-BR');
}

export function getYouTubeThumbnail(externalId: string): string {
  return `https://img.youtube.com/vi/${externalId}/mqdefault.jpg`;
}
