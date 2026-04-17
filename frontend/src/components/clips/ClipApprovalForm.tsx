import { useState } from 'react';
import { Check, X as XIcon } from 'lucide-react';
import type { ClipResponse, ClipApproval } from '../../types/clip';

interface Props {
  clip: ClipResponse;
  onApprove: (data?: ClipApproval) => void;
  onReject: () => void;
  loading?: boolean;
}

export function ClipApprovalForm({ clip, onApprove, onReject, loading }: Props) {
  const [title, setTitle] = useState(clip.title_suggestion || '');
  const [description, setDescription] = useState('');
  const [hashtagInput, setHashtagInput] = useState(
    clip.hashtags?.join(', ') || '',
  );

  const handleApprove = () => {
    const hashtags = hashtagInput
      .split(',')
      .map((h) => h.trim())
      .filter(Boolean);

    onApprove({
      title: title || undefined,
      description: description || undefined,
      hashtags: hashtags.length > 0 ? hashtags : undefined,
    });
  };

  const inputClass =
    'w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-violet-500 focus:outline-none';

  return (
    <div className="space-y-3 border-t border-gray-800 pt-4">
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Titulo
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Titulo do clip"
          className={inputClass}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Descricao
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Descricao opcional"
          rows={2}
          className={inputClass}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-400">
          Hashtags (separadas por virgula)
        </label>
        <input
          type="text"
          value={hashtagInput}
          onChange={(e) => setHashtagInput(e.target.value)}
          placeholder="#viral, #clips"
          className={inputClass}
        />
      </div>

      <div className="flex gap-2 pt-2">
        <button
          onClick={handleApprove}
          disabled={loading}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50"
        >
          <Check className="h-4 w-4" />
          Aprovar
        </button>
        <button
          onClick={onReject}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-lg bg-red-600/20 px-4 py-2.5 text-sm font-medium text-red-400 transition-colors hover:bg-red-600/30 disabled:opacity-50"
        >
          <XIcon className="h-4 w-4" />
          Rejeitar
        </button>
      </div>
    </div>
  );
}
