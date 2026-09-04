import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import styles from './ToastContext.module.css';

export type ToastType = 'error' | 'success' | 'info';

interface Toast {
  id: number;
  type: ToastType;
  title?: string;
  message: string;
}

interface ShowToastOptions {
  title?: string;

  duration?: number;
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
    setToasts((prev) => [...prev, { id, type, message, title: options?.title }]);
    const duration = options?.duration ?? DEFAULT_DURATION[type];
    if (duration > 0) {
      window.setTimeout(() => remove(id), duration);
    }
  }, [remove]);

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
        {toasts.map((toast) => {
          const Icon = ICONS[toast.type];
          return (
            <div key={toast.id} className={`${styles.toast} ${styles[toast.type]}`} role="alert">
              <Icon size={18} className={styles.icon} />
              <div className={styles.body}>
                {toast.title && <div className={styles.title}>{toast.title}</div>}
                <div className={styles.message}>{toast.message}</div>
              </div>
              <button
                className={styles.close}
                onClick={() => remove(toast.id)}
                aria-label="Dismiss"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
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
