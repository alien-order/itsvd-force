// Shared utilities — loaded by all page files

const PRIORITY_LABEL  = { low:'낮음', normal:'보통', high:'높음', urgent:'긴급' };
const ASSIGN_TYPE_LABEL = { auto:'자동', forced:'지정', dedicated:'전담', skipped:'보류', manual:'수동' };
const ASSIGN_TYPE_COLOR = {
  auto:      'bg-slate-100 text-slate-600',
  forced:    'bg-orange-100 text-orange-700',
  dedicated: 'bg-blue-100 text-blue-700',
  skipped:   'bg-red-100 text-red-600',
  manual:    'bg-slate-100 text-slate-600',
};

function todayStr() { return new Date().toISOString().slice(0,10); }
function oneMonthAgo() { const d=new Date(); d.setMonth(d.getMonth()-1); return d.toISOString().slice(0,10); }

function getDday(d) {
  if (!d) return null;
  const t=new Date(); t.setHours(0,0,0,0);
  const v=new Date(d); v.setHours(0,0,0,0);
  return Math.ceil((v-t)/86400000);
}
function ddayLabel(d) {
  const n=getDday(d);
  if (n===null) return '';
  if (n<0) return `D+${Math.abs(n)}`;
  if (n===0) return 'D-Day';
  return `D-${n}`;
}
function ddayCls(d) {
  const n=getDday(d);
  if (n===null) return 'dday-normal';
  if (n<0) return 'dday-past';
  if (n===0) return 'dday-today';
  if (n<=3) return 'dday-soon';
  return 'dday-normal';
}

function renderContent(text) {
  if (!text) return '';
  if (/<[a-z][\s\S]*>/i.test(text)) return text;
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}
function formatSize(s) {
  if (s<1024) return s+'B';
  if (s<1048576) return (s/1024).toFixed(0)+'KB';
  return (s/1048576).toFixed(1)+'MB';
}

// Notify shell sidebar to refresh workload
function notifySidebar() { try { window.parent.refreshSidebarWorkload?.(); } catch(e){} }
function notifySidebarMenus() { try { window.parent.refreshSidebarMenus?.(); } catch(e){} }

// Middle panel resize (shared by all pages)
function useMpResize() {
  const mpWidth = Vue.ref(parseInt(localStorage.getItem('mp_width')||'268'));
  let _drag=false, _sx=0, _sw=0;
  const applyWidth = (w) => { document.getElementById('app').style.setProperty('--mp-width', w+'px'); };
  const startResize = (e) => {
    _drag=true; _sx=e.clientX; _sw=mpWidth.value;
    document.addEventListener('mousemove', _onMove);
    document.addEventListener('mouseup', _onUp);
    document.querySelector('.resize-handle')?.classList.add('dragging');
  };
  const _onMove = (e) => {
    if (!_drag) return;
    const w = Math.max(200, Math.min(520, _sw + e.clientX - _sx));
    mpWidth.value = w; applyWidth(w);
  };
  const _onUp = () => {
    _drag=false;
    localStorage.setItem('mp_width', mpWidth.value);
    document.removeEventListener('mousemove', _onMove);
    document.removeEventListener('mouseup', _onUp);
    document.querySelector('.resize-handle')?.classList.remove('dragging');
  };
  return { mpWidth, applyWidth, startResize };
}

// Type system helper — builds statusLabel / statusList from type_items
async function loadTypeSystem() {
  const groups = await eel.get_type_groups()();
  const pairs  = await Promise.all(groups.map(g => eel.get_type_items(g.code)().then(items=>[g.code,items])));
  const map = {};
  for (const [code,items] of pairs) map[code] = items;
  return { groups, map };
}

function buildStatusLabel(statusItems) {
  const m = { open:'접수', in_progress:'처리중', resolved:'해결', closed:'종료' };
  for (const s of statusItems) { if (s.value) m[s.value] = s.name; }
  return m;
}
function buildStatusList(statusItems) {
  return statusItems.length
    ? statusItems.map(s=>s.value).filter(Boolean)
    : ['open','in_progress','resolved','closed'];
}
