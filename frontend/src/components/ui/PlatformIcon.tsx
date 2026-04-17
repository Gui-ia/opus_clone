import { Play, Camera, Music } from 'lucide-react';
import type { Platform } from '../../types/channel';

const config: Record<Platform, { icon: typeof Play; className: string; label: string }> = {
  youtube:   { icon: Play,   className: 'text-red-500',  label: 'YouTube' },
  instagram: { icon: Camera, className: 'text-pink-500', label: 'Instagram' },
  tiktok:    { icon: Music,  className: 'text-cyan-400', label: 'TikTok' },
};

export function PlatformIcon({
  platform,
  size = 20,
}: {
  platform: Platform;
  size?: number;
}) {
  const { icon: Icon, className, label } = config[platform];
  return <Icon className={className} size={size} aria-label={label} />;
}
