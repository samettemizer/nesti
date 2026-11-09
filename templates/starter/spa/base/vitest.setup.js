// Nesti: jsdom lacks browser APIs PrimeVue calls while mounting (Select, the DataTable paginator, overlays).
if (typeof window.matchMedia !== 'function') {
  window.matchMedia = (query) => ({
    matches: false, media: query, onchange: null,
    addListener() {}, removeListener() {},
    addEventListener() {}, removeEventListener() {},
    dispatchEvent() { return false; },
  });
}
if (typeof globalThis.ResizeObserver !== 'function') {
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
}
