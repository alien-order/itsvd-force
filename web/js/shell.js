const { createApp, ref, computed, onMounted } = Vue;

createApp({
  setup() {
    const menus   = ref([]);
    const workload = ref([]);
    const activeId = ref(null);
    const uiZoom  = ref(parseFloat(localStorage.getItem('ui_zoom') || '0.9'));

    const activeMenus = computed(() => menus.value.filter(m => m.active));

    const loadMenus    = async () => { menus.value    = await eel.get_custom_menus()(); };
    const loadWorkload = async () => { workload.value = await eel.get_workload()(); };

    const getUrl = (m) => {
      if (m.source_type === 'file') return 'pages/' + m.source_value;
      if (m.source_type === 'url')  return m.source_value;
      return '';
    };

    const clickMenu = (m) => {
      const url = getUrl(m);
      if (!url) return;
      activeId.value = m.id;
      localStorage.setItem('last_menu_id', m.id);
      document.getElementById('content-frame').src = url;
    };

    const applyZoom = (z) => {
      const app = document.getElementById('app');
      app.style.zoom   = z;
      app.style.height = (100 / z) + 'vh';
      app.style.width  = (100 / z) + 'vw';
    };
    const setZoom = (delta) => {
      const next = Math.round((uiZoom.value + delta) * 100) / 100;
      uiZoom.value = Math.min(1.3, Math.max(0.65, next));
      applyZoom(uiZoom.value);
      localStorage.setItem('ui_zoom', uiZoom.value);
    };

    // Pages call this after changes that affect workload
    window.refreshSidebarWorkload = loadWorkload;
    // Pages call this to reload the menu list (e.g., after settings change)
    window.refreshSidebarMenus = loadMenus;
    // Pages call this to navigate to another page within the iframe
    window.navigateTo = (url) => {
      const frame = document.getElementById('content-frame');
      if (frame) frame.src = url;
      // Update active menu if url matches a known menu
      const matched = activeMenus.value.find(m => getUrl(m) === url || url.startsWith(getUrl(m)));
      if (matched) activeId.value = matched.id;
    };

    onMounted(async () => {
      applyZoom(uiZoom.value);
      await Promise.all([loadMenus(), loadWorkload()]);

      const lastId = parseInt(localStorage.getItem('last_menu_id'));
      const first  = lastId
        ? activeMenus.value.find(m => m.id === lastId) || activeMenus.value[0]
        : activeMenus.value[0];
      if (first) clickMenu(first);

      setInterval(loadWorkload, 30000);
    });

    return { menus, activeMenus, workload, activeId, uiZoom, setZoom, clickMenu };
  }
}).mount('#app');
