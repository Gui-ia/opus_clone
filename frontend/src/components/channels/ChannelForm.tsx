import { useState, useEffect } from 'react';
import type { ChannelCreate, ChannelResponse, ChannelUpdate, Platform, SourceType } from '../../types/channel';

interface Props {
  channel?: ChannelResponse | null;
  onSubmit: (data: ChannelCreate | ChannelUpdate) => void;
  onCancel: () => void;
  loading?: boolean;
}

const PLATFORMS: { value: Platform; label: string }[] = [
  { value: 'youtube', label: 'YouTube' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'tiktok', label: 'TikTok' },
];

const SOURCE_TYPES: { value: SourceType; label: string }[] = [
  { value: 'video', label: 'Video' },
  { value: 'shorts', label: 'Shorts' },
  { value: 'reels', label: 'Reels' },
  { value: 'feed', label: 'Feed' },
  { value: 'stories', label: 'Stories' },
  { value: 'live', label: 'Live' },
];

export function ChannelForm({ channel, onSubmit, onCancel, loading }: Props) {
  const isEdit = !!channel;

  const [platform, setPlatform] = useState<Platform>(channel?.platform || 'youtube');
  const [externalId, setExternalId] = useState(channel?.external_id || '');
  const [username, setUsername] = useState(channel?.username || '');
  const [displayName, setDisplayName] = useState(channel?.display_name || '');
  const [pollInterval, setPollInterval] = useState(channel?.poll_interval_seconds || 900);
  const [sourceTypes, setSourceTypes] = useState<SourceType[]>(
    (channel?.source_types as SourceType[]) || ['video'],
  );
  const [minViralScore, setMinViralScore] = useState(channel?.min_viral_score || 65);
  const [maxClips, setMaxClips] = useState(channel?.max_clips_per_video || 8);
  const [stylePreset, setStylePreset] = useState(channel?.style_preset || 'default');

  useEffect(() => {
    if (channel) {
      setPlatform(channel.platform);
      setExternalId(channel.external_id);
      setUsername(channel.username);
      setDisplayName(channel.display_name || '');
      setPollInterval(channel.poll_interval_seconds);
      setSourceTypes((channel.source_types as SourceType[]) || ['video']);
      setMinViralScore(channel.min_viral_score);
      setMaxClips(channel.max_clips_per_video);
      setStylePreset(channel.style_preset);
    }
  }, [channel]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isEdit) {
      const update: ChannelUpdate = {};
      if (displayName !== (channel!.display_name || '')) update.display_name = displayName || null;
      if (pollInterval !== channel!.poll_interval_seconds) update.poll_interval_seconds = pollInterval;
      if (minViralScore !== channel!.min_viral_score) update.min_viral_score = minViralScore;
      if (maxClips !== channel!.max_clips_per_video) update.max_clips_per_video = maxClips;
      if (stylePreset !== channel!.style_preset) update.style_preset = stylePreset;
      if (JSON.stringify(sourceTypes) !== JSON.stringify(channel!.source_types))
        update.source_types = sourceTypes;
      onSubmit(update);
    } else {
      onSubmit({
        platform,
        external_id: externalId,
        username,
        display_name: displayName || undefined,
        poll_interval_seconds: pollInterval,
        source_types: sourceTypes,
        min_viral_score: minViralScore,
        max_clips_per_video: maxClips,
        style_preset: stylePreset,
      } as ChannelCreate);
    }
  };

  const toggleSourceType = (st: SourceType) => {
    setSourceTypes((prev) =>
      prev.includes(st) ? prev.filter((s) => s !== st) : [...prev, st],
    );
  };

  const inputClass =
    'w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-violet-500 focus:outline-none';
  const labelClass = 'block text-sm font-medium text-gray-300 mb-1';

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {!isEdit && (
        <>
          <div>
            <label className={labelClass}>Plataforma</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value as Platform)}
              className={inputClass}
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>ID Externo</label>
            <input
              type="text"
              value={externalId}
              onChange={(e) => setExternalId(e.target.value)}
              placeholder="UC..."
              required
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="@username"
              required
              className={inputClass}
            />
          </div>
        </>
      )}

      <div>
        <label className={labelClass}>Nome de Exibicao</label>
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Nome do canal"
          className={inputClass}
        />
      </div>

      <div>
        <label className={labelClass}>Intervalo de Poll (segundos)</label>
        <input
          type="number"
          value={pollInterval}
          onChange={(e) => setPollInterval(Number(e.target.value))}
          min={60}
          className={inputClass}
        />
      </div>

      <div>
        <label className={labelClass}>Tipos de Conteudo</label>
        <div className="flex flex-wrap gap-2">
          {SOURCE_TYPES.map((st) => (
            <button
              key={st.value}
              type="button"
              onClick={() => toggleSourceType(st.value)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                sourceTypes.includes(st.value)
                  ? 'bg-violet-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Score Viral Min</label>
          <input
            type="number"
            value={minViralScore}
            onChange={(e) => setMinViralScore(Number(e.target.value))}
            min={0}
            max={100}
            className={inputClass}
          />
        </div>
        <div>
          <label className={labelClass}>Max Clips/Video</label>
          <input
            type="number"
            value={maxClips}
            onChange={(e) => setMaxClips(Number(e.target.value))}
            min={1}
            className={inputClass}
          />
        </div>
      </div>

      <div>
        <label className={labelClass}>Style Preset</label>
        <select
          value={stylePreset}
          onChange={(e) => setStylePreset(e.target.value)}
          className={inputClass}
        >
          <option value="default">Default</option>
          <option value="highlight">Highlight</option>
          <option value="minimal">Minimal</option>
        </select>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg px-4 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700 disabled:opacity-50"
        >
          {loading ? 'Salvando...' : isEdit ? 'Salvar' : 'Criar Canal'}
        </button>
      </div>
    </form>
  );
}
