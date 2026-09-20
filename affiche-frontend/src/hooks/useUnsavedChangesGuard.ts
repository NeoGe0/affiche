import { useEffect } from 'react';
import { useBlocker, type Location } from 'react-router-dom';

export function useUnsavedChangesGuard(
  hasUnsavedChanges: boolean,
  isSameScreen: (from: Location, to: Location) => boolean = () => false,
) {
  const blocker = useBlocker(({ currentLocation, nextLocation }) =>
    hasUnsavedChanges && !isSameScreen(currentLocation, nextLocation));

  useEffect(() => {
    if (!hasUnsavedChanges) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [hasUnsavedChanges]);

  return {
    isAsking: blocker.state === 'blocked',
    stay: () => blocker.reset?.(),
    leave: () => blocker.proceed?.(),
  };
}
