(function(){
  const LS_PREFIX = 'cttViewer:';
  function setPref(k,v){ try { localStorage.setItem(LS_PREFIX+k, String(v)); } catch(e){} }
  function getPref(k,d){ try { const v=localStorage.getItem(LS_PREFIX+k); return (v===null||v===undefined)? d : v; } catch(e){ return d; } }

  function applyTheme(pref){
    const root = document.documentElement;
    const mql = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
    function setDark(on){ try { if (on) root.setAttribute('data-theme','dark'); else root.removeAttribute('data-theme'); } catch(e){} }
    if (pref === 'dark'){ setDark(true); return 'dark'; }
    if (pref === 'light'){ setDark(false); return 'light'; }
    // auto
    const dark = !!(mql && mql.matches);
    setDark(dark);
    return dark ? 'dark' : 'light';
  }

  function init(selectId){
    const sel = document.getElementById(selectId);
    const saved = getPref('theme','auto');
    if (sel){ sel.value = saved; }
    applyTheme(saved);
    if (sel){
      sel.addEventListener('change', ()=>{
        const val = sel.value || 'auto';
        setPref('theme', val);
        applyTheme(val);
      });
    }
    // watch OS theme only when auto
    try{
      const mql = window.matchMedia('(prefers-color-scheme: dark)');
      if (mql && mql.addEventListener){
        mql.addEventListener('change', ()=>{ if (getPref('theme','auto')==='auto') applyTheme('auto'); });
      }
    } catch(e){}
  }

  window.Theme = { apply: applyTheme, init };
})();

