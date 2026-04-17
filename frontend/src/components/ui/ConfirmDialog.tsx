import { Modal } from './Modal';

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: 'danger' | 'default';
  loading?: boolean;
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirmar',
  variant = 'default',
  loading = false,
}: Props) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-gray-400">{message}</p>
      <div className="mt-6 flex justify-end gap-3">
        <button
          onClick={onClose}
          className="rounded-lg px-4 py-2 text-sm text-gray-400 transition-colors hover:bg-gray-800"
        >
          Cancelar
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 ${
            variant === 'danger'
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-violet-600 text-white hover:bg-violet-700'
          }`}
        >
          {loading ? 'Aguarde...' : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
