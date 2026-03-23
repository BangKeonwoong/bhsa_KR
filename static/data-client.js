(function () {
  const runtimeState = {
    ready: null,
    mode: 'server',
    manifest: null,
  };

  function buildUrl(path) {
    return new URL(path, document.baseURI).toString();
  }

  async function detectRuntime() {
    if (runtimeState.ready) return runtimeState.ready;
    runtimeState.ready = (async () => {
      try {
        const res = await fetch(buildUrl('./data/manifest.json'), { cache: 'no-store' });
        if (res.ok) {
          runtimeState.manifest = await res.json();
          runtimeState.mode = 'static';
          return { mode: 'static', manifest: runtimeState.manifest };
        }
      } catch (e) {
        // ignore and fall back to server mode
      }
      runtimeState.manifest = null;
      runtimeState.mode = 'server';
      return { mode: 'server', manifest: null };
    })();
    return runtimeState.ready;
  }

  function runtimeMode() {
    return runtimeState.mode;
  }

  function manifest() {
    return runtimeState.manifest;
  }

  function availabilityFor(book, chapter) {
    const data = runtimeState.manifest && runtimeState.manifest.availability;
    if (!data) return null;
    const chapterMap = data[String(book || '')];
    if (!chapterMap) return null;
    return chapterMap[String(parseInt(chapter, 10) || 0)] || null;
  }

  function buildBooksUrl() {
    return runtimeState.mode === 'static' ? buildUrl('./data/books.json') : buildUrl('./api/books');
  }

  function buildBooksChaptersUrl() {
    return runtimeState.mode === 'static' ? buildUrl('./data/books-chapters.json') : buildUrl('./api/books/chapters');
  }

  function buildCapabilitiesUrl() {
    return runtimeState.mode === 'static' ? buildUrl('./data/capabilities.json') : buildUrl('./api/tf/status');
  }

  function buildTreeUrl(params) {
    const book = String(params.book || '');
    const chapter = parseInt(params.chapter, 10) || 0;
    const source = String(params.source || '');
    const lite = !!params.lite;
    const maxDepth = params.maxDepth;
    if (runtimeState.mode === 'static') {
      const suffix = lite ? 'lite' : 'full';
      return buildUrl(`./data/tree/${encodeURIComponent(source)}/${encodeURIComponent(book)}/${chapter}-${suffix}.json`);
    }
    const url = new URL('./api/tree', document.baseURI);
    url.searchParams.set('book', book);
    url.searchParams.set('chapter', String(chapter));
    if (source) url.searchParams.set('source', source);
    url.searchParams.set('lite', lite ? '1' : '0');
    if (typeof maxDepth === 'number' && maxDepth >= 0) url.searchParams.set('max_depth', String(maxDepth));
    return url.toString();
  }

  function buildVersionChapterUrl(params) {
    const version = String(params.version || '');
    const book = String(params.book || '');
    const chapter = parseInt(params.chapter, 10) || 0;
    if (runtimeState.mode === 'static') {
      return buildUrl(`./data/versions/${encodeURIComponent(version)}/${encodeURIComponent(book)}/${chapter}.json`);
    }
    const url = new URL('./api/versions/chapter', document.baseURI);
    url.searchParams.set('version', version);
    url.searchParams.set('book', book);
    url.searchParams.set('chapter', String(chapter));
    return url.toString();
  }

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error('fetch failed');
    return res.json();
  }

  window.CTTDataClient = {
    detectRuntime,
    runtimeMode,
    manifest,
    buildBooksUrl,
    buildBooksChaptersUrl,
    buildCapabilitiesUrl,
    buildTreeUrl,
    buildVersionChapterUrl,
    fetchJson,
    getAvailability: availabilityFor,
  };
})();
