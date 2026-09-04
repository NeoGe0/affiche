type Entry = Pick<IntersectionObserverEntry, 'isIntersecting'>;

class StubIntersectionObserver {
  static instances: StubIntersectionObserver[] = [];

  callback: (entries: Entry[]) => void;

  constructor(callback: (entries: Entry[]) => void) {
    this.callback = callback;
    StubIntersectionObserver.instances.push(this);
  }

  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }

  trigger() {
    this.callback([{ isIntersecting: true }]);
  }
}

export function installIntersectionObserver() {
  StubIntersectionObserver.instances = [];

  globalThis.IntersectionObserver =
    StubIntersectionObserver as unknown as typeof IntersectionObserver;
}

export function latestObserver(): StubIntersectionObserver | undefined {
  return StubIntersectionObserver.instances.at(-1);
}
