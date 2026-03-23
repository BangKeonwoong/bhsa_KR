(function () {
  const state = {
    data: null,
    collapsed: new Set(),
    orientation: 'horizontal',
    showGloss: false,
    depthLimit: 0,
    tidyZoom: null, // {k,x,y}
    baseTranslate: { x: 40, y: 0 },
    highlightCats: new Set(),
    selectedId: null,
    selectedVerse: null,
    anchorMode: 'center',
    fitDoneFor: new Set(),
    lastHoverVerse: null,
    runtime: { mode: 'server', manifest: null },
    versionChapterCache: new Map(),
    literalIndex: null,
    literalIndexPromise: null,
  };
  const elBook = document.getElementById('book');
  const elChapter = document.getElementById('chapter');
  const elLoad = document.getElementById('loadBtn');
  const btnPrevBook = document.getElementById('prevBookBtn');
  const btnNextBook = document.getElementById('nextBookBtn');
  const btnPrevChap = document.getElementById('prevChapterBtn');
  const btnNextChap = document.getElementById('nextChapterBtn');
  const btnTidy = document.getElementById('viewTidy');
  const btnList = document.getElementById('viewList');
  const selOrient = document.getElementById('orientation');
  const selAnchorMode = document.getElementById('anchorMode');
  const selSource = document.getElementById('sourceSel');
  const chkGloss = document.getElementById('toggleGloss');
  const chkGlossKo = document.getElementById('toggleGlossKo');
  const chkLegend = document.getElementById('toggleLegend');
  const chkDetails = document.getElementById('toggleDetails');
  const tidyView = document.getElementById('tidyView');
  const listView = document.getElementById('listView');
  const tidyContainer = document.getElementById('tidyContainer');
  const listContainer = document.getElementById('listContainer');
  const detailsPanel = document.getElementById('detailsPanel');
  const detailsResizer = document.getElementById('detailsResizer');
  const legendPanel = document.getElementById('legendPanel');
  // Versions side panel elements
  const btnVersions = document.getElementById('toggleVersions');
  const versionsPanel = document.getElementById('versionsPanel');
  const selVersion = document.getElementById('versionSelect');
  const versionContent = document.getElementById('versionContent');
  const btnCloseVersions = document.getElementById('closeVersions');
  const vpRef = document.getElementById('vpRef');
  const depthRange = document.getElementById('depthRange');
  const depthValue = document.getElementById('depthValue');
  const spacingRange = document.getElementById('spacingRange');
  const spacingValue = document.getElementById('spacingValue');
  const elLoadStatus = document.getElementById('loadStatus');
  const spinOverlay = document.getElementById('spinnerOverlay');
  const toastEl = document.getElementById('toast');
  const themeSelect = document.getElementById('themeSelect');
  const dataClient = window.CTTDataClient || null;
  const LITERAL_BOOK_OVERRIDES = {
    'song of songs': 'Song_of_songs',
  };

  // --- Local storage helpers ---
  const LS_PREFIX = 'cttViewer:';
  function setPref(k, v){ try { localStorage.setItem(LS_PREFIX + k, String(v)); } catch(e){} }
  function getPref(k, defVal){ try { const v = localStorage.getItem(LS_PREFIX + k); return (v===null||v===undefined)? defVal : v; } catch(e){ return defVal; } }

  // Spinner + Toast
  let _loadCount = 0;
  function showSpinner(){ try { _loadCount++; if (spinOverlay) spinOverlay.classList.add('visible'); } catch(e){} }
  function hideSpinner(){ try { _loadCount=Math.max(0,_loadCount-1); if (_loadCount===0 && spinOverlay) spinOverlay.classList.remove('visible'); } catch(e){} }
  function showToast(msg, level){
    if (!toastEl) return;
    toastEl.textContent = String(msg||'');
    toastEl.className = 'show ' + (level||'');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(()=>{ toastEl.className=''; }, 2400);
  }

  // --- URL state helpers (deeplink) ---
  function getCurrentView(){ return tidyView.classList.contains('visible') ? 'tidy' : 'list'; }
  function readQueryState(){
    const u = new URL(window.location.href);
    const p = u.searchParams;
    const q = {};
    if (p.get('book')) q.book = p.get('book');
    if (p.get('chapter')) q.chapter = parseInt(p.get('chapter'), 10) || undefined;
    if (p.get('source')) q.source = p.get('source');
    if (p.get('view')) q.view = p.get('view');
    if (p.get('orientation')) q.orientation = p.get('orientation');
    return q;
  }
  function updateUrlFromState(push){
    try {
      const u = new URL(window.location.href);
      const params = u.searchParams;
      const book = elBook && elBook.value || '';
      const ch = elChapter && (elChapter.value || '');
      const src = selSource && selSource.value ? selSource.value : '';
      const view = getCurrentView();
      const ori = selOrient && selOrient.value || 'horizontal';
      params.set('book', book || 'genesis');
      if (ch) params.set('chapter', String(ch)); else params.delete('chapter');
      if (src) params.set('source', src); else params.delete('source');
      if (view && view !== 'tidy') params.set('view', view); else params.delete('view');
      if (ori && ori !== 'horizontal') params.set('orientation', ori); else params.delete('orientation');
      u.search = params.toString();
      if (push) window.history.pushState({}, '', u.toString());
      else window.history.replaceState({}, '', u.toString());
    } catch(e) { /* ignore */ }
  }
  function applyInitialStateFromQuery(){
    try {
      const q = readQueryState();
      if (q.book){
        const opt = Array.from(elBook.options).find(o => (o.value||'').toLowerCase() === String(q.book).toLowerCase());
        if (opt) elBook.value = opt.value;
      }
      if (q.chapter && q.chapter > 0){ elChapter.value = String(q.chapter); }
      try { updateChapterMaxForBook(elBook.value); } catch(e){}
      if (selSource && q.source){ selSource.value = q.source; }
      if (selOrient && q.orientation){ selOrient.value = q.orientation; }
      if (q.view === 'list'){ switchView('list'); } else { switchView('tidy'); }
    } catch(e) { /* ignore */ }
  }

  function applySavedPreferences(){
    try {
      const q = readQueryState();
      if (!q.book){
        const savedBook = getPref('book','');
        if (savedBook){
          const opt = Array.from(elBook.options).find(o => (o.value||'').toLowerCase() === String(savedBook).toLowerCase());
          if (opt) elBook.value = opt.value;
        }
      }
      if (!q.chapter){
        const savedCh = parseInt(getPref('chapter','')||'0',10) || 0;
        if (savedCh>0) elChapter.value = String(savedCh);
      }
      try { updateChapterMaxForBook(elBook.value); } catch(e){}
      if (!q.source && selSource){ selSource.value = getPref('source','tf'); }
      if (!q.orientation && selOrient){ selOrient.value = getPref('orientation','horizontal'); }
      if (selAnchorMode){ selAnchorMode.value = getPref('anchor','selection') || 'selection'; state.anchorMode = selAnchorMode.value; }
      // toggles and sliders
      try { if (chkGloss) chkGloss.checked = (getPref('gloss','')==='1'); } catch(e){}
      try { if (chkGlossKo) chkGlossKo.checked = (getPref('glossKo','')==='1'); } catch(e){}
      try { if (chkLegend) { const v = getPref('legend','1'); chkLegend.checked = (v==='1'); legendPanel.classList.toggle('visible', chkLegend.checked); } } catch(e){}
      try { if (chkDetails) { const v = getPref('details','1'); chkDetails.checked = (v==='1'); detailsPanel.classList.toggle('visible', chkDetails.checked); if (detailsResizer) detailsResizer.classList.toggle('visible', chkDetails.checked); } } catch(e){}
      try { const sp = parseInt(getPref('spacing','')||'0',10); if (sp && spacingRange) { spacingRange.value = String(sp); spacingValue.textContent = String(sp); state.spacing = sp; } } catch(e){}
      try { const dp = parseInt(getPref('depth','')||''); if (!isNaN(dp) && depthRange) { depthRange.value = String(dp); depthValue.textContent = String(dp); state.depthLimit = dp; } } catch(e){}
    } catch(e){}
  }

  elLoad.addEventListener('click', loadData);
  // Auto-load on Book change
  if (elBook) elBook.addEventListener('change', () => {
    try {
      const bookVal = elBook.value;
      updateChapterMaxForBook(bookVal);
      // Always reset to chapter 1 on book change
      const ch = 1;
      setBookAndChapter(bookVal, ch);
    } catch(e){
      // Fallback: ensure at least load with chapter 1
      try { elChapter.value = '1'; } catch(_) {}
      loadData();
    }
  });
  // Auto-load on Chapter change and Enter key
  if (elChapter){
    elChapter.addEventListener('change', () => {
      try {
        const bookVal = elBook.value;
        let ch = parseInt(elChapter.value || '1', 10) || 1;
        const maxCh = getMaxChapterForBook(bookVal);
        if (ch < 1) ch = 1;
        if (maxCh && ch > maxCh) ch = maxCh;
        setBookAndChapter(bookVal, ch);
      } catch(e){ loadData(); }
    });
    elChapter.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter'){
        ev.preventDefault();
        try {
          const bookVal = elBook.value;
          let ch = parseInt(elChapter.value || '1', 10) || 1;
          const maxCh = getMaxChapterForBook(bookVal);
          if (ch < 1) ch = 1;
          if (maxCh && ch > maxCh) ch = maxCh;
          setBookAndChapter(bookVal, ch);
        } catch(e){ loadData(); }
      }
    });
  }
  if (btnPrevBook) btnPrevBook.addEventListener('click', () => { navigateBook(-1); });
  if (btnNextBook) btnNextBook.addEventListener('click', () => { navigateBook(1); });
  if (btnPrevChap) btnPrevChap.addEventListener('click', () => { navigateChapter(-1); });
  if (btnNextChap) btnNextChap.addEventListener('click', () => { navigateChapter(1); });
  btnTidy.addEventListener('click', () => { switchView('tidy'); updateUrlFromState(false); });
  btnList.addEventListener('click', () => { switchView('list'); updateUrlFromState(false); });
  selOrient.addEventListener('change', () => { state.orientation = selOrient.value; try { setPref('orientation', selOrient.value); } catch(e){} updateUrlFromState(false); renderTidy(); });
  if (selAnchorMode) selAnchorMode.addEventListener('change', () => { state.anchorMode = selAnchorMode.value || 'center'; try { setPref('anchor', state.anchorMode); } catch(e){} renderTidy(); });
  if (selSource) selSource.addEventListener('change', () => { try { setPref('source', selSource.value||''); } catch(e){} updateUrlFromState(false); loadData(); });
  window.addEventListener('popstate', () => { applyInitialStateFromQuery(); loadData(); });
  if (chkGloss) chkGloss.addEventListener('change', ()=> {
    state.showGloss = !!chkGloss.checked;
    // 토글 직후 gloss 데이터가 하나도 없으면(경량 모드 가정) 상세 포함으로 재요청
    if (state.showGloss && state.data && !hasAnyGloss(state.data)) {
      reloadWithDetails();
      return;
    }
    render();
  });
  if (chkGlossKo) chkGlossKo.addEventListener('change', ()=> {
    state.showGlossKo = !!chkGlossKo.checked;
    if (state.showGlossKo && state.data && !hasAnyGloss(state.data)) {
      reloadWithDetails();
      return;
    }
    render();
  });
  if (chkLegend) chkLegend.addEventListener('change', ()=> {
    const on = !!chkLegend.checked;
    state.showLegend = on;
    if (legendPanel) { legendPanel.classList.toggle('visible', on); if (on) renderLegendCats(); }
  });
  if (chkDetails) chkDetails.addEventListener('change', ()=> {
    const on = !!chkDetails.checked; state.showDetails = on;
    if (detailsPanel){ detailsPanel.classList.toggle('visible', on); if (!on) detailsPanel.innerHTML=''; }
    if (detailsResizer){ detailsResizer.classList.toggle('visible', on); }
    // 초기 높이 기록(토글로 보이게 될 때 한 번 저장)
    try {
      if (on && detailsPanel){
        const h = detailsPanel.getBoundingClientRect().height;
        if (!state.detailsInitHeightPx || state.detailsInitHeightPx <= 0){
          state.detailsInitHeightPx = Math.max(120, Math.floor(h || window.innerHeight * 0.28));
        }
      }
    } catch(e) { /* ignore */ }
    render();
  });
  // Versions toggle + controls
  // Versions panel open/close helpers with focus + aria
  let _prevFocus = null;
  function openVersionsPanel(){
    if (!versionsPanel) return;
    versionsPanel.classList.add('visible');
    versionsPanel.setAttribute('aria-hidden','false');
    if (btnVersions) btnVersions.setAttribute('aria-expanded','true');
    try { _prevFocus = document.activeElement; } catch(e){ _prevFocus = null; }
    // prefer saved selection
    try { const saved = getPref('versionPanel:selected',''); if (selVersion && saved) selVersion.value = saved; } catch(e){}
    refreshVersionsPanel().then(()=>{
      // focus first interactive element in panel
      try {
        if (selVersion) { selVersion.focus(); return; }
        const first = versionsPanel.querySelector('.verse-item');
        if (first) first.focus();
      } catch(e){}
    }).catch(()=>{});
  }
  function closeVersionsPanel(){
    if (!versionsPanel) return;
    versionsPanel.classList.remove('visible');
    versionsPanel.setAttribute('aria-hidden','true');
    if (btnVersions) btnVersions.setAttribute('aria-expanded','false');
    clearVerseHover();
    try { if (_prevFocus && _prevFocus.focus) _prevFocus.focus(); } catch(e){}
  }
  // Toggle button
  if (btnVersions) btnVersions.addEventListener('click', ()=> {
    const open = !(versionsPanel && versionsPanel.classList.contains('visible'));
    if (open) { try { setPref('versionPanel:open','1'); } catch(e){} openVersionsPanel(); }
    else { try { setPref('versionPanel:open','0'); } catch(e){} closeVersionsPanel(); }
  });
  if (btnCloseVersions) btnCloseVersions.addEventListener('click', ()=> { try { setPref('versionPanel:open','0'); } catch(e){} closeVersionsPanel(); });
  // Escape to close + focus trap within panel
  document.addEventListener('keydown', (ev) => {
    try {
      if (!versionsPanel || !versionsPanel.classList.contains('visible')) return;
      if (ev.key === 'Escape') { ev.preventDefault(); closeVersionsPanel(); return; }
      if (ev.key !== 'Tab') return;
      // focus trap
      const focusables = versionsPanel.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusables || !focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const cur = document.activeElement;
      if (ev.shiftKey) {
        if (cur === first) { ev.preventDefault(); last.focus(); }
      } else {
        if (cur === last) { ev.preventDefault(); first.focus(); }
      }
    } catch(e){}
  });
  if (selVersion) selVersion.addEventListener('change', ()=> { refreshVersionsPanel(); try { setPref('versionPanel:selected', selVersion.value||''); } catch(e){} });
  window.addEventListener('resize', () => {
    if (tidyView.classList.contains('visible')) renderTidy();
  });
  // Spacebar centers the tidy tree on the root
  document.addEventListener('keydown', (ev) => {
    try {
      if (ev.code !== 'Space' && ev.key !== ' ') return;
      if (!tidyView.classList.contains('visible')) return;
      ev.preventDefault();
      // compute desired translate so that root (0,0 in zoom-layer) sits at svg center
      const svg = tidyContainer.querySelector('svg');
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const cx = Math.max(0, rect.width / 2);
      const cy = Math.max(0, rect.height / 2);
      const base = state.baseTranslate || { x: 0, y: 0 };
      const k = (state.tidyZoom && typeof state.tidyZoom.k === 'number') ? state.tidyZoom.k : 1;
      const tx = cx - base.x;
      const ty = cy - base.y;
      // Use d3 zoom behavior attached to svg so drag state stays in sync
      try {
        const t = d3.zoomIdentity.translate(tx, ty).scale(k);
        if (state.tidyZoomBehavior && state.tidySvg){
          d3.select(state.tidySvg).call(state.tidyZoomBehavior.transform, t);
        } else {
          d3.select(svg).call(d3.zoom().transform, t);
        }
      } catch (e) {
        // fallback direct transform if zoom behavior missing
        const gZoom = tidyContainer.querySelector('g.zoom-layer');
        if (gZoom) gZoom.setAttribute('transform', `translate(${tx},${ty}) scale(${k})`);
      }
      state.tidyZoom = { x: tx, y: ty, k };
    } catch(e){ /* ignore */ }
  });
  if (depthRange) depthRange.addEventListener('input', () => {
    const v = parseInt(depthRange.value || '2', 10);
    state.depthLimit = isNaN(v) ? 2 : v;
    if (depthValue) depthValue.textContent = String(state.depthLimit);
    recomputeCollapsedToDepth();
    renderTidy();
    try { setPref('depth', state.depthLimit|0); } catch(e){}
  });
  if (spacingRange) spacingRange.addEventListener('input', () => {
    const v = parseInt(spacingRange.value || '280', 10);
    state.spacing = isNaN(v) ? 280 : v;
    if (spacingValue) spacingValue.textContent = String(state.spacing);
    renderTidy();
    try { setPref('spacing', state.spacing|0); } catch(e){}
  });

  // Load books dynamically if available, then data
  // simple in-memory API cache keyed by URL (ETag-aware)
  state.apiCache = new Map();
  // cache for phrase segmentation per node id
  state.tidySegCache = new Map();
  const API_CACHE_TTL_MS = 30000; // 30s default
  const API_CACHE_MAX = 100; // simple LRU max size
  function ensureFirstRunDefaults(){
    try {
      const flag = getPref('firstRun','');
      if (!flag){
        setPref('source','tf');
        setPref('anchor','selection');
        setPref('legend','1');
        setPref('details','1');
        setPref('firstRun','1');
      }
    } catch(e){}
  }
  initBooks().then(() => { ensureFirstRunDefaults(); applyInitialStateFromQuery(); applySavedPreferences(); updateUrlFromState(false); }).then(initTfStatus).then(loadData).catch(loadData);
  // Restore versions panel open state
  try {
    const wantOpen = getPref('versionPanel:open','');
    if (String(wantOpen) === '1') {
      setTimeout(() => { try { openVersionsPanel(); } catch(e){} }, 0);
    }
  } catch(e){}
  // Init theme select if Theme helper is available
  try { if (window.Theme && themeSelect) window.Theme.init('themeSelect'); } catch(e){}

  async function fetchJsonCached(url){
    const now = Date.now();
    const entry = state.apiCache.get(url);
    if (entry && (now - entry.time) < API_CACHE_TTL_MS){
      // fresh
      return { json: entry.data, etag: entry.etag, fromCache: true };
    }
    const headers = {};
    if (entry && entry.etag){ headers['If-None-Match'] = entry.etag; }
    let res;
    try {
      res = await fetch(url, { headers });
    } catch(e){
      if (entry) return { json: entry.data, etag: entry.etag, fromCache: true };
      throw e;
    }
    if (res.status === 304 && entry){ entry.time = now; return { json: entry.data, etag: entry.etag, fromCache: true }; }
    if (!res.ok){
      if (entry) return { json: entry.data, etag: entry.etag, fromCache: true };
      throw new Error('fetch failed');
    }
    const etag = res.headers.get('ETag') || null;
    const json = await res.json();
    if (etag){
      state.apiCache.set(url, { etag, data: json, time: now });
      // prune simple LRU
      if (state.apiCache.size > API_CACHE_MAX){
        let oldestKey = null, oldestTime = Infinity;
        for (const [k,v] of state.apiCache.entries()){
          if (v.time < oldestTime){ oldestTime = v.time; oldestKey = k; }
        }
        if (oldestKey) state.apiCache.delete(oldestKey);
      }
    }
    return { json, etag, fromCache: false };
  }

  function sleep(ms){
    return new Promise(resolve => window.setTimeout(resolve, ms));
  }

  function tfStatusUrl(requireDetails){
    const url = new URL('./api/tf/status', document.baseURI);
    if (requireDetails) url.searchParams.set('details', '1');
    return url.toString();
  }

  function setLoadStatus(message, className, actions){
    if (!elLoadStatus) return;
    const html = [`<span>${escapeHtml(message || '')}</span>`];
    if (Array.isArray(actions) && actions.length){
      html.push(actions.map((action, idx) => (
        `<button type="button" class="status-action" data-status-action="${idx}">${escapeHtml(action.label || '')}</button>`
      )).join(' '));
    }
    elLoadStatus.innerHTML = html.join(' ');
    elLoadStatus.className = className || 'status';
    if (Array.isArray(actions) && actions.length){
      elLoadStatus.querySelectorAll('[data-status-action]').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.getAttribute('data-status-action') || '-1', 10);
          const action = actions[idx];
          if (action && typeof action.onClick === 'function'){
            try { action.onClick(); } catch(e) { /* ignore */ }
          }
        });
      });
    }
  }

  function renderTfStatusBadge(st){
    const el = document.getElementById('glossStatus');
    if (!el) return;
    if (!st || !st.has_local_bhsa){
      el.textContent = 'TF 미탑재: gloss 제한';
      el.className = 'status warn';
      return;
    }
    if (st.phase === 'error'){
      el.textContent = 'TF 준비 실패';
      el.className = 'status err';
      return;
    }
    if (!st.ready){
      el.textContent = st.message || 'TF 초기화 중';
      el.className = 'status warn';
      return;
    }
    if (!st.has_gloss){
      el.textContent = 'TF gloss 없음: 영어/한글 gloss 제한';
      el.className = 'status warn';
      return;
    }
    el.textContent = 'TF gloss 사용 가능';
    el.className = 'status ok';
  }

  async function fetchTfStatus(requireDetails){
    if (state.runtime && state.runtime.mode === 'static'){
      const st = dataClient ? await dataClient.fetchJson(dataClient.buildCapabilitiesUrl()) : null;
      const staticStatus = Object.assign({
        ready: true,
        warming: false,
        details_ready: true,
        phase: 'ready',
        message: '정적 데이터 사용 중',
        last_error: null,
      }, st || {});
      renderTfStatusBadge(staticStatus);
      return staticStatus;
    }
    const res = await fetch(tfStatusUrl(!!requireDetails), { cache: 'no-store' });
    const st = await res.json();
    renderTfStatusBadge(st);
    return st;
  }

  function makeCttFallbackAction(){
    return {
      label: 'CTT 보기',
      onClick: () => {
        try {
          if (selSource) selSource.value = 'ctt';
          setPref('source', 'ctt');
          updateUrlFromState(false);
        } catch(e) { /* ignore */ }
        loadData();
      },
    };
  }

  function renderTfWaitStatus(st, requireDetails){
    const message = (st && st.message)
      || (requireDetails ? 'gloss/상세 데이터 준비 중' : '히브리 원문 feature 로딩 중');
    const actions = [{ label: '다시 확인', onClick: () => { loadData(); } }];
    const fallbackCandidates = preferredTreeSources(elBook.value || 'genesis', elChapter.value || 1);
    if (Array.isArray(fallbackCandidates) && fallbackCandidates.includes('ctt')){
      actions.push(makeCttFallbackAction());
    }
    setLoadStatus(
      `TF 데이터를 초기화하는 중입니다. 첫 실행은 오래 걸릴 수 있습니다. ${message}`,
      'status warn',
      actions
    );
  }

  async function waitForTfReady(requireDetails){
    let st = null;
    try {
      st = await fetchTfStatus(requireDetails);
    } catch (e) {
      setLoadStatus('TF 상태를 확인하지 못했습니다. 다시 시도해 주세요.', 'status err', [
        { label: '다시 시도', onClick: () => { loadData(); } },
      ]);
      return false;
    }
    if (!st || !st.has_local_bhsa) return false;
    if (st.ready) return true;
    renderTfWaitStatus(st, requireDetails);
    const deadline = Date.now() + 120000;
    while (Date.now() < deadline){
      await sleep(1200);
      st = await fetchTfStatus(requireDetails).catch(() => null);
      if (st && st.ready) return true;
      if (st && st.phase === 'error'){
        setLoadStatus(st.message || 'TF 준비 실패', 'status err', [
          { label: '다시 시도', onClick: () => { loadData(); } },
          makeCttFallbackAction(),
        ]);
        return false;
      }
      renderTfWaitStatus(st, requireDetails);
    }
    setLoadStatus(
      'TF 초기화가 예상보다 오래 걸리고 있습니다. 잠시 후 다시 시도하거나 CTT 보기로 전환할 수 있습니다.',
      'status warn',
      [
        { label: '다시 시도', onClick: () => { loadData(); } },
        makeCttFallbackAction(),
      ]
    );
    return false;
  }

  async function initTfStatus(){
    try {
      await fetchTfStatus(false);
    } catch (e) { /* no-op */ }
  }

  async function initBooks() {
    try {
      const runtime = dataClient ? await dataClient.detectRuntime() : { mode: 'server', manifest: null };
      state.runtime = runtime || { mode: 'server', manifest: null };
      const books = (runtime && runtime.mode === 'static' && runtime.manifest && Array.isArray(runtime.manifest.books))
        ? runtime.manifest.books.map(b => ({ book: b.book, code: b.label, name: b.name, chapters: b.chapters }))
        : (dataClient ? await dataClient.fetchJson(dataClient.buildBooksUrl()) : []);
      if (!Array.isArray(books) || !books.length) return;
      state.books = books;
      elBook.innerHTML = '';
      for (const b of books) {
        const opt = document.createElement('option');
        opt.value = (b.book || b.name || '').toLowerCase();
        opt.textContent = b.name || '';
        elBook.appendChild(opt);
      }
      try { state.booksOrder = Array.from(elBook.options).map(o => String(o.value)); } catch(e) { state.booksOrder = null; }
      const gen = Array.from(elBook.options).find(o => (o.textContent || '').toLowerCase() === 'genesis');
      if (gen) elBook.value = gen.value;
      const list = (runtime && runtime.mode === 'static' && runtime.manifest && Array.isArray(runtime.manifest.books))
        ? runtime.manifest.books.map(b => ({ book: b.book, code: b.label, name: b.name, chapters: b.chapters }))
        : (dataClient ? await dataClient.fetchJson(dataClient.buildBooksChaptersUrl()) : []);
      const map = {};
      if (Array.isArray(list)){
        for (const it of list){
          const nm = String(it && (it.book || it.name || '')).toLowerCase();
          const ch = (it && typeof it.chapters === 'number') ? Math.max(0, it.chapters|0) : 0;
          if (nm) map[nm] = ch;
        }
      }
      state.bookChapters = map;
      try { updateChapterMaxForBook(elBook.value); } catch(e){}
      try { syncSourceOptions(elBook.value, elChapter.value || 1); syncVersionOptions(elBook.value, elChapter.value || 1); } catch(e){}
    } catch (e) { /* ignore */ }
  }

  // ---------- Book/Chapter navigation ----------
  function getBookIndex(val){
    const order = state.booksOrder || Array.from(elBook.options).map(o => String(o.value));
    return order.findIndex(v => v === val);
  }
  function bookValueAt(idx){
    const order = state.booksOrder || Array.from(elBook.options).map(o => String(o.value));
    if (idx < 0 || idx >= order.length) return null; return order[idx];
  }
  function wrapIndex(idx, len){ if (!len) return 0; return ((idx % len) + len) % len; }
  function setBookAndChapter(bookVal, chap){
    if (bookVal) elBook.value = bookVal;
    if (chap) elChapter.value = String(chap);
    try { updateChapterMaxForBook(elBook.value); } catch(e){}
    try { syncSourceOptions(elBook.value, elChapter.value || 1); syncVersionOptions(elBook.value, elChapter.value || 1); } catch(e){}
    try { setPref('book', elBook.value||''); setPref('chapter', elChapter.value||''); } catch(e){}
    updateUrlFromState(false);
    loadData();
  }
  function getMaxChapterForBook(bookVal){
    const nm = (bookVal || '').toLowerCase();
    const m = state.bookChapters || {};
    const v = m[nm];
    if (typeof v === 'number' && v > 0) return v;
    return null;
  }
  function updateChapterMaxForBook(bookVal){
    const maxCh = getMaxChapterForBook(bookVal);
    if (maxCh && elChapter){ elChapter.max = String(maxCh); }
  }
  function getChapterAvailability(bookVal, chap){
    try {
      if (!dataClient || !state.runtime || state.runtime.mode !== 'static') return null;
      return dataClient.getAvailability(String(bookVal || '').toLowerCase(), chap);
    } catch(e){ return null; }
  }
  function syncSourceOptions(bookVal, chap){
    if (!selSource) return;
    const availability = getChapterAvailability(bookVal, chap);
    const supported = availability && Array.isArray(availability.tree) ? new Set(availability.tree) : null;
    Array.from(selSource.options).forEach(opt => {
      if (!opt.value) { opt.disabled = false; return; }
      opt.disabled = !!(supported && !supported.has(opt.value));
    });
    if (selSource.value && selSource.options[selSource.selectedIndex] && selSource.options[selSource.selectedIndex].disabled){
      selSource.value = '';
    }
  }
  function syncVersionOptions(bookVal, chap){
    if (!selVersion) return;
    const availability = getChapterAvailability(bookVal, chap);
    const supported = availability && Array.isArray(availability.versions) ? new Set(availability.versions) : null;
    let firstEnabled = null;
    Array.from(selVersion.options).forEach(opt => {
      opt.disabled = !!(supported && !supported.has(opt.value));
      if (!opt.disabled && firstEnabled === null) firstEnabled = opt.value;
    });
    if (selVersion.value && selVersion.options[selVersion.selectedIndex] && selVersion.options[selVersion.selectedIndex].disabled){
      selVersion.value = firstEnabled || 'knt';
    }
  }
  function preferredTreeSources(bookVal, chap){
    const sourcePref = selSource ? (selSource.value || '') : '';
    const availability = getChapterAvailability(bookVal, chap);
    if (availability && Array.isArray(availability.tree)){
      if (sourcePref && availability.tree.includes(sourcePref)) return [sourcePref];
      if (availability.tree.includes('tf')) return ['tf'];
      if (availability.tree.includes('ctt')) return ['ctt'];
      return [];
    }
    if (sourcePref === 'tf') return ['tf'];
    if (sourcePref === 'ctt') return ['ctt'];
    return ['tf', 'ctt'];
  }
  async function candidateHasData(bookVal, chap){
    try {
      const availability = getChapterAvailability(bookVal, chap);
      if (availability) return Array.isArray(availability.tree) && availability.tree.length > 0;
      const url1 = dataClient.buildTreeUrl({ book: bookVal, chapter: chap, lite: true });
      const r1 = await fetchJsonCached(url1).catch(()=>null);
      const j1 = r1 && r1.json;
      if (j1 && Array.isArray(j1.children) && j1.children.length) return true;
      if (j1 && j1.error) return false;
      const url2 = dataClient.buildTreeUrl({ book: bookVal, chapter: chap, source: 'ctt', lite: true });
      const r2 = await fetchJsonCached(url2).catch(()=>null);
      const j2 = r2 && r2.json;
      return !!(j2 && Array.isArray(j2.children) && j2.children.length);
    } catch(e) { return false; }
  }
  async function navigateChapter(dir){
    try {
      const bookVal = elBook.value;
      const ch0 = parseInt(elChapter.value || '1', 10) || 1;
      const step = dir >= 0 ? 1 : -1;
      const maxCh = getMaxChapterForBook(bookVal);
      let candidate = ch0 + step;
      if (maxCh){
        if (candidate < 1){
          // go to previous book, last chapter available
          await navigateBook(-1, true);
          return;
        }
        if (candidate > maxCh){
          // go to next book, first chapter
          await navigateBook(1, true);
          return;
        }
        // within range; attempt direct
        if (await candidateHasData(bookVal, candidate)) { setBookAndChapter(bookVal, candidate); return; }
        // fallback scan within range
        if (dir >= 0){ for (let c=candidate+1;c<=maxCh;c++){ if (await candidateHasData(bookVal, c)) { setBookAndChapter(bookVal, c); return; } } }
        else { for (let c=candidate-1;c>=1;c--){ if (await candidateHasData(bookVal, c)) { setBookAndChapter(bookVal, c); return; } } }
        // no hit → neighbor book
        await navigateBook(dir, true);
      } else {
        // no known max → legacy scan bounded
        const MAX_SCAN = 200; let c = candidate; for (let i=0;i<MAX_SCAN;i++, c+=step){ if (c <= 0) break; if (await candidateHasData(bookVal, c)) { setBookAndChapter(bookVal, c); return; } }
        await navigateBook(dir, true);
      }
    } catch(e) { /* ignore */ }
  }
  async function navigateBook(dir, fromChapterNav=false){
    try {
      const order = state.booksOrder || Array.from(elBook.options).map(o => String(o.value));
      if (!order || !order.length) return;
      const cur = elBook.value;
      const idx = getBookIndex(cur);
      if (idx < 0) return;
      const nextIdx = wrapIndex(idx + (dir>=0?1:-1), order.length);
      const target = bookValueAt(nextIdx);
      if (!target) return;
      // choose chapter based on known max
      const maxCh = getMaxChapterForBook(target);
      if (dir >= 0){
        const start = 1; const end = maxCh || 200;
        for (let c=start;c<=end;c++){ if (await candidateHasData(target, c)) { setBookAndChapter(target, c); return; } }
        setBookAndChapter(target, start);
      } else {
        const end = maxCh || 200; const start = 1;
        for (let c=end;c>=start;c--){ if (await candidateHasData(target, c)) { setBookAndChapter(target, c); return; } }
        setBookAndChapter(target, end);
      }
    } catch(e) { /* ignore */ }
  }

  function renderLegendCats(){
    if (!legendPanel) return;
    const items = [
      { key: 'cat-verb', label: '동사절' },
      { key: 'cat-weq',  label: '연접/연속절' },
      { key: 'cat-part', label: '분사절' },
      { key: 'cat-inf',  label: '부정사절' },
      { key: 'cat-imv',  label: '명령/원망/기원절' },
      { key: 'cat-noun', label: '명사절' },
      { key: 'cat-adj',  label: '형용사절' },
      { key: 'cat-rel',  label: '관계/수식절' },
      { key: 'cat-pp',   label: '전치사절' },
      { key: 'cat-verbless', label: '무서술절' },
      { key: 'cat-intj', label: '감탄절' },
      { key: 'cat-other',label: '기타' },
    ];
    const html = [
      '<h4>절 유형 안내</h4>',
      ...items.map(it => {
        const checked = state.highlightCats && state.highlightCats.has(it.key) ? 'checked' : '';
        return `<label class="legend-row"><input type="checkbox" data-cat="${it.key}" ${checked}/> <span class="swatch ${it.key}"></span><span>${it.label}</span></label>`;
      })
    ].join('');
    legendPanel.innerHTML = html;
    legendPanel.querySelectorAll('input[type="checkbox"]').forEach(inp => {
      inp.addEventListener('change', () => {
        const cat = inp.getAttribute('data-cat');
        if (!cat) return;
        if (!state.highlightCats) state.highlightCats = new Set();
        if (inp.checked) state.highlightCats.add(cat); else state.highlightCats.delete(cat);
        render();
      });
    });
  }

  async function loadData() {
    const book = elBook.value || 'genesis';
    const chapter = elChapter.value || 1;
    let sources = preferredTreeSources(book, chapter);
    const startTs = performance.now();
    setLoadStatus('불러오는 중…', 'status');
    showSpinner();
    if (sources[0] === 'tf' && (!state.runtime || state.runtime.mode !== 'static')){
      const tfStatus = await fetchTfStatus(false).catch(() => null);
      if (tfStatus && !tfStatus.has_local_bhsa){
        sources = sources.filter(source => source !== 'tf');
      } else if (tfStatus && !tfStatus.ready){
        const ready = await waitForTfReady(false);
        if (!ready){
          hideSpinner();
          return;
        }
      }
    }
    let r1 = null;
    try {
      for (const source of sources){
        const url = dataClient.buildTreeUrl({ book, chapter, source, lite: true });
        r1 = await fetchJsonCached(url).catch(()=>null);
        const json = r1 && r1.json;
        if (json && !json.error) break;
      }
    } catch(e){ /* handled below */ }
    if (!r1 || !r1.json || r1.json.error){
      setLoadStatus('로드 실패', 'status err');
      showToast('데이터 로드 실패', 'err');
      hideSpinner();
      return;
    }
    state.data = r1.json;
    state.source = (state.data && state.data.source) ? state.data.source : (sources[0] || 'tf');
    try { syncSourceOptions(book, chapter); syncVersionOptions(book, chapter); } catch(e){}
    state.collapsed.clear();
    // 깊이 슬라이더 최대값/초기값 설정 (트리 높이 기반)
    try {
      const h = treeHeight(state.data);
      if (depthRange) {
        depthRange.max = String(Math.max(0, h));
        if (state.depthLimit > h) state.depthLimit = Math.min(state.depthLimit, h);
        depthRange.value = String(state.depthLimit);
      }
      if (depthValue) depthValue.textContent = String(state.depthLimit);
      recomputeCollapsedToDepth();
    } catch(e) { /* ignore */ }
    render();
    const ms = Math.max(0, performance.now() - startTs).toFixed(0);
    const src = state.source ? state.source.toUpperCase() : '';
    setLoadStatus(`${src} ${ms}ms`, 'status ok');
    showToast('불러오기 완료', 'ok');
    hideSpinner();
    // Ensure resizer visibility matches panel state on first load
    if (detailsResizer){ detailsResizer.classList.toggle('visible', !!state.showDetails); }
    // If versions panel is open, sync its content with current book/chapter
    try { await refreshVersionsPanel(); } catch(e){}
  }

  function hasAnyGloss(root){
    let found = false;
    (function walk(n){ if(!n||found) return; if (n.gloss || n.gloss_ko) { found = true; return; }
      const kids = (n.children||[]); for(const c of kids) walk(c);
    })(root);
    return found;
  }

  function findNodeById(root, targetId){
    let found = null;
    (function walk(node){
      if (!node || found) return;
      if (String(node.id) === String(targetId)) { found = node; return; }
      const kids = node.children || [];
      for (const child of kids) walk(child);
    })(root);
    return found;
  }

  async function reloadWithDetails(selectedId){
    try{
      const book = elBook.value || 'genesis';
      const chapter = elChapter.value || 1;
      const sources = preferredTreeSources(book, chapter);
      if ((sources[0] || state.source) === 'tf' && (!state.runtime || state.runtime.mode !== 'static')){
        const ready = await waitForTfReady(true);
        if (!ready) return;
      }
      const url = dataClient.buildTreeUrl({ book, chapter, source: sources[0] || state.source || 'tf', lite: false });
      showSpinner();
      const r = await fetchJsonCached(url);
      state.data = r.json;
      state.source = (state.data && state.data.source) ? state.data.source : state.source;
      render();
      if (selectedId !== undefined && selectedId !== null){
        const refreshed = findNodeById(state.data, selectedId);
        if (refreshed) showDetails(refreshed);
      }
    }catch(e){ render(); showToast('상세 불러오기 실패', 'err'); }
    finally { hideSpinner(); }
  }

  // ---- Versions panel support ----
  function bookLabelName(val){
    try { return (elBook.options[elBook.selectedIndex] || {}).textContent || val || ''; } catch(e){ return val || ''; }
  }
  // --- Hover helpers (unified) ---
  /**
   * Return NodeList of tidy tree clause nodes for a given verse number.
   * Nodes carry data-verse-num and data-has-ctype attributes.
   */
  function _treeClauseNodesByVerse(vnum){
    try { return tidyContainer.querySelectorAll(`g.tree-node[data-verse-num="${vnum}"][data-has-ctype="1"]`); } catch(e){ return []; }
  }
  /** Return NodeList of list-view items for a given verse number. */
  function _listClauseItemsByVerse(vnum){
    try { return listContainer.querySelectorAll(`li.node-item[data-verse-num="${vnum}"][data-has-ctype="1"]`); } catch(e){ return []; }
  }
  function _unhoverNodes(nodes){
    nodes.forEach(el => {
      try {
        el.classList.remove('hover-hi');
      } catch(e){}
    });
  }
  /** Remove hover highlight/scale for the specified verse across views. */
  function unhoverVerse(vnum){
    if (!vnum) return;
    try { _unhoverNodes(_treeClauseNodesByVerse(vnum)); } catch(e){}
    try { _listClauseItemsByVerse(vnum).forEach(el => el.classList.remove('hover-hi')); } catch(e){}
  }
  /** Clear any active verse hover (cached) and residual classes. */
  function clearVerseHover(){
    if (!tidyContainer) return;
    if (state.lastHoverVerse){ unhoverVerse(state.lastHoverVerse); state.lastHoverVerse = null; }
    // Best-effort cleanup in case of re-renders
    try {
      tidyContainer.querySelectorAll('g.tree-node.hover-hi').forEach(el => {
        el.classList.remove('hover-hi');
      });
      listContainer.querySelectorAll('li.node-item.hover-hi').forEach(el => el.classList.remove('hover-hi'));
    } catch(e){}
  }
  /** Apply hover highlight for a verse (tree/list highlight only). */
  function setVerseHover(vnum){
    if (!tidyContainer) return;
    try { vnum = parseInt(vnum, 10) || 0; } catch(e){ vnum = 0; }
    if (!vnum){ clearVerseHover(); return; }
    if (state.lastHoverVerse === vnum) return;
    if (state.lastHoverVerse){ unhoverVerse(state.lastHoverVerse); }
    const nodes = _treeClauseNodesByVerse(vnum);
    nodes.forEach(el => { try { el.classList.add('hover-hi'); } catch(e){} });
    try { _listClauseItemsByVerse(vnum).forEach(el => el.classList.add('hover-hi')); } catch(e){}
    state.lastHoverVerse = vnum;
  }
  function applyVerseHover(vnum){
    setVerseHover(vnum);
    setActiveVerseInPanel(vnum, false);
  }
  function syncSelectedVerseInPanel(doScroll){
    try {
      if (!versionContent) return;
      versionContent.querySelectorAll('.verse-item.selected').forEach(el => el.classList.remove('selected'));
      const vnum = parseInt(state.selectedVerse || '0', 10) || 0;
      if (!vnum) return;
      const el = versionContent.querySelector(`.verse-item[data-verse="${vnum}"]`);
      if (!el) return;
      el.classList.add('selected');
      if (doScroll){ try { el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch(e){} }
    } catch(e){}
  }
  /** Build unified versions API URL for fetch. */
  function versionsApiUrl(version, book, chapter){
    return dataClient.buildVersionChapterUrl({ version, book, chapter });
  }
  /** Render loading placeholder into versions panel. */
  function setVersionsPanelLoading(){ if (versionContent) versionContent.innerHTML = `<div class=\"empty\">불러오는 중…</div>`; }
  /** Render error + retry into versions panel. */
  function setVersionsPanelError(){
    if (!versionContent) return;
    versionContent.innerHTML = `<div class=\"empty\">역본을 불러오지 못했습니다. <button class=\"btn-retry\">다시 시도</button></div>`;
    try { const btn = versionContent.querySelector('.btn-retry'); if (btn) btn.addEventListener('click', ()=> refreshVersionsPanel()); } catch(_){}
  }
  /** Fetch verses for (version,book,chapter). Returns {verses:Array, ok:boolean}. */
  async function fetchVersionsChapter(version, book, chapter){
    const key = `${String(version||'').toLowerCase()}|${String(book||'').toLowerCase()}|${parseInt(chapter, 10) || 0}`;
    if (state.versionChapterCache.has(key)) return state.versionChapterCache.get(key);
    const r = await fetchJsonCached(versionsApiUrl(version, book, chapter));
    const j = r && r.json;
    const result = (!j || !Array.isArray(j.verses)) ? { verses: [], ok: false } : { verses: j.verses, ok: true };
    state.versionChapterCache.set(key, result);
    return result;
  }
  /** Load panel content by calling fetch helper and rendering or erroring. */
  async function loadVersionsPanel(version, book, chapter){
    try {
      if (!versionsPanel || !versionsPanel.classList.contains('visible')) return false;
      if (vpRef) vpRef.textContent = `${bookLabelName(book)} ${chapter}`;
      setVersionsPanelLoading();
      const { verses, ok } = await fetchVersionsChapter(version, book, chapter);
      if (!ok){ setVersionsPanelError(); return false; }
      renderVersionsContent(verses);
      return true;
    } catch(e){ setVersionsPanelError(); return false; }
  }
  async function refreshVersionsPanel(){
    try {
      if (!versionsPanel || !versionsPanel.classList.contains('visible')) return;
      const ver = ((selVersion && selVersion.value) || 'knt').toLowerCase();
      const book = elBook.value || 'genesis';
      const chapter = parseInt(elChapter.value || '1', 10) || 1;
      syncVersionOptions(book, chapter);
      await loadVersionsPanel(ver, book, chapter);
    } catch(e){ setVersionsPanelError(); }
  }
  function renderVersionsContent(verses){
    if (!versionContent) return;
    if (!verses || !verses.length){ versionContent.innerHTML = `<div class=\"empty\">이 장의 텍스트가 없습니다.</div>`; return; }
    const html = verses.map(v => {
      const num = v && typeof v.verse==='number' ? v.verse : null;
      const tx = (v && v.text) ? String(v.text) : '';
      const lab = num ? `절 ${num}` : '절';
      return `<div class=\"verse-item\" role=\"button\" tabindex=\"0\" aria-label=\"${lab}\" data-verse=\"${num||''}\"><span class=\"vnum\">${num||''}</span><div class=\"vtext\">${escapeHtml(tx)}</div></div>`;
    }).join('');
    versionContent.innerHTML = html;
    versionContent.querySelectorAll('.verse-item').forEach(el => {
      el.addEventListener('mouseenter', () => {
        const num = parseInt(el.getAttribute('data-verse')||'0',10)||0;
        if (num>0) applyVerseHover(num);
      });
      el.addEventListener('mouseleave', () => { clearVerseHover(); clearActiveVerseInPanel(); });
      el.addEventListener('click', () => {
        const num = parseInt(el.getAttribute('data-verse')||'0',10)||0;
        if (num>0) selectFirstClauseForVerse(num);
      });
      el.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          const num = parseInt(el.getAttribute('data-verse')||'0',10)||0;
          if (num>0) selectFirstClauseForVerse(num);
        }
      });
    });
    syncSelectedVerseInPanel(false);
    if (state.lastHoverVerse) setActiveVerseInPanel(state.lastHoverVerse, false);
  }

  function ensureDetailsVisible(){
    try {
      if (!detailsPanel) return;
      if (chkDetails){ chkDetails.checked = true; }
      state.showDetails = true;
      detailsPanel.classList.add('visible');
      if (detailsResizer) detailsResizer.classList.add('visible');
    } catch(e){}
  }
  // --- Verse utils ---
  /** Parse verse metadata from a BHSA-like ref string e.g. "GEN 01,03". */
  function parseVerseRef(vs){
    try {
      const m = /\b([0-9A-Z]{3})\s+(\d{2}),(\d{2})/.exec(String(vs||''));
      if (!m) return null;
      return {
        bookCode: m[1],
        chapter: parseInt(m[2], 10) || null,
        verse: parseInt(m[3], 10) || null,
      };
    } catch(e){ return null; }
  }
  /** Parse verse number (int) from a BHSA-like ref string e.g. "GEN 01,03". */
  function verseNumFromRef(vs){
    const ref = parseVerseRef(vs);
    return ref ? ref.verse : null;
  }
  /** Convenience wrapper: parse verse number from a node object. */
  function verseNumFromNode(n){ return verseNumFromRef(n && n.verse); }
  // Backward-compat name (to be phased out)
  function parseNodeVerseNum(vs){ return verseNumFromRef(vs); }
  function isClauseNode(n){ return !!(n && n.ctype); }
  function findFirstClauseNodeForVerse(vnum){
    let found = null;
    try {
      if (!state || !state.data) return null;
      walk(state.data, (n)=>{
        if (found) return;
        if (!n) return;
        const vn = verseNumFromNode(n);
        if (vn === vnum && isClauseNode(n)) found = n;
      });
    } catch(e){}
    return found;
  }
  function currentLiteralBookKey(){
    try {
      const label = String(bookLabelName(elBook && elBook.value) || '').trim();
      if (!label) return '';
      const aliases = (state.literalIndex && state.literalIndex.aliases) || {};
      const canonicalLabel = LITERAL_BOOK_OVERRIDES[label.toLowerCase()] || label;
      return (
        aliases[label.toLowerCase()] ||
        aliases[label.replace(/\s+/g, '_').toLowerCase()] ||
        aliases[canonicalLabel.toLowerCase()] ||
        aliases[canonicalLabel.replace(/\s+/g, '_').toLowerCase()] ||
        canonicalLabel
      );
    } catch(e){ return ''; }
  }
  async function loadLiteralIndex(){
    if (state.literalIndex) return state.literalIndex;
    if (state.literalIndexPromise) return state.literalIndexPromise;
    const url = new URL('./literal-index.json', document.baseURI).toString();
    state.literalIndexPromise = fetchJsonCached(url)
      .then(r => {
        state.literalIndex = (r && r.json && typeof r.json === 'object') ? r.json : {};
        return state.literalIndex;
      })
      .catch(() => {
        state.literalIndex = {};
        return state.literalIndex;
      })
      .finally(() => { state.literalIndexPromise = null; });
    return state.literalIndexPromise;
  }
  function normalizeLiteralType(value){
    return String(value || '')
      .toLowerCase()
      .replace(/\s+/g, '')
      .replace(/[^a-z0-9]/g, '');
  }
  function getNodePathById(root, targetId){
    const path = [];
    let done = false;
    (function dfs(node){
      if (!node || done) return;
      path.push(node);
      if (String(node.id) === String(targetId)){ done = true; return; }
      const kids = (node.children || []).concat(node._children || []);
      for (const child of kids){
        dfs(child);
        if (done) return;
      }
      path.pop();
    })(root);
    return done ? path.slice() : [];
  }
  function getMotherClauseTypeForNode(node){
    if (!node || node.id === undefined || node.id === null || !state || !state.data) return '';
    const path = getNodePathById(state.data, node.id);
    for (let i = path.length - 2; i >= 0; i -= 1){
      const candidate = path[i];
      if (candidate && candidate.ctype) return String(candidate.ctype);
    }
    return '';
  }
  function getLiteralVerseEntries(node){
    try {
      const literalIndex = (state.literalIndex && state.literalIndex.books) || {};
      const ref = parseVerseRef(node && node.verse);
      const bookKey = currentLiteralBookKey();
      if (!ref || !ref.chapter || !ref.verse || !bookKey) return [];
      const byBook = literalIndex[bookKey];
      const byChapter = byBook && byBook[String(ref.chapter)];
      const byVerse = byChapter && byChapter[String(ref.verse)];
      return Array.isArray(byVerse) ? byVerse : [];
    } catch(e){ return []; }
  }
  function resolveLiteralEntriesForNode(node){
    const entries = getLiteralVerseEntries(node);
    if (!entries.length) return [];
    const clauseType = normalizeLiteralType(node && node.ctype);
    const motherClauseType = normalizeLiteralType(getMotherClauseTypeForNode(node));
    if (clauseType){
      const exact = entries.filter(entry =>
        normalizeLiteralType(entry && entry.clauseType) === clauseType &&
        (!motherClauseType || normalizeLiteralType(entry && entry.motherClauseType) === motherClauseType)
      );
      if (exact.length) return exact;
      const clauseOnly = entries.filter(entry => normalizeLiteralType(entry && entry.clauseType) === clauseType);
      if (clauseOnly.length) return clauseOnly;
    }
    return entries;
  }
  function renderLiteralEntries(entries){
    if (!Array.isArray(entries) || !entries.length) return '';
    const lines = entries
      .map(entry => String(entry && entry.koreanLiteral || '').trim())
      .filter(Boolean);
    if (!lines.length) return '';
    if (lines.length === 1){
      return `<b>직역</b>: ${escapeHtml(lines[0])}`;
    }
    return `<b>직역</b>: ${lines.map(line => `<span class="literal-entry">${escapeHtml(line)}</span>`).join('<br>')}`;
  }
  function setSelectedNodeState(node){
    const selectedId = node && node.id !== undefined && node.id !== null ? node.id : null;
    state.selectedId = selectedId;
    state.selectedVerse = selectedId !== null ? (verseNumFromNode(node) || null) : null;
  }
  function clearNodeSelection(){
    state.selectedId = null;
    state.selectedVerse = null;
    try { render(); } catch(e){}
    try { syncSelectedVerseInPanel(false); } catch(e){}
    try { ensureListSelectionIntoView(); } catch(e){}
  }
  function applyNodeSelection(node, opts){
    if (!node || node.id === undefined || node.id === null) return false;
    const options = opts || {};
    setSelectedNodeState(node);
    try { render(); } catch(e){}
    try { syncSelectedVerseInPanel(!!options.scrollVerse); } catch(e){}
    try { ensureListSelectionIntoView(); } catch(e){}
    if (options.showDetails !== false) {
      try { showDetails(node); } catch(e){}
    }
    if (options.center) {
      requestAnimationFrame(() => { try { centerOnNodeId(node.id); } catch(e){} });
    }
    return true;
  }
  function toggleNodeSelection(node, opts){
    if (!node || node.id === undefined || node.id === null) return false;
    if (state.selectedId !== null && String(state.selectedId) === String(node.id)){
      clearNodeSelection();
      return false;
    }
    return applyNodeSelection(node, opts);
  }
  function selectFirstClauseForVerse(vnum){
    ensureDetailsVisible();
    const node = findFirstClauseNodeForVerse(vnum);
    if (!node){ showToast('해당 절의 절/절요소를 찾지 못했습니다', 'warn'); return; }
    try { ensurePathExpandedTo(node.id); } catch(e){}
    toggleNodeSelection(node, { center: true, scrollVerse: true, showDetails: true });
  }

  function setActiveVerseInPanel(vnum, doScroll){
    try {
      if (!versionsPanel || !versionsPanel.classList.contains('visible') || !versionContent) return;
      versionContent.querySelectorAll('.verse-item.hover').forEach(el => el.classList.remove('hover'));
      const el = versionContent.querySelector(`.verse-item[data-verse="${vnum}"]`);
      if (el){
        el.classList.add('hover');
        if (doScroll){ try { el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); } catch(e){} }
      }
    } catch(e){}
  }
  function clearActiveVerseInPanel(){
    try { if (!versionContent) return; versionContent.querySelectorAll('.verse-item.hover').forEach(el => el.classList.remove('hover')); } catch(e){}
  }

  // --- Details resizer (drag to set height) ---
  if (detailsResizer){
    let dragging = false;
    let startY = 0;
    let startH = 0;
    const onDown = (ev)=>{
      dragging = true;
      startY = (ev.touches? ev.touches[0].clientY : ev.clientY);
      startH = detailsPanel.getBoundingClientRect().height;
      document.documentElement.style.cursor = 'row-resize';
      document.body.style.userSelect = 'none';
      ev.preventDefault();
    };
    const onMove = (ev)=>{
      if (!dragging) return;
      const y = (ev.touches? ev.touches[0].clientY : ev.clientY);
      const dy = startY - y; // dragging up increases details height
      const minH = 60; // allow smaller minimum
      const maxH = Math.max(240, window.innerHeight * 0.95); // allow larger maximum
      let newH = Math.max(minH, Math.min(maxH, startH + dy));
      // apply via flex-basis so layout remains flexible
      detailsPanel.style.flex = `0 0 ${newH}px`;
    };
    const onUp = ()=>{
      if (!dragging) return;
      dragging = false;
      document.documentElement.style.cursor = '';
      document.body.style.userSelect = '';
    };
    detailsResizer.addEventListener('mousedown', onDown);
    detailsResizer.addEventListener('touchstart', onDown, { passive:false });
    window.addEventListener('mousemove', onMove);
    window.addEventListener('touchmove', onMove, { passive:false });
    window.addEventListener('mouseup', onUp);
    window.addEventListener('touchend', onUp);

    // Double-click handler removed per request; only drag-to-resize is supported.
  }

  function switchView(which){
    if (which==='tidy'){
      btnTidy.classList.add('active'); btnList.classList.remove('active');
      tidyView.classList.add('visible'); listView.classList.remove('visible');
      renderTidy();
    } else {
      btnList.classList.add('active'); btnTidy.classList.remove('active');
      listView.classList.add('visible'); tidyView.classList.remove('visible');
      renderList();
    }
  }

  function render(){ if (tidyView.classList.contains('visible')) renderTidy(); else renderList(); }

  // ---- Tidy helpers ----
  function shouldFadeNodeBySelectionAndLegend(data, active){
    const id = data && data.id;
    const verse = verseNumFromNode(data);
    const keepForSelection = !!(
      state.selectedId &&
      (
        String(id) === String(state.selectedId) ||
        (state.lastHoverVerse && verse === state.lastHoverVerse)
      )
    );
    const fadeForSelection = !!(state.selectedId && !keepForSelection);
    const cat = clauseClass(data);
    const fadeForLegend = !!(active && !active.has(cat));
    return fadeForSelection || fadeForLegend;
  }
  function shouldFadeLinkBySelectionAndLegend(link, active){
    const sourceData = link && link.source && link.source.data;
    const targetData = link && link.target && link.target.data;
    const sourceVisible = sourceData && !(
      state.selectedId &&
      !(
        String(sourceData.id) === String(state.selectedId) ||
        (state.lastHoverVerse && verseNumFromNode(sourceData) === state.lastHoverVerse)
      )
    );
    const targetVisible = targetData && !(
      state.selectedId &&
      !(
        String(targetData.id) === String(state.selectedId) ||
        (state.lastHoverVerse && verseNumFromNode(targetData) === state.lastHoverVerse)
      )
    );
    const fadeForSelection = !!(state.selectedId && !(sourceVisible || targetVisible));
    const sourceLegend = !!(active && !active.has(clauseClass(sourceData)));
    const targetLegend = !!(active && !active.has(clauseClass(targetData)));
    const fadeForLegend = !!(active && (sourceLegend || targetLegend));
    return fadeForSelection || fadeForLegend;
  }

  /** Apply selection- and legend-based fading on nodes and links. */
  function applyNodeFading(node, linkLayer){
    const active = (state.activeCats && state.activeCats.size) ? new Set(state.activeCats) : null;
    try { node.classed('faded', function(d){ return shouldFadeNodeBySelectionAndLegend(d && d.data, active); }); } catch(e){}
    try { linkLayer.classed('faded', function(d){ return shouldFadeLinkBySelectionAndLegend(d, active); }); } catch(e){}
  }

  /**
   * Add text labels to each node and, on next frame, measure and insert
   * rounded rect backgrounds sized to the text. Also raises the selected
   * node above siblings and decorates labels.
   */
  function addTextAndRects(node, labelTextForNodeCb){
    const textSel = node.append('text')
      .attr('dy','0.32em')
      .attr('x', 0)
      .attr('text-anchor', 'middle')
      .text(d=> { try { return labelTextForNodeCb ? labelTextForNodeCb(d) : ''; } catch(e){ return ''; } });
    const padX = 8, padY = 4;
    requestAnimationFrame(() => {
      try {
        textSel.each(function(d){
          try {
            const bbox = this.getBBox();
            const w = Math.max(10, bbox.width + padX*2);
            const h = Math.max(16, bbox.height + padY*2);
            const rx = -w/2; const ry = -h/2;
            d3.select(this.parentNode).insert('rect','text')
              .attr('class','node-rect ' + clauseClass(d && d.data))
              .attr('x', rx).attr('y', ry).attr('width', w).attr('height', h);
            d3.select(this).attr('x', 0).attr('dy', '0.32em');
          } catch (e) {
            const name = (d && d.data && d.data.name) ? d.data.name : '';
            const w = Math.max(40, name.length * 6) + padX*2; const h = 18 + padY*2; const rx = -w/2; const ry = -h/2;
            d3.select(this.parentNode).insert('rect','text')
              .attr('class','node-rect ' + clauseClass(d && d.data))
              .attr('x', rx).attr('y', ry).attr('width', w).attr('height', h);
            d3.select(this).attr('x', 0).attr('dy', '0.32em');
          }
        });
        try { node.selectAll('rect.node-rect').classed('hl', function(d){ const cat = clauseClass(d && d.data); return !!(state.highlightCats && state.highlightCats.has(cat)); }); } catch(e){}
        // Raise selected node to top
        try { if (state.selectedId){ node.each(function(d){ try { if (d && d.data && d.data.id === state.selectedId) { const p = this.parentNode; if (p) p.appendChild(this); } } catch(e){} }); } } catch(e){}
        // Decorate labels
        try { textSel.each(function(d){ try { decorateTidyNodeLabel(this, d && d.data); } catch(e){} }); } catch(e){}
      } catch(e){}
    });
    return textSel;
  }

  /** Add edge (relation) labels and schedule collision resolution. */
  function addEdgeLabelsAndResolve(g, links){
    const linksWithRela = links.filter(d=>{ const r=d&&d.target&&d.target.data&&d.target.data.rela; return (r&&r!=='NA'); });
    const elabelLayer = g.append('g').attr('class','edge-labels');
    const elGroups = elabelLayer.selectAll('g').data(linksWithRela).join('g').attr('class','edge-label-group');
    elGroups.each(function(d){ const r = d.target.data.rela; d3.select(this).append('text').attr('class', `edge-label ${classForRela(r)}`).attr('text-anchor','middle').text(r); });
    let edgeLabelIdle;
    function scheduleEdgeLabelResolve(){
      if (edgeLabelIdle) { try { cancelIdleCallback(edgeLabelIdle); } catch(e) { clearTimeout(edgeLabelIdle); } }
      const run = ()=> { try { resolveEdgeLabelCollisions(elGroups.nodes(), g.node(), state.orientation); } catch(e){} };
      try { edgeLabelIdle = requestIdleCallback(run, { timeout: 120 }); } catch(e) { edgeLabelIdle = setTimeout(run, 60); }
    }
    scheduleEdgeLabelResolve();
    return scheduleEdgeLabelResolve;
  }

  /**
   * Bind zoom behavior and restore previous view anchor/zoom if present.
   * Returns { zoom, appliedPrev }.
   */
  function setupZoomAndView(svg, g, baseX, baseY){
    const zoom = d3.zoom().on('zoom', (e)=> { g.attr('transform', e.transform); state.tidyZoom = e.transform; });
    svg.call(zoom);
    try { state.tidyZoomBehavior = zoom; state.tidySvg = svg.node(); } catch(e){}
    let appliedPrev = false;
    try {
      if (state.viewAnchor && typeof state.viewAnchor.x === 'number' && typeof state.viewAnchor.y === 'number'){
        const k = (state.viewAnchor.k && isFinite(state.viewAnchor.k)) ? state.viewAnchor.k : 1;
        const rect2 = (svg && svg.node && svg.node().getBoundingClientRect) ? svg.node().getBoundingClientRect() : tidyContainer.getBoundingClientRect();
        const cx2 = Math.max(0, rect2.width/2); const cy2 = Math.max(0, rect2.height/2);
        const tx = cx2 - baseX - k*state.viewAnchor.x; const ty = cy2 - baseY - k*state.viewAnchor.y;
        const t = d3.zoomIdentity.translate(tx, ty).scale(k);
        svg.call(zoom.transform, t);
        state.tidyZoom = t; appliedPrev = true;
      }
    } catch(e) { appliedPrev = false; }
    state.baseTranslate = { x: baseX, y: baseY };
    return { zoom, appliedPrev };
  }

  /** Render the tidy tree view (hierarchical D3 tree). */
  function renderTidy(){
    // Capture current view anchor before rerender so we can preserve viewpoint
    try { state.viewAnchor = captureViewAnchor(); } catch(e) { /* ignore */ }
    tidyContainer.innerHTML=''; if (!state.data) return;
    state.activeCats = (state.activeOnly && state.highlightCats && state.highlightCats.size) ? new Set(state.highlightCats) : null;
    const data = deepClone(state.data); applyCollapsed(data);
    const root = d3.hierarchy(data);
    // Spacing controlled by slider
    const baseSpacing = state.spacing || 280;
    const dy = baseSpacing; // depth spacing (left-right when horizontal, top-bottom when vertical)
    const dx = Math.max(12, Math.round(baseSpacing / 14)); // sibling spacing base (px)
    function labelTextForNode(d){
      if (!d || !d.data) return '';
      try{
        const meta = `${d.data.verse || ''} – ${d.data.ctype || ''} – `;
        let content = '';
        if (state.showGlossKo) {
          content = nodeGlossTextTidyKo(d.data);
        } else if (state.showGloss) {
          content = nodeGlossText(d.data);
        } else {
          content = (d.data.text_he || d.data.text || '');
        }
        return (meta + (content || '')).trim();
      } catch(e){ return String(d && d.data && d.data.name || ''); }
    }
    function estLabelWidthPx(d){
      const t = labelTextForNode(d);
      // approx average char width 6px + padding
      return Math.min(800, t.length * 6 + 16);
    }
    const tree=d3.tree().nodeSize([dx,dy]).separation((a,b)=>{
      // Base separation smaller to tighten vertical spacing
      const sameParent = (a.parent===b.parent);
      const baseSep = sameParent ? 0.9 : 1.25;
      // Compute minimal separation to avoid label overlap (estimated)
      const wa = estLabelWidthPx(a), wb = estLabelWidthPx(b);
      const requiredPx = (wa + wb) / 2 + 8; // centers must be at least this far apart
      const sepNeeded = requiredPx / dx;    // convert px to separation units
      // Clamp to reasonable bounds to avoid excessive spread for very long labels
      return Math.min(3.0, Math.max(baseSep, sepNeeded));
    });
    tree(root);
    let x0=Infinity,x1=-x0; root.each(d=>{ if(d.x>x1)x1=d.x; if(d.x<x0)x0=d.x; });
    const rect = tidyContainer.getBoundingClientRect();
    const cW = Math.max(320, Math.floor(rect.width || 0));
    const cH = Math.max(240, Math.floor(rect.height || 0));
    const svg=d3.select(tidyContainer).append('svg').attr('width', cW).attr('height', cH)
      .style('width','100%').style('height','100%');
    // Base translate to normalize top space; zoom layer preserves view
    const baseX = 40;
    const baseY = -x0 + dx;
    const gBase=svg.append('g').attr('class','base-layer').attr('transform',`translate(${baseX},${baseY})`);
    const g=gBase.append('g').attr('class','zoom-layer');
    const linkGen= state.orientation==='horizontal'? d3.linkHorizontal().x(d=>d.y).y(d=>d.x) : d3.linkVertical().x(d=>d.x).y(d=>d.y);
    const links=root.links();
    const linkLayer = g.append('g').attr('fill','none').attr('stroke','#aaa').attr('stroke-width',1.2)
      .selectAll('path').data(links).join('path').attr('class','tree-link')
      .attr('d', d=> state.orientation==='horizontal'
        ? linkGen({source:{x:d.source.x,y:d.source.y},target:{x:d.target.x,y:d.target.y}})
        : linkGen({source:{x:d.source.x,y:d.source.y},target:{x:d.target.x,y:d.target.y}}));
    // Nodes layer
    const node=g.append('g').selectAll('g').data(root.descendants()).join('g').attr('class','tree-node')
      .attr('data-verse-num', d => { try { const m = String(d && d.data && d.data.verse || '').match(/^[0-9A-Z]{3}\s+\d{2},(\d{2})/); return m ? String(parseInt(m[1],10)||'') : ''; } catch(e){ return ''; } })
      .attr('data-has-ctype', d => (d && d.data && d.data.ctype) ? '1' : '')
      .attr('transform', d=> state.orientation==='horizontal' ? `translate(${d.y},${d.x})` : `translate(${d.x},${d.y})`)
      .classed('selected', d => !!(state.selectedId && d && d.data && d.data.id===state.selectedId))
      .on('click', (ev, d)=> {
        if (state.showDetails) {
          ev.stopPropagation();
          toggleNodeSelection(d.data, { showDetails: true, scrollVerse: true });
        } else {
          toggleNode(d.data);
        }
      })
      .on('mouseenter', (ev, d)=>{ try { const v = verseNumFromNode(d && d.data); if (v) setActiveVerseInPanel(v, false); } catch(e){} })
      .on('mouseleave', ()=>{ try { clearActiveVerseInPanel(); } catch(e){} });
    // Apply selection and legend-based fading
    applyNodeFading(node, linkLayer);
    const textSel = addTextAndRects(node, labelTextForNode);

    // Edge labels (rela) after nodes for visibility and collision-aware placement
    const scheduleEdgeLabelResolve = addEdgeLabelsAndResolve(g, links);
    // Zoom behavior with view preservation
    const { zoom, appliedPrev } = setupZoomAndView(svg, g, baseX, baseY);
    try { svg.on('end', null); } catch(e){}
    try { zoom.on('end', ()=> { scheduleEdgeLabelResolve(); }); } catch(e){}

    // Initial fit to content area on first load of a chapter
    try {
      const key = (function(){
        try {
          const book = (elBook && elBook.value) ? String(elBook.value) : '';
          const chapter = (elChapter && elChapter.value) ? String(elChapter.value) : '';
          return `${book}:${chapter}`;
        } catch(e){ return 'default'; }
      })();
      if ((!state.fitDoneFor || !state.fitDoneFor.has(key)) && !appliedPrev){
        requestAnimationFrame(() => {
          requestAnimationFrame(() => { try { fitAllIntoView(svg, g, zoom); state.fitDoneFor.add(key); } catch(e){} });
        });
      }
    } catch(e) { /* ignore */ }
  }

  function captureViewAnchor(){
    try {
      const svg = state.tidySvg; const z = state.tidyZoom; const base = state.baseTranslate || {x:0,y:0};
      if (!svg || !z) return null;
      // Selection-anchored mode: try to preserve selected node position
      if (state.anchorMode === 'selection' && state.selectedId){
        try {
          const nodes = tidyContainer.querySelectorAll('g.tree-node');
          for (const el of nodes){
            const d = el && el.__data__;
            if (d && d.data && d.data.id === state.selectedId){
              const isH = (state.orientation === 'horizontal');
              const wx = isH ? d.y : d.x; // world coords in zoom-layer space
              const wy = isH ? d.x : d.y;
              const k = (z.k && isFinite(z.k)) ? z.k : 1;
              return { x: wx, y: wy, k };
            }
          }
        } catch(e) { /* fallthrough to center */ }
      }
      const rect = svg.getBoundingClientRect ? svg.getBoundingClientRect() : { width: tidyContainer.clientWidth, height: tidyContainer.clientHeight };
      const cx = Math.max(0, rect.width/2);
      const cy = Math.max(0, rect.height/2);
      const k = (z.k && isFinite(z.k)) ? z.k : 1;
      const wx = (cx - base.x - z.x) / k;
      const wy = (cy - base.y - z.y) / k;
      return { x: wx, y: wy, k };
    } catch(e) { return null; }
  }

  function fitAllIntoView(svgSel, gSel, zoom){
    try {
      const svg = svgSel && svgSel.node ? svgSel.node() : svgSel;
      const gNode = gSel && gSel.node ? gSel.node() : gSel;
      if (!svg || !gNode) return;
      const sbox = svg.getBoundingClientRect();
      const pad = Math.max(16, Math.min(48, Math.floor(Math.min(sbox.width, sbox.height) * 0.04)));
      // Try precise bbox first
      let bb = null;
      try { bb = gNode.getBBox(); } catch(e) { bb = null; }
      let minX, minY, maxX, maxY;
      if (bb && isFinite(bb.width) && isFinite(bb.height) && bb.width>0 && bb.height>0){
        minX = bb.x; minY = bb.y; maxX = bb.x + bb.width; maxY = bb.y + bb.height;
      } else {
        // Fallback: compute from bound data
        minX = Infinity; minY = Infinity; maxX = -Infinity; maxY = -Infinity;
        const nodes = []; try { d3.select(gNode).selectAll('g.tree-node').each(function(d){ nodes.push(d); }); } catch(e){}
        nodes.forEach(d => {
          if (!d) return;
          const isH = (state.orientation==='horizontal');
          const x = isH ? d.y : d.x;
          const y = isH ? d.x : d.y;
          // conservative width estimate
          const t = (d && d.data && (d.data.name || '')) + '';
          const w = Math.min(1000, t.length * 6 + 16);
          const h = 22;
          minX = Math.min(minX, x - w/2); maxX = Math.max(maxX, x + w/2);
          minY = Math.min(minY, y - h/2); maxY = Math.max(maxY, y + h/2);
        });
        if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) return;
      }
      const contentW = Math.max(1, maxX - minX);
      const contentH = Math.max(1, maxY - minY);
      const viewW = Math.max(1, sbox.width);
      const viewH = Math.max(1, sbox.height);
      const kx = (viewW - pad*2) / contentW;
      const ky = (viewH - pad*2) / contentH;
      let k = Math.max(0.05, Math.min(kx, ky));
      // Translate so that (minX,minY) maps to (pad,pad)
      const tx = pad - minX * k;
      const ty = pad - minY * k;
      const t = d3.zoomIdentity.translate(tx, ty).scale(k);
      try { svgSel.call(zoom.transform, t); } catch(e) { d3.select(gNode).attr('transform', `translate(${tx},${ty}) scale(${k})`); }
      state.tidyZoom = t;
    } catch(e) { /* ignore */ }
  }

  /** Render the indented list view (DOM list, not SVG). */
  function renderList(){
    listContainer.innerHTML=''; if(!state.data) return;
    const ul=document.createElement('ul'); ul.className='indented'; listContainer.appendChild(ul);
    const data=deepClone(state.data); applyCollapsed(data);
    data.children.forEach(ch=> ul.appendChild(renderItem(ch,0)));
    // Apply highlight and fading based on legend selections and selection state
    const active = (state.activeOnly && state.highlightCats && state.highlightCats.size)
      ? new Set(state.highlightCats)
      : null;
    const lis = listContainer.querySelectorAll('li.node-item');
    lis.forEach(li => {
      // find 'cat-*' class on li
      let cat = null;
      li.className.split(/\s+/).forEach(c => { if (c.startsWith('cat-')) cat = c; });
      if (cat && state.highlightCats && state.highlightCats.has(cat)) li.classList.add('hl'); else li.classList.remove('hl');
      const node = findNodeInStateById(li.getAttribute('data-node-id'));
      li.classList.toggle('faded', shouldFadeNodeBySelectionAndLegend(node, active));
    });
  }

  function renderItem(node, level){
    const li=document.createElement('li'); li.className='node-item ' + clauseClass(node);
    try { if (node && node.id !== undefined && node.id !== null) li.setAttribute('data-node-id', String(node.id)); } catch(e){}
    // annotate list items for cross-view hover/highlight
    try { const vnum = verseNumFromNode(node); if (vnum) li.setAttribute('data-verse-num', String(vnum)); } catch(e){}
    try { li.setAttribute('data-has-ctype', isClauseNode(node) ? '1' : ''); } catch(e){}
    if (state.selectedId && node && node.id===state.selectedId) li.classList.add('selected');
    // quote highlight (CTT qBlockId/qDepth preferred)
    const depthClass = node.qDepth ? ` depth-${Math.min(4, node.qDepth)}` : '';
    if ((node.qBlockId && node.qBlockId>0) || node.text_type==='Q') li.className += ' q-row'+depthClass;
    const line=document.createElement('div'); line.className='node-line';
    const tog=document.createElement('span'); tog.className='toggle'+(node.children&&node.children.length?'':' leaf');
    tog.textContent=isCollapsed(node)?'+':(node.children&&node.children.length?'−':'•');
    tog.addEventListener('click',()=>toggleNode(node));
    const t=document.createElement('span'); t.className='name';
    const meta = `${node.verse || ''} – ${node.ctype || ''} – `;
    let content = '';
    if (state.showGlossKo) {
      content = nodeGlossTextTidyKo(node);
    } else if (state.showGloss) {
      content = nodeGlossText(node);
    } else {
      content = (node.text_he || node.text || '');
    }
    if ((state.showGloss || state.showGlossKo) && (!content || !content.trim())) content = node.text || node.text_he || '';
    t.textContent = meta + content;
    line.appendChild(tog); line.appendChild(t); li.appendChild(line);
    if (state.showDetails){
      t.style.cursor='pointer';
      t.addEventListener('click', ()=> toggleNodeSelection(node, { showDetails: true, scrollVerse: true }));
    }
    if(node.children&&node.children.length){ const ul=document.createElement('ul'); ul.className='indented'; if(!isCollapsed(node)) node.children.forEach(c=> ul.appendChild(renderItem(c,level+1))); li.appendChild(ul);} return li;
  }

  function ensureListSelectionIntoView(){
    try {
      if (!listView || !listView.classList.contains('visible')) return;
      const sel = listContainer.querySelector('li.node-item.selected');
      if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } catch(e){}
  }

  function toggleNode(n){ if(!n||n.id==='root')return; if(state.collapsed.has(n.id)) state.collapsed.delete(n.id); else state.collapsed.add(n.id); render(); }
  function isCollapsed(d){ return d && d.id!=='root' && state.collapsed.has(d.id); }
  function applyCollapsed(root){ walk(root, (n,depth)=>{
    if(n.children&&n.children.length&&isCollapsed(n)){
      n._children=n.children; n.children=[];
    } else if(n._children&&n._children.length&&!isCollapsed(n)){
      n.children=n._children; n._children=[];
    }
  }); }
  function walk(n,fn,depth=0){ fn(n,depth); const kids=(n.children&&n.children.length)?n.children:(n._children||[]); if(kids&&kids.length) kids.forEach(k=> walk(k,fn,depth+1)); }
  function deepClone(o){ return JSON.parse(JSON.stringify(o)); }
  function clauseClass(n){
    if (!n) return 'cat-other';
    const t = (n.ctype || n.typ || '')+'';
    const s = t.toLowerCase();
    const rela = ((n.rela||'')+'').toLowerCase();
    const toks = Array.isArray(n.tokens) ? n.tokens : [];
    const pos = countPos(toks);
    const hasVerb = pos.verb > 0 || toks.some(x=> norm(x.vs) || norm(x.vt));
    const hasAdj  = pos.adjv > 0;
    const hasNoun = (pos.subs + pos.nmpr) > 0;
    const prepRatio = toks.length ? pos.prep / toks.length : 0;

    // 1) Specific clause forms by ctype codes
    if (/ptcp|ptca/.test(s)) return 'cat-part';
    if (/inf[a|c]?/.test(s)) return 'cat-inf';
    if (/imv|juss|coh/.test(s)) return 'cat-imv';
    if (/(way|wxq|wqtl|weq|weyiq|wqt)/.test(s)) return 'cat-weq';
    if (/nmcl|nom/.test(s)) return hasAdj ? 'cat-adj' : 'cat-noun';

    // 2) Relation-based: attributive -> relative/adjectival
    if (rela === 'attr') return 'cat-rel';

    // 3) POS-driven fallbacks
    if (hasAdj && !hasVerb) return 'cat-adj';
    if (!hasVerb && hasNoun) return 'cat-noun';
    if (!hasVerb && prepRatio >= 0.5) return 'cat-pp';
    if (!hasVerb && !hasNoun) return 'cat-verbless';

    // 4) Interjection-dominant
    if (pos.intj > 0 && pos.verb === 0) return 'cat-intj';

    // 5) Generic verbal clause
    if (s.endsWith('cl') || hasVerb) return 'cat-verb';
    return 'cat-other';
  }
  function countPos(toks){
    const c = {verb:0, adjv:0, subs:0, nmpr:0, prep:0, advb:0, intj:0};
    for (const t of toks){
      const sp = (t && t.sp ? String(t.sp).toLowerCase() : '');
      if (sp==='verb') c.verb++;
      else if (sp==='adjv') c.adjv++;
      else if (sp==='subs') c.subs++;
      else if (sp==='nmpr') c.nmpr++;
      else if (sp==='prep') c.prep++;
      else if (sp==='advb') c.advb++;
      else if (sp==='intj') c.intj++;
    }
    return c;
  }

  function nodeGlossText(n){
    // 한글 우선 옵션
    if (state.showGlossKo){
      const tks = (n && Array.isArray(n.tokens)) ? n.tokens.map(t => {
        const s = norm(t.gloss_ko);
        return s ? s.replaceAll('/', ';') : '';
      }).filter(Boolean) : [];
      if (tks.length) return tks.join(' | ');
      const gk = norm(n && n.gloss_ko);
      if (gk){
        // 백엔드에서 이미 ' | '로 결합됨을 가정, '/'는 ';'로 치환
        return gk.replaceAll('/', ';');
      }
    }
    // 기본 영어 gloss
    const engTokens = (n && Array.isArray(n.tokens)) ? n.tokens.map(t => norm(t.gloss)).filter(Boolean) : [];
    if (engTokens.length) return engTokens.join(' | ');
    const g = norm(n && n.gloss);
    if (g){ return g; }
    return (n && (n.text_he || n.text)) ? (n.text_he || n.text) : '';
  }

  // Tidy 트리 전용(한글 gloss): ';'로 여러 뜻이 구분된 경우 각 단어의 첫 번째 뜻만 사용
  function nodeGlossTextTidyKo(n){
    // 1) 토큰이 있는 경우: 각 토큰의 첫 뜻만 추출하여 ' | '로 결합
    const toks = (n && Array.isArray(n.tokens)) ? n.tokens : [];
    if (toks.length){
      const list = toks.map(t => {
        let s = norm(t && t.gloss_ko);
        if (!s) return '';
        // 표준화: '/'는 ';'로 통일한 후 첫 세미콜론 이전만 취함
        s = s.replaceAll('/', ';');
        const idx = s.indexOf(';');
        return (idx >= 0 ? s.slice(0, idx) : s).trim();
      }).filter(Boolean);
      if (list.length) return list.join(' | ');
    }
    // 2) 토큰이 없고 노드 수준 요약만 있는 경우: ' | '로 단어 분할 → 각 단어에서 첫 뜻만
    const gk = norm(n && n.gloss_ko);
    if (gk){
      const perWord = gk.replaceAll('/', ';').split(/\s*\|\s*/).filter(Boolean);
      const firsts = perWord.map(s => {
        const idx = s.indexOf(';');
        return (idx >= 0 ? s.slice(0, idx) : s).trim();
      }).filter(Boolean);
      if (firsts.length) return firsts.join(' | ');
      return gk.replaceAll('/', ';');
    }
    // 3) 한글이 없으면 영어 gloss로 대체
    const engTokens = (n && Array.isArray(n.tokens)) ? n.tokens.map(t => norm(t.gloss)).filter(Boolean) : [];
    if (engTokens.length) return engTokens.join(' | ');
    const g = norm(n && n.gloss);
    if (g) return g;
    return (n && (n.text_he || n.text)) ? (n.text_he || n.text) : '';
  }

  

  

  function recomputeCollapsedToDepth(){
    if (!state.data) return;
    const limit = Math.max(0, state.depthLimit|0);
    const newSet = new Set();
    (function rec(n, depth){
      if (!n) return;
      if (n.id !== 'root'){
        if (depth === limit && n.children && n.children.length){
          newSet.add(n.id);
        }
      }
      if (depth < limit) {
        const kids = n.children || [];
        for (const c of kids) rec(c, depth+1);
      }
    })(state.data, 0);
    state.collapsed = newSet;
  }

  function treeHeight(root){
    let h = 0;
    (function rec(n,d){ h = Math.max(h,d); const kids = (n.children||[]); for(const c of kids) rec(c,d+1); })(root,0);
    return h;
  }

  function classForRela(r){
    // Map first 4 letters to class set above; default neutral
    const key = (r||'').slice(0,4);
    switch (key){
      case 'Coor': return 'rela-Coor';
      case 'Cmpl': return 'rela-Cmpl';
      case 'Subj': return 'rela-Subj';
      case 'Objc': return 'rela-Objc';
      case 'Adju': return 'rela-Adju';
      case 'Attr': return 'rela-Attr';
      case 'Spec': return 'rela-Spec';
      case 'Resu': return 'rela-Resu';
      default: return '';
    }
  }

  function resolveEdgeLabelCollisions(labelGroups, gNode, orientation){
    // Precompute link middle + normal per label group from bound data
    const placements = labelGroups.map(node => {
      const d = d3.select(node).datum();
      let vx, vy;
      if (orientation==='horizontal'){
        vx = (d.target.y - d.source.y);
        vy = (d.target.x - d.source.x);
      } else {
        vx = (d.target.x - d.source.x);
        vy = (d.target.y - d.source.y);
      }
      const len = Math.max(1e-6, Math.hypot(vx,vy));
      const nx = -vy/len, ny = vx/len; // normal
      const mx = orientation==='horizontal' ? (d.source.y + d.target.y)/2 : (d.source.x + d.target.x)/2;
      const my = orientation==='horizontal' ? (d.source.x + d.target.x)/2 : (d.source.y + d.target.y)/2;
      return { node, mx, my, nx, ny };
    });
    // Collect node rects (screen space)
    const nodeRects = Array.from(gNode.querySelectorAll('.node-rect')).map(el => el.getBoundingClientRect());
    const placedRects = [];
    const candidates = [0,1,-1,2,-2,3,-3,4,-4,5,-5];
    const step = 12;
    placements.forEach(p => {
      const sel = d3.select(p.node);
      const text = sel.select('text');
      // try different offsets
      let chosen = {x:p.mx, y:p.my};
      for (let i=0;i<candidates.length;i++){
        const off = candidates[i]*step;
        const cx = p.mx + p.nx*off;
        const cy = p.my + p.ny*off;
        sel.attr('transform', `translate(${cx},${cy})`);
        // measure bbox of text
        const tnode = text.node();
        if (!tnode) continue;
        let bbox;
        try { bbox = tnode.getBoundingClientRect(); } catch(e){ bbox = null; }
        if (!bbox || (bbox.width===0 && bbox.height===0)) continue;
        const inflated = inflateRect(bbox, 2);
        const overlapsNode = nodeRects.some(r => rectsOverlap(inflated, r));
        const overlapsLabel = placedRects.some(r => rectsOverlap(inflated, r));
        if (!overlapsNode && !overlapsLabel){
          chosen = {x:cx, y:cy};
          placedRects.push(inflated);
          // add a background rect sized to text
          const localBBox = tnode.getBBox();
          const bg = sel.insert('rect', 'text').attr('class','edge-label-bg');
          bg.attr('x', -localBBox.width/2 - 4)
            .attr('y', -localBBox.height/2 - 1)
            .attr('width', localBBox.width + 8)
            .attr('height', localBBox.height + 2);
          break;
        }
      }
      // final fallback: place at mid
      sel.attr('transform', `translate(${chosen.x},${chosen.y})`);
    });
  }

  function rectsOverlap(a,b){
    return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
  }
  function inflateRect(r, pad){ return { left: r.left-pad, top: r.top-pad, right: r.right+pad, bottom: r.bottom+pad, width: r.width+pad*2, height: r.height+pad*2 }; }

  function showDetails(n){
    if (!detailsPanel) return;
    // 경량 트리에서 상세 필드가 빠져 있으면 full tree로 승격 로드
    try {
      const missingTokens = !Array.isArray(n.tokens) || !n.tokens.length;
      const missingSegments = (state && state.source === 'tf') && !Array.isArray(n.phrase_segments);
      const needFullTree = (missingTokens || missingSegments) && (String(n.id).match(/^[0-9]+$/));
      if (needFullTree){
        detailsPanel.innerHTML = '<div class="kv">세부 정보를 불러오는 중...</div>';
        reloadWithDetails(n.id).catch(()=>{});
        return;
      }
    } catch(e) { /* ignore */ }
    // 헤더 메타
    const detailNodeId = String((n && n.id) || '');
    const verse = norm(n.verse);
    const ctype = norm(n.ctype);
    const rela = norm(n.rela);
    const txtType = norm(n.text_type);
    const funcs = norm(Array.isArray(n.funcs) ? n.funcs.join(', ') : (n.funcs || ''));
    // 토큰 테이블
    const tokens = Array.isArray(n.tokens) ? n.tokens : [];
    const rows = tokens.map(t => {
      const sp = valueKo('sp', t.sp), ps = valueKo('ps', t.ps), nu=valueKo('nu', t.nu), gn=valueKo('gn', t.gn), st=valueKo('st', t.st), vs=norm(t.vs), vt=norm(t.vt);
      const lemma = escapeHtml(norm(t.lemma));
      const glossRaw = norm(t.gloss);
      const gloss = escapeHtml(splitGloss(glossRaw).join(' | ') || glossRaw);
      const glossKoRaw = norm(t.gloss_ko);
      // 한글 gloss는 '/'를 ';'로 치환해 전체 그대로 표시
      const glossKo = escapeHtml((glossKoRaw || '').replaceAll('/', ';'));
      const w = safe(t.w);
      const wid = (t && (t.wid || t.id)) ? String(t.wid || t.id) : '';
      return `<tr data-wid="${wid}"><td class="token-he">${w}</td><td class="token-lemma">${lemma}</td><td class="tok-gloss">${gloss}</td><td>${glossKo}</td><td class="mono">${sp}</td><td class="mono">${ps}</td><td class="mono">${nu}</td><td class="mono">${gn}</td><td class="mono">${st}</td><td class="mono">${vs}</td><td class="mono">${vt}</td></tr>`;
    }).join('');
    const koLine = n.gloss_ko ? `<div class="kv"><b>해석(한)</b>: ${escapeHtml(n.gloss_ko)}</div>` : '';
    const literalPlaceholder = `<div class="kv" id="literalLine"></div>`;
    // KNT 절 텍스트 자리 표시자 (해석(한) 아래)
    const kntPlaceholder = `<div class="kv" id="kntVerseLine"></div>`;
    const nav = buildDetailsNav(n && n.id);
    const head = `
      ${nav}
      <div class="kv"><b>절</b>: ${escapeHtml(verse)} &nbsp; <b>문장유형</b>: ${escapeHtml(ctype)} &nbsp; <b>관계</b>: ${escapeHtml(rela)}</div>
      <div class="kv"><b>텍스트 유형</b>: ${escapeHtml(txtType)} &nbsp; <b>기능</b>: ${escapeHtml(funcs)}</div>
      ${koLine}
      ${literalPlaceholder}
      ${kntPlaceholder}
    `;
    const phrasePlaceholder = `<div class="section-title">구(phrase) 분해</div><div id="phraseSegments"></div>`;
    const table = `
      <div class="section-title">토큰 상세</div>
      <table class="token-table">
        <thead><tr><th>형태(히브리)</th><th>원형</th><th>해석(영)</th><th>해석(한)</th><th>품사</th><th>인칭</th><th>수</th><th>성</th><th>상태</th><th>동사 어간</th><th>동사형</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
    detailsPanel.innerHTML = head + phrasePlaceholder + table;
    detailsPanel.setAttribute('data-detail-node-id', detailNodeId);
    try { wireDetailsNav(n && n.id); } catch(e){}

    loadLiteralIndex()
      .then(() => {
        if (detailsPanel.getAttribute('data-detail-node-id') !== detailNodeId) return;
        const line = document.getElementById('literalLine');
        if (!line) return;
        const rendered = renderLiteralEntries(resolveLiteralEntriesForNode(n));
        line.innerHTML = rendered;
      })
      .catch(() => {
        if (detailsPanel.getAttribute('data-detail-node-id') !== detailNodeId) return;
        const line = document.getElementById('literalLine');
        if (line) line.innerHTML = '';
      });

    // KNT 절 텍스트 로드: node.verse("GEN 01,03")에서 장/절 추출하여 백엔드 요청
    try {
      const ref = parseVerseRef(verse);
      if (ref && ref.chapter && ref.verse){
        const book = (elBook && elBook.value) ? elBook.value : '';
        fetchVersionsChapter('knt', book, ref.chapter)
          .then(result => {
            if (detailsPanel.getAttribute('data-detail-node-id') !== detailNodeId) return;
            const line = document.getElementById('kntVerseLine');
            if (!line) return;
            const verseItem = result && result.ok ? (result.verses || []).find(v => (parseInt(v && v.verse, 10) || 0) === ref.verse) : null;
            if (verseItem && verseItem.text){
              line.innerHTML = `<b>KNT</b>: ${escapeHtml(String(verseItem.text))}`;
            } else {
              line.innerHTML = '';
            }
          })
          .catch(() => {
            if (detailsPanel.getAttribute('data-detail-node-id') !== detailNodeId) return;
            const line = document.getElementById('kntVerseLine');
            if(line) line.innerHTML='';
          });
      }
    } catch(e) { /* ignore */ }
    // 구(phrase) 분해 로드 (칩 표시 + 토큰 표 색상 연동)
    try {
      const wrap = document.getElementById('phraseSegments');
      const applySegments = (segments) => {
        if (wrap){
          if (!Array.isArray(segments) || !segments.length) { wrap.innerHTML=''; return; }
          wrap.innerHTML = segments.map(seg => phraseChip(seg)).join(' ');
        }
        if (Array.isArray(segments)){
          const map = new Map();
          segments.forEach(seg => {
            const cat = String(seg && seg.cat || 'other');
            const cls = `ph-${cat}`;
            const toks = Array.isArray(seg && seg.tokens) ? seg.tokens : [];
            toks.forEach(t => {
              if (t && (t.wid!==undefined && t.wid!==null)){
                map.set(String(t.wid), cls);
              }
            });
          });
          const tbody = detailsPanel.querySelector('.token-table tbody');
          if (tbody){
            tbody.querySelectorAll('tr').forEach(tr => {
              const wid = tr.getAttribute('data-wid');
              if (!wid) return;
              const cls = map.get(wid);
              if (!cls) return;
              const tds = tr.querySelectorAll('td');
              if (tds && tds.length){
                tds[0].classList.add(cls);
                tds[1].classList.add(cls);
              }
            });
          }
        }
      };
      if (Array.isArray(n.phrase_segments)){
        applySegments(n.phrase_segments);
      } else if (wrap) {
        wrap.innerHTML = '';
      }
    } catch(e) { /* ignore */ }
  }

  // Center view on a specific node id (tidy tree)
  /** Center tidy view on the node with the given id, preserving current zoom. */
  function centerOnNodeId(id){
    try {
      const svg = state.tidySvg; const z = state.tidyZoom; const zoom = state.tidyZoomBehavior; const base = state.baseTranslate || {x:0,y:0};
      if (!svg || !zoom) return;
      // find D3 bound node by id
      const nodes = tidyContainer.querySelectorAll('g.tree-node');
      let target = null;
      for (const el of nodes){ const d = el && el.__data__; if (d && d.data && d.data.id === id){ target = d; break; } }
      if (!target) return;
      const isH = (state.orientation === 'horizontal');
      const wx = isH ? target.y : target.x; // world coords in zoom-layer space
      const wy = isH ? target.x : target.y;
      const rect = svg.getBoundingClientRect ? svg.getBoundingClientRect() : { width: tidyContainer.clientWidth, height: tidyContainer.clientHeight };
      const cx = Math.max(0, rect.width/2);
      const cy = Math.max(0, rect.height/2);
      const k = (z && z.k && isFinite(z.k)) ? z.k : 1;
      const tx = cx - base.x - k*wx;
      const ty = cy - base.y - k*wy;
      const t = d3.zoomIdentity.translate(tx, ty).scale(k);
      d3.select(svg).call(zoom.transform, t);
      state.tidyZoom = t;
    } catch(e){}
  }

  // ---- Prev/Next clause navigation helpers ----
  function flattenClauseIds(root){
    const out = [];
    if (!root) return out;
    walk(root, (n)=>{ if (!n) return; const id = n.id; if (id!==undefined && id!==null && id !== 'root') out.push(id); });
    return out;
  }
  function findNodeInStateById(id){
    let found = null;
    if (!state || !state.data) return null;
    walk(state.data, (n)=>{ if (found) return; if (n && String(n.id) === String(id)) found = n; });
    return found;
  }
  function ensurePathExpandedTo(id){
    try {
      if (!state || !state.data) return;
      const path = [];
      let done = false;
      (function dfs(n){
        if (!n || done) return;
        path.push(n);
        if (n.id === id){ done = true; return; }
        const kids = (n.children||[]).concat(n._children||[]);
        for (const c of kids){ dfs(c); if (done) return; }
        path.pop();
      })(state.data);
      if (!done) return;
      for (const node of path){
        if (node && node.id && state.collapsed && state.collapsed.has(node.id)) state.collapsed.delete(node.id);
      }
    } catch(e) { /* ignore */ }
  }
  function goToNeighbor(currentId, dir){
    try {
      if (!state || !state.data) return;
      const ids = flattenClauseIds(state.data);
      const idx = ids.findIndex(x => x === currentId);
      if (idx < 0) return;
      const nextIdx = dir > 0 ? idx + 1 : idx - 1;
      if (nextIdx < 0 || nextIdx >= ids.length) return;
      const targetId = ids[nextIdx];
      ensurePathExpandedTo(targetId);
      const node = findNodeInStateById(targetId);
      if (node) applyNodeSelection(node, { showDetails: true, scrollVerse: true });
    } catch(e) { /* ignore */ }
  }
  function buildDetailsNav(currentId){
    try {
      if (!state || !state.data || currentId===undefined || currentId===null) return '';
      const ids = flattenClauseIds(state.data);
      const idx = ids.findIndex(x => x === currentId);
      if (idx < 0) return '';
      const hasPrev = idx > 0;
      const hasNext = idx < ids.length - 1;
      const prevDis = hasPrev ? '' : 'disabled';
      const nextDis = hasNext ? '' : 'disabled';
      return `
        <div class=\"details-nav\">
          <button id=\"btnPrevClause\" ${prevDis}>⟨ 이전 절</button>
          <span class=\"sep\"></span>
          <button id=\"btnNextClause\" ${nextDis}>다음 절 ⟩</button>
        </div>`;
    } catch(e) { return ''; }
  }
  function wireDetailsNav(currentId){
    const btnPrev = document.getElementById('btnPrevClause');
    const btnNext = document.getElementById('btnNextClause');
    if (btnPrev){ btnPrev.addEventListener('click', ()=> goToNeighbor(currentId, -1)); }
    if (btnNext){ btnNext.addEventListener('click', ()=> goToNeighbor(currentId, +1)); }
  }

  function phraseChip(seg){
    const cat = String(seg && seg.cat || 'other');
    const catKo = String(seg && seg.cat_ko || '구');
    const func = String(seg && seg.function || '');
    const text = String(seg && seg.text || '');
    const label = func ? `${catKo} (${func})` : `${catKo}`;
    const body = escapeHtml(text);
    return `<span class="phrase-chip ph-${cat}"><span class="label">${label}</span><span class="text">${body}</span></span>`;
  }

  function safe(v){ return (v===undefined||v===null)?'':String(v); }
  function norm(v){
    const s = safe(v).trim();
    if (!s) return '';
    if (s.toUpperCase && s.toUpperCase()==='NA') return '-';
    return s;
  }
  function splitGloss(s){
    const raw = safe(s);
    const arr = raw.split(/[;,\/]/).map(x=>x.trim()).filter(Boolean);
    // normalize leading 'to '
    const out = [];
    const seen = new Set();
    for (let p of arr){
      const cand = [p];
      if (p.toLowerCase().startsWith('to ')) cand.push(p.slice(3).trim());
      for (let c of cand){
        if (c && !seen.has(c)){ seen.add(c); out.push(c); }
      }
    }
    return out;
  }
  function uniq(list){
    const out=[]; const seen=new Set();
    for(const x of list){ if(x && !seen.has(x)){ seen.add(x); out.push(x);} }
    return out;
  }
  function valueKo(key, v){
    const s = norm(v);
    if (!s) return '';
    const x = s.toLowerCase();
    if (key==='ps'){
      if (x==='1' || x==='p1') return '1인칭';
      if (x==='2' || x==='p2') return '2인칭';
      if (x==='3' || x==='p3') return '3인칭';
      return s;
    }
    if (key==='nu'){
      if (x==='sg') return '단수';
      if (x==='du') return '쌍수';
      if (x==='pl') return '복수';
      return s;
    }
    if (key==='gn'){
      if (x==='m') return '남성';
      if (x==='f') return '여성';
      if (x==='b' || x==='c' || x==='mf') return '공용';
      return s;
    }
    if (key==='st'){
      if (x==='a') return '절대형';
      if (x==='c') return '연계형';
      if (x==='d') return '정관형';
      return s;
    }
    if (key==='sp'){
      const map = {
        'verb':'동사','subs':'명사','nmpr':'고유명사','adjv':'형용사','advb':'부사',
        'prps':'인칭대명사','prde':'지시대명사','prn':'대명사','prep':'전치사','conj':'접속사',
        'art':'관사','intj':'감탄사','inrg':'의문사','nega':'부정어','ptcl':'불변화사','numr':'수사'
      };
      return map[x] || s;
    }
    return s;
  }

  // --- Tidy label decoration helpers ---
  function firstSenseKo(s){
    const raw = norm(s);
    if (!raw) return '';
    const std = raw.replaceAll('/', ';');
    const i = std.indexOf(';');
    return (i >= 0 ? std.slice(0, i) : std).trim();
  }

  async function ensureSegForNode(id){
    try {
      const key = String(id);
      if (state.tidySegCache.has(key)) return state.tidySegCache.get(key);
      const node = findNodeById(state.data, id);
      if (node && Array.isArray(node.phrase_segments)){
        const out = { segs: node.phrase_segments };
        state.tidySegCache.set(key, out);
        return out;
      }
      const out = { segs: [] };
      state.tidySegCache.set(key, out);
      return out;
    } catch(e){ return { segs: [] }; }
  }

  function rebuildTidyTextWithSeg(textEl, data, segs){
    if (!textEl || !data) return;
    const sel = d3.select(textEl);
    // Build token order and subject/predicate sets
    const subj = new Set();
    const pred = new Set();
    const order = []; const seen = new Set();
    for (const seg of segs){
      const fn = String(seg && seg.function || '');
      const toks = Array.isArray(seg && seg.tokens) ? seg.tokens : [];
      if (fn === 'Subj'){ toks.forEach(t => { if (t && (t.wid!==undefined && t.wid!==null)) subj.add(String(t.wid)); }); }
      if (fn === 'Pred'){ toks.forEach(t => { if (t && (t.wid!==undefined && t.wid!==null)) pred.add(String(t.wid)); }); }
      for (const t of toks){
        const wid = (t && (t.wid || t.id)) ? String(t.wid || t.id) : '';
        if (wid && !seen.has(wid)){ seen.add(wid); order.push(t); }
      }
    }
    if (!order.length) return; // nothing to decorate
    // Rebuild text with tspans
    sel.text('');
    const meta = `${data.verse || ''} – ${data.ctype || ''} – `;
    sel.append('tspan').attr('class','label-meta').text(meta);
    const useKo = !!state.showGlossKo;
    const useEn = !useKo && !!state.showGloss;
    const delim = useKo || useEn ? ' | ' : ' ';
    order.forEach((t, idx) => {
      const wid = (t && (t.wid || t.id)) ? String(t.wid || t.id) : '';
      let txt = '';
      if (useKo){ txt = firstSenseKo(t && t.gloss_ko); }
      else if (useEn){ txt = norm(t && t.gloss); }
      else { txt = norm(t && t.w); }
      const cls = subj.has(wid) ? 'tok-subj' : (pred.has(wid) ? 'tok-pred' : null);
      if (idx>0) sel.append('tspan').text(delim);
      const span = sel.append('tspan');
      if (cls) span.attr('class', cls);
      span.text(txt);
    });
    // Resize rect to fit new text
    try {
      const bbox = textEl.getBBox();
      const w = Math.max(10, bbox.width + 16);
      const h = Math.max(16, bbox.height + 8);
      const rx = -w/2, ry = -h/2;
      const parent = d3.select(textEl.parentNode);
      parent.select('rect.node-rect')
        .attr('x', rx).attr('y', ry)
        .attr('width', w).attr('height', h);
    } catch(e) { /* ignore */ }
  }

  async function decorateTidyNodeLabel(textEl, data){
    try {
      const id = data && data.id; if (!id || !String(id).match(/^[0-9]+$/)) return;
      const r = await ensureSegForNode(id);
      const segs = (r && r.segs) ? r.segs : [];
      if (!segs.length) return;
      rebuildTidyTextWithSeg(textEl, data, segs);
    } catch(e) { /* ignore */ }
  }

  function renderLegend(){
    if (!legendPanel) return;
    const rows = [
      { c: 'cat-verb', label: '동사절 (일반 동사형 포함)' },
      { c: 'cat-weq',  label: '연접/연속절 (wayyiqtol/weqatal)' },
      { c: 'cat-part', label: '분사절 (Ptcp/Ptca)' },
      { c: 'cat-inf',  label: '부정사절 (InfC/InfA)' },
      { c: 'cat-imv',  label: '명령/원망/기원절 (Imv/Juss/Coh)' },
      { c: 'cat-noun', label: '명사절 (NmCl/Nom)' },
      { c: 'cat-adj',  label: '형용사절 (형용사/수식)' },
      { c: 'cat-rel',  label: '관계/수식절 (rela=Attr)' },
      { c: 'cat-pp',   label: '전치사절 (prep 우세)' },
      { c: 'cat-verbless', label: '무서술절 (동사 없음)' },
      { c: 'cat-intj', label: '감탄/감탄사 위주' },
      { c: 'cat-other',label: '기타' },
    ];
    const html = [
      '<h4>절 유형 안내</h4>',
      ...rows.map(r=> `<div class="row"><span class="swatch ${r.c}"></span><span>${r.label}</span></div>`)
    ].join('');
    legendPanel.innerHTML = html;
  }
  function escapeHtml(s){ return String(s||'').replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }
})();
  
