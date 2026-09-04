const cachedUrls = new Set<string>();
let installed = false;

export function markCached(url: string) {
  install();
  cachedUrls.add(url);
}

function isCached(src: string) {
  if (!src) return false;
  for (const url of cachedUrls) {
    if (src.includes(url)) return true;
  }
  return false;
}

function install() {
  if (installed) return;
  installed = true;
  Object.defineProperty(HTMLImageElement.prototype, 'complete', {
    configurable: true,
    get(this: HTMLImageElement) {
      return isCached(this.getAttribute('src') ?? '');
    },
  });
  Object.defineProperty(HTMLImageElement.prototype, 'naturalWidth', {
    configurable: true,
    get(this: HTMLImageElement) {
      return isCached(this.getAttribute('src') ?? '') ? 500 : 0;
    },
  });
}

export function resetCachedImages() {
  cachedUrls.clear();
  if (installed) {

    Reflect.deleteProperty(HTMLImageElement.prototype, 'complete');
    Reflect.deleteProperty(HTMLImageElement.prototype, 'naturalWidth');
    installed = false;
  }
}
