import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import styles from './ToastContext.module.css';

export type ToastType = 'error' | 'success' | 'info';

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface Toast {
  id: number;
  type: ToastType;
  title?: string;
  message: string;
  action?: ToastAction;

  duration: number;
}

interface ShowToastOptions {
  title?: string;

  duration?: number;

  action?: ToastAction;
}

interface ToastContextValue {
  show: (type: ToastType, message: string, options?: ShowToastOptions) => void;
  error: (message: string, options?: ShowToastOptions) => void;
  success: (message: string, options?: ShowToastOptions) => void;
  info: (message: string, options?: ShowToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const DEFAULT_DURATION: Record<ToastType, number> = {
  success: 4000,
  info: 5000,
  error: 8000,
};

const ICONS = {
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((type: ToastType, message: string, options?: ShowToastOptions) => {
    const id = nextId.current++;
    const duration = options?.duration ?? DEFAULT_DURATION[type];
    setToasts((prev) => [...prev, { id, type, message, title: options?.title, action: options?.action, duration }]);
  }, []);

  const error = useCallback((m: string, o?: ShowToastOptions) => show('error', m, o), [show]);
  const success = useCallback((m: string, o?: ShowToastOptions) => show('success', m, o), [show]);
  const info = useCallback((m: string, o?: ShowToastOptions) => show('info', m, o), [show]);

  const value: ToastContextValue = useMemo(
    () => ({ show, error, success, info }),
    [show, error, success, info]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={styles.container} role="region" aria-label="Notifications">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={remove} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: number) => void }) {
  const [paused, setPaused] = useState(false);
  const Icon = ICONS[toast.type];
  const onDismiss = () => onRemove(toast.id);

  useEffect(() => {
    if (paused || toast.duration <= 0) return;
    const timer = window.setTimeout(() => onRemove(toast.id), toast.duration);
    return () => window.clearTimeout(timer);
  }, [paused, toast.duration, toast.id, onRemove]);

  return (
    <div
      className={`${styles.toast} ${styles[toast.type]}`}
      role={toast.type === 'error' ? 'alert' : 'status'}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <Icon size={18} className={styles.icon} />
      <div className={styles.body}>
        {toast.title && <div className={styles.title}>{toast.title}</div>}
        <div className={styles.message}>{toast.message}</div>
        {toast.action && (
          <button
            className={styles.action}
            onClick={() => {
              toast.action?.onClick();
              onDismiss();
            }}
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button className={styles.close} onClick={onDismiss} aria-label="Dismiss">
        <X size={14} />
      </button>
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (ctx === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}
