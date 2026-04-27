const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;

// Single rich-text editor instance (one visible at a time)
let _editor = null;

createApp({
  setup() {

    // ═══════════════════════════════════════════════
    // 공통
    // ═══════════════════════════════════════════════
    const activeMenu   = ref('active');
    const assignees    = ref([]);
    const workload     = ref([]);
    const nextUp       = ref(null);
    const imageSupport = ref(false);

    // ── 유형 시스템 ──
    const typeGroups = ref([]);
    const typeItems  = ref({}); // { group_code: [...items] }

    const categoryList    = computed(() => typeItems.value['category']     || []);
    const processTypeList = computed(() => typeItems.value['process_type'] || []);
    const statusItemsList = computed(() => typeItems.value['voc_status']   || []);

    const statusLabel = computed(() => {
      const m = { open: '접수', in_progress: '처리중', resolved: '해결', closed: '종료' };
      for (const s of statusItemsList.value) { if (s.value) m[s.value] = s.name; }
      return m;
    });
    const statusList = computed(() =>
      statusItemsList.value.length
        ? statusItemsList.value.map(s => s.value).filter(Boolean)
        : ['open', 'in_progress', 'resolved', 'closed']
    );

    const loadAssignees = async () => { assignees.value = await eel.get_assignees()(); };
    const loadWorkload  = async () => { workload.value  = await eel.get_workload()(); };
    const loadNextUp    = async () => { nextUp.value    = await eel.get_next_up()(); };

    // ── UI 줌 ──
    const uiZoom = ref(parseFloat(localStorage.getItem('ui_zoom') || '0.9'));
    const applyZoom = (z) => { document.getElementById('app').style.zoom = z; };
    const setZoom = (delta) => {
      const next = Math.round((uiZoom.value + delta) * 100) / 100;
      uiZoom.value = Math.min(1.3, Math.max(0.65, next));
      applyZoom(uiZoom.value);
      localStorage.setItem('ui_zoom', uiZoom.value);
    };

    const loadTypeSystem = async () => {
      const groups = await eel.get_type_groups()();
      typeGroups.value = groups;
      const pairs = await Promise.all(groups.map(g => eel.get_type_items(g.code)().then(items => [g.code, items])));
      const map = {};
      for (const [code, items] of pairs) map[code] = items;
      typeItems.value = map;
    };

    // ── 에디터 관리 ──
    const _destroyEditor = () => {
      if (_editor) { try { _editor.destroy(); } catch (e) {} _editor = null; }
    };

    const _initEditor = (containerId, content = '') => {
      _destroyEditor();
      const el = document.getElementById(containerId);
      if (!el || !window.toastui) return;
      _editor = new window.toastui.Editor({
        el,
        height: '380px',
        initialEditType: 'wysiwyg',
        usageStatistics: false,
        toolbarItems: [
          ['heading', 'bold', 'italic', 'strike'],
          ['hr', 'quote'],
          ['ul', 'ol', 'task'],
          ['link'],
          ['code', 'codeblock'],
        ],
      });
      if (content) {
        const isHtml = /<[a-z][\s\S]*>/i.test(content);
        _editor.setHTML(isHtml ? content : content.replace(/\n/g, '<br>'));
      }
    };

    const _getEditorContent = () => _editor ? _editor.getHTML() : '';

    // 내용 표시 헬퍼 (plain text ↔ HTML 자동 감지)
    const renderContent = (text) => {
      if (!text) return '';
      if (/<[a-z][\s\S]*>/i.test(text)) return text;
      return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
    };

    const priorityLabel   = { low: '낮음', normal: '보통', high: '높음', urgent: '긴급' };
    const assignTypeLabel = { auto: '자동', forced: '지정', dedicated: '전담', skipped: '보류', manual: '수동' };
    const assignTypeColor = {
      auto:      'bg-slate-100 text-slate-600',
      forced:    'bg-orange-100 text-orange-700',
      dedicated: 'bg-blue-100 text-blue-700',
      skipped:   'bg-red-100 text-red-600',
      manual:    'bg-slate-100 text-slate-600',
    };

    const todayStr    = () => new Date().toISOString().slice(0, 10);
    const oneMonthAgo = () => {
      const d = new Date();
      d.setMonth(d.getMonth() - 1);
      return d.toISOString().slice(0, 10);
    };

    const getDday = (d) => {
      if (!d) return null;
      const today = new Date(); today.setHours(0, 0, 0, 0);
      const due   = new Date(d); due.setHours(0, 0, 0, 0);
      return Math.ceil((due - today) / 86400000);
    };
    const ddayLabel = (d) => {
      const n = getDday(d);
      if (n === null) return '';
      if (n < 0)   return `D+${Math.abs(n)}`;
      if (n === 0) return 'D-Day';
      return `D-${n}`;
    };
    const ddayCls = (d) => {
      const n = getDday(d);
      if (n === null) return 'dday-normal';
      if (n < 0)   return 'dday-past';
      if (n === 0) return 'dday-today';
      if (n <= 3)  return 'dday-soon';
      return 'dday-normal';
    };

    // ═══════════════════════════════════════════════
    // VOC 상세 (active + allvoc 공용)
    // ═══════════════════════════════════════════════
    const selectedVoc       = ref(null);
    const rightTab          = ref('detail');
    const vocHistory        = ref([]);
    const vocNotes          = ref([]);
    const vocImages         = ref([]);
    const vocLinks          = ref([]);
    const reassignId        = ref('');
    const reassignNote      = ref('');
    const reassignForced    = ref(false);
    const showReassignPanel = ref(false);
    const showForcedPanel   = ref(false);
    const textSimilar       = ref([]);

    const similarVocs = computed(() => textSimilar.value.filter(v => v.id !== selectedVoc.value?.id));

    const memoDate    = ref(todayStr());
    const memoMinutes = ref('');
    const memoText    = ref('');

    const kLinkSearch   = ref('');
    const kLinkResults  = ref([]);
    const kLinkCreating = ref(false);
    const kLinkForm     = reactive({ title: '', content: '', category: '', tags: '', process_type: '' });

    let kLinkTimer = null;
    const onKLinkSearch = () => {
      clearTimeout(kLinkTimer);
      kLinkTimer = setTimeout(async () => {
        if (!kLinkSearch.value.trim()) { kLinkResults.value = []; return; }
        kLinkResults.value = await eel.get_knowledge(kLinkSearch.value, 'all')();
      }, 300);
    };

    const linkKnowledge = async (kid) => {
      if (!selectedVoc.value) return;
      await eel.link_knowledge_to_voc(kid, selectedVoc.value.id)();
      vocLinks.value = await eel.get_voc_knowledge(selectedVoc.value.id)();
    };

    const unlinkKnowledge = async (kid) => {
      if (!selectedVoc.value) return;
      await eel.unlink_knowledge_from_voc(kid, selectedVoc.value.id)();
      vocLinks.value = await eel.get_voc_knowledge(selectedVoc.value.id)();
    };

    const saveAndLinkKnowledge = async () => {
      if (!kLinkForm.title.trim()) return;
      const result = await eel.create_knowledge({ ...kLinkForm })();
      if (result.success) {
        await linkKnowledge(result.id);
        kLinkCreating.value = false;
        Object.assign(kLinkForm, { title: '', content: '', category: '', tags: '', process_type: '' });
        await loadKnowledge();
      }
    };

    const openVoc = async (v) => {
      selectedVoc.value    = { ...v };
      reassignId.value     = v.assignee_id ? String(v.assignee_id) : '';
      reassignNote.value   = '';
      reassignForced.value = false;
      showReassignPanel.value = false;
      showForcedPanel.value   = false;
      rightTab.value = 'detail';
      memoDate.value = todayStr();
      memoMinutes.value = '';
      memoText.value = '';
      kLinkSearch.value = '';
      kLinkResults.value = [];
      kLinkCreating.value = false;

      const [history, notes, images, links] = await Promise.all([
        eel.get_assignment_history(v.id)(),
        eel.get_voc_notes(v.id)(),
        eel.get_voc_images(v.id)(),
        eel.get_voc_knowledge(v.id)(),
      ]);
      vocHistory.value  = history;
      vocNotes.value    = notes;
      vocImages.value   = images;
      vocLinks.value    = links;
      textSimilar.value = await eel.get_similar_vocs(v.title, v.content, 5)();
    };

    const updateStatus = async (status) => {
      if (!selectedVoc.value) return;
      await eel.update_voc_status(selectedVoc.value.id, status)();
      selectedVoc.value.status = status;
      loadWorkload();
      if (activeMenu.value === 'active') loadActiveVocs();
      if (activeMenu.value === 'allvoc') loadAllVoc();
    };

    const doReassign = async () => {
      if (!reassignId.value || !selectedVoc.value) return;
      const aid = parseInt(reassignId.value);
      const result = await eel.reassign_voc(selectedVoc.value.id, aid, '', false)();
      if (result.success) {
        const a = assignees.value.find(x => x.id === aid);
        if (a) { selectedVoc.value.assignee_name = a.name; selectedVoc.value.assignee_id = a.id; }
        vocHistory.value = await eel.get_assignment_history(selectedVoc.value.id)();
        reassignId.value = String(aid);
        loadWorkload(); loadNextUp();
        if (activeMenu.value === 'active') loadActiveVocs();
        if (activeMenu.value === 'allvoc') loadAllVoc();
      }
    };

    const autoAssignVoc = async () => {
      if (!selectedVoc.value) return;
      let result;
      try {
        result = await eel.auto_assign_voc(selectedVoc.value.id)();
      } catch (e) {
        alert('자동 배정 오류: ' + e); return;
      }
      if (result && result.success) {
        const ai = result.assign_info;
        const a  = assignees.value.find(x => x.id === ai.assignee_id);
        if (a) { selectedVoc.value.assignee_name = a.name; selectedVoc.value.assignee_id = a.id; }
        vocHistory.value = await eel.get_assignment_history(selectedVoc.value.id)();
        showForcedPanel.value = false;
        await loadWorkload(); await loadNextUp();
        if (activeMenu.value === 'active') await loadActiveVocs();
        if (activeMenu.value === 'allvoc') await loadAllVoc();
      } else {
        alert(result ? result.error : '배정 실패');
      }
    };

    const addNote = async () => {
      if (!memoText.value.trim() || !selectedVoc.value) return;
      const result = await eel.add_voc_note(
        selectedVoc.value.id, memoText.value,
        memoDate.value, parseInt(memoMinutes.value) || 0
      )();
      if (result.success) {
        memoText.value = ''; memoMinutes.value = ''; memoDate.value = todayStr();
        vocNotes.value = await eel.get_voc_notes(selectedVoc.value.id)();
      }
    };

    // ═══════════════════════════════════════════════
    // 1. 처리중인 VOC (active)
    // ═══════════════════════════════════════════════
    const activeVocList    = ref([]);
    const activeAssigneeId = ref('all');
    const showFetchForm    = ref(false);
    const vocFetching      = ref(false);
    const fetchError       = ref('');
    const vocNumInput      = ref('');
    const previewData      = ref(null);
    const submitting       = ref(false);
    const lastCreated      = ref(null);
    const lastAssignInfo   = ref(null);
    const forcedAssigneeId = ref('');
    const syncing          = ref(false);
    const syncResult       = ref(null);
    const reportText       = ref('');
    const reportCopied     = ref(false);

    const loadActiveVocs = async () => {
      activeVocList.value = await eel.get_vocs('active', null, activeAssigneeId.value)();
    };

    const fetchVoc = async () => {
      if (!vocNumInput.value.trim()) return;
      vocFetching.value = true; fetchError.value = '';
      const result = await eel.fetch_voc_data(vocNumInput.value.trim())();
      vocFetching.value = false;
      if (result.success) {
        previewData.value = { ...result.data, category: '', priority: 'normal' };
      } else {
        fetchError.value = result.error;
      }
    };

    const submitVoc = async () => {
      if (!previewData.value?.title?.trim()) return;
      submitting.value = true;
      const payload = { ...previewData.value, images: previewData.value.images || [] };
      if (forcedAssigneeId.value) payload.forced_assignee_id = parseInt(forcedAssigneeId.value);
      const result = await eel.create_voc(payload)();
      submitting.value = false;
      if (result.success) {
        lastCreated.value    = result.voc;
        lastAssignInfo.value = result.assign_info;
        showFetchForm.value  = false;
        previewData.value    = null;
        vocNumInput.value    = '';
        forcedAssigneeId.value = '';
        await loadActiveVocs();
        await loadWorkload();
        await loadNextUp();
        const found = activeVocList.value.find(v => v.id === result.voc.id);
        if (found) openVoc(found);
      } else {
        alert(result.error);
      }
    };

    const generateReport = async () => { reportText.value = await eel.get_daily_report()(); };
    const copyReport = async () => {
      if (!reportText.value) await generateReport();
      await navigator.clipboard.writeText(reportText.value);
      reportCopied.value = true;
      setTimeout(() => { reportCopied.value = false; }, 2000);
    };

    const syncStatuses = async () => {
      syncing.value = true; syncResult.value = null;
      const result = await eel.sync_voc_statuses()();
      syncing.value = false; syncResult.value = result;
      if (result.success && result.updated?.length > 0) {
        await loadActiveVocs(); await loadWorkload();
        if (selectedVoc.value) {
          const fresh = activeVocList.value.find(v => v.id === selectedVoc.value.id);
          if (fresh) selectedVoc.value = { ...fresh };
        }
      }
    };

    // ═══════════════════════════════════════════════
    // 2. 전체 VOC (allvoc)
    // ═══════════════════════════════════════════════
    const allVocList     = ref([]);
    const allVocSearch   = ref('');
    const allVocDateFrom = ref(oneMonthAgo());
    const allVocDateTo   = ref(todayStr());
    const allVocStatus   = ref('all');
    const allVocAssignee = ref('all');
    const allVocCategory = ref('all');

    const loadAllVoc = async () => {
      allVocList.value = await eel.get_vocs(
        allVocStatus.value,
        allVocSearch.value || null,
        allVocAssignee.value,
        allVocCategory.value,
        allVocDateFrom.value || null,
        allVocDateTo.value   || null
      )();
    };

    let allVocSearchTimer = null;
    const onAllVocSearch = () => { clearTimeout(allVocSearchTimer); allVocSearchTimer = setTimeout(loadAllVoc, 350); };

    // ═══════════════════════════════════════════════
    // 3. VOC 통계 (stats)
    // ═══════════════════════════════════════════════
    const statsMode    = ref('monthly');
    const statsData    = ref([]);
    const selectedStat = ref(null);

    const loadStats = async () => {
      selectedStat.value = null;
      if (statsMode.value === 'assignee') {
        statsData.value = workload.value;
      } else {
        statsData.value = await eel.get_voc_stats(statsMode.value)();
      }
    };

    const formatPeriod = (period, mode) => {
      if (!period) return '';
      if (mode === 'monthly') {
        const [y, m] = period.split('-');
        return `${y}년 ${m}월`;
      }
      const parts = period.split('-W');
      return `${parts[0]}년 ${parseInt(parts[1])}주차`;
    };

    const periodToDateRange = (period, mode) => {
      if (mode === 'monthly') {
        const [y, m] = period.split('-');
        const from    = `${y}-${m}-01`;
        const lastDay = new Date(parseInt(y), parseInt(m), 0).getDate();
        const to      = `${y}-${m}-${String(lastDay).padStart(2, '0')}`;
        return { from, to };
      }
      const [y, w] = period.split('-W');
      const jan4   = new Date(parseInt(y), 0, 4);
      const dow    = jan4.getDay() || 7;
      const weekStart = new Date(jan4.getTime() - (dow - 1) * 86400000 + (parseInt(w) - 1) * 7 * 86400000);
      const weekEnd   = new Date(weekStart.getTime() + 6 * 86400000);
      const fmt = d => d.toISOString().slice(0, 10);
      return { from: fmt(weekStart), to: fmt(weekEnd) };
    };

    const goToAllVocFiltered = (period, category) => {
      if (period) {
        const range = periodToDateRange(period, statsMode.value);
        allVocDateFrom.value = range.from;
        allVocDateTo.value   = range.to;
      } else {
        allVocDateFrom.value = '';
        allVocDateTo.value   = '';
      }
      allVocCategory.value = category || 'all';
      allVocStatus.value   = 'all';
      allVocAssignee.value = 'all';
      allVocSearch.value   = '';
      switchMenu('allvoc');
    };

    const goToActiveFiltered = async (aid) => {
      activeAssigneeId.value = String(aid);
      await switchMenu('active');
    };

    // ═══════════════════════════════════════════════
    // 4. 레퍼런스 (knowledge)
    // ═══════════════════════════════════════════════
    const knowledgeList       = ref([]);
    const knowledgeSearch     = ref('');
    const knowledgeCat        = ref('all');
    const knowledgeProcessType = ref('all');
    const selectedKnowledge   = ref(null);
    const kEdit               = ref(false);
    const kRightTab           = ref('content');
    const kForm               = reactive({ title: '', content: '', category: '', tags: '', process_type: '' });
    const kSaving             = ref(false);
    const kVocs               = ref([]);

    const loadKnowledge = async () => {
      knowledgeList.value = await eel.get_knowledge(knowledgeSearch.value || null, knowledgeCat.value, knowledgeProcessType.value)();
    };

    let kSearchTimer = null;
    const onKSearch = () => { clearTimeout(kSearchTimer); kSearchTimer = setTimeout(loadKnowledge, 350); };

    const openKnowledge = async (item) => {
      selectedKnowledge.value = { ...item };
      kEdit.value    = false;
      kRightTab.value = 'content';
      kVocs.value    = await eel.get_knowledge_vocs(item.id)();
    };

    const newKnowledge  = () => { selectedKnowledge.value = null; Object.assign(kForm, { title: '', content: '', category: '', tags: '', process_type: '' }); kEdit.value = true; };
    const editKnowledge = () => { Object.assign(kForm, selectedKnowledge.value); kEdit.value = true; };

    const saveKnowledge = async () => {
      if (_editor) kForm.content = _getEditorContent();
      kSaving.value = true;
      let result;
      if (selectedKnowledge.value?.id) {
        result = await eel.update_knowledge(selectedKnowledge.value.id, { ...kForm })();
      } else {
        result = await eel.create_knowledge({ ...kForm })();
      }
      kSaving.value = false;
      if (result.success) {
        await loadKnowledge();
        const id = result.id || selectedKnowledge.value?.id;
        if (id) {
          const found = knowledgeList.value.find(k => k.id === id);
          await openKnowledge(found || { id });
        }
        kEdit.value = false;
      }
    };

    const deleteKnowledge = async (kid) => {
      if (!confirm('삭제하시겠습니까?')) return;
      await eel.delete_knowledge(kid)();
      selectedKnowledge.value = null; kVocs.value = [];
      await loadKnowledge();
    };

    const goToKnowledge = async (kid) => {
      await switchMenu('knowledge');
      const item = knowledgeList.value.find(k => k.id === kid);
      if (item) {
        await openKnowledge(item);
      } else {
        const one = await eel.get_knowledge_one(kid)();
        if (one) await openKnowledge(one);
      }
    };

    const goToVocFromKnowledge = async (v) => {
      allVocDateFrom.value = '';
      allVocDateTo.value   = '';
      allVocStatus.value   = 'all';
      allVocAssignee.value = 'all';
      allVocCategory.value = 'all';
      allVocSearch.value   = '';
      await switchMenu('allvoc');
      const found = allVocList.value.find(x => x.id === v.id);
      if (found) openVoc(found);
    };

    // ═══════════════════════════════════════════════
    // 5. 공유문서 (board)
    // ═══════════════════════════════════════════════
    const boardList     = ref([]);
    const boardSearch   = ref('');
    const boardCat      = ref('all');
    const boardCats     = ref([]);
    const selectedPost  = ref(null);
    const postEdit      = ref(false);
    const postForm      = reactive({ title: '', content: '', category: '' });
    const postSaving    = ref(false);
    const fileUploading = ref(false);

    const loadBoard = async () => {
      boardList.value = await eel.get_board_posts(boardSearch.value, boardCat.value)();
      boardCats.value = await eel.get_board_categories()();
    };

    let bSearchTimer = null;
    const onBSearch = () => { clearTimeout(bSearchTimer); bSearchTimer = setTimeout(loadBoard, 350); };

    const openPost  = async (item) => { selectedPost.value = await eel.get_board_post(item.id)(); postEdit.value = false; };
    const newPost   = () => { selectedPost.value = null; Object.assign(postForm, { title: '', content: '', category: '' }); postEdit.value = true; };
    const editPost  = () => { Object.assign(postForm, selectedPost.value); postEdit.value = true; };

    const savePost = async () => {
      if (_editor) postForm.content = _getEditorContent();
      postSaving.value = true;
      let result;
      if (selectedPost.value?.id) {
        result = await eel.update_board_post(selectedPost.value.id, { ...postForm })();
        if (result.success) selectedPost.value = await eel.get_board_post(selectedPost.value.id)();
      } else {
        result = await eel.create_board_post({ ...postForm })();
        if (result.success) selectedPost.value = await eel.get_board_post(result.id)();
      }
      postSaving.value = false;
      if (result.success) { await loadBoard(); postEdit.value = false; }
    };

    const deletePost = async (id) => {
      if (!confirm('삭제하시겠습니까?')) return;
      await eel.delete_board_post(id)();
      selectedPost.value = null; await loadBoard();
    };

    const handleFileSelect = async (e) => {
      if (!selectedPost.value?.id) return;
      fileUploading.value = true;
      for (const file of e.target.files) {
        await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = async (ev) => {
            await eel.upload_board_file(selectedPost.value.id, file.name, ev.target.result.split(',')[1])();
            resolve();
          };
          reader.readAsDataURL(file);
        });
      }
      selectedPost.value = await eel.get_board_post(selectedPost.value.id)();
      fileUploading.value = false; e.target.value = '';
    };

    const deleteFile = async (fileId) => {
      await eel.delete_board_file(fileId)();
      selectedPost.value = await eel.get_board_post(selectedPost.value.id)();
    };

    const formatSize = (s) => {
      if (s < 1024)    return s + 'B';
      if (s < 1048576) return (s / 1024).toFixed(0) + 'KB';
      return (s / 1048576).toFixed(1) + 'MB';
    };

    // ═══════════════════════════════════════════════
    // 6. 설정 (settings)
    // ═══════════════════════════════════════════════
    const settingsTab = ref('members');

    // 휴가 관리
    const vacations        = ref([]);
    const newVacAssigneeId = ref('');
    const newVacDate       = ref(todayStr());
    const newVacType       = ref('연차');

    const _nowYM = () => {
      const n = new Date();
      return { y: String(n.getFullYear()), m: String(n.getMonth() + 1).padStart(2, '0') };
    };
    const { y: _initY, m: _initM } = _nowYM();
    const vacHistoryYear  = ref(_initY);
    const vacHistoryMonth = ref(_initM);

    const vacHistoryYears = computed(() => {
      const s = new Set(
        vacations.value.filter(v => v.is_past && v.vacation_date)
          .map(v => v.vacation_date.substring(0, 4))
      );
      return [...s].sort((a, b) => b.localeCompare(a));
    });

    const vacHistoryFiltered = computed(() =>
      vacations.value.filter(v =>
        v.is_past && v.vacation_date &&
        v.vacation_date.startsWith(vacHistoryYear.value + '-' + vacHistoryMonth.value)
      )
    );

    const loadVacations = async () => { vacations.value = await eel.get_vacations()(); };
    const addVacation = async () => {
      if (!newVacAssigneeId.value || !newVacDate.value) return;
      const result = await eel.add_vacation(parseInt(newVacAssigneeId.value), newVacDate.value, newVacType.value)();
      if (result.success) {
        newVacAssigneeId.value = ''; newVacDate.value = todayStr(); newVacType.value = '연차';
        await loadVacations(); await loadWorkload(); await loadNextUp();
      } else { alert(result.error); }
    };
    const deleteVacation = async (vid) => {
      await eel.delete_vacation(vid)();
      await loadVacations(); await loadWorkload(); await loadNextUp();
    };

    // 유형 관리
    const PROTECTED_GROUPS  = ['category', 'process_type', 'voc_status'];
    const selectedGroupCode = ref('');
    const newGroupCode      = ref('');
    const newGroupLabel     = ref('');
    const groupError        = ref('');
    const newItemName       = ref('');
    const newItemValue      = ref('');
    const itemError         = ref('');

    const currentGroup      = computed(() => typeGroups.value.find(g => g.code === selectedGroupCode.value));
    const currentGroupItems = computed(() => typeItems.value[selectedGroupCode.value] || []);

    const selectGroup = (code) => {
      selectedGroupCode.value = code;
      newItemName.value = '';
      newItemValue.value = '';
      itemError.value = '';
    };

    const addTypeGroup = async () => {
      groupError.value = '';
      const result = await eel.add_type_group(newGroupCode.value, newGroupLabel.value)();
      if (result.success) {
        newGroupCode.value = ''; newGroupLabel.value = '';
        await loadTypeSystem();
      } else { groupError.value = result.error; }
    };

    const deleteTypeGroup = async (id, code) => {
      if (PROTECTED_GROUPS.includes(code)) { alert('기본 그룹은 삭제할 수 없습니다.'); return; }
      if (!confirm('그룹과 모든 항목을 삭제하시겠습니까?')) return;
      const result = await eel.delete_type_group(id)();
      if (result.success) {
        if (selectedGroupCode.value === code) selectedGroupCode.value = '';
        await loadTypeSystem();
      } else { alert(result.error); }
    };

    const moveTypeGroup = async (idx, dir) => {
      const list   = typeGroups.value;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= list.length) return;
      const orderList = list.map((g, i) => ({ id: g.id, sort_order: i }));
      const tmp = orderList[idx].sort_order;
      orderList[idx].sort_order   = orderList[newIdx].sort_order;
      orderList[newIdx].sort_order = tmp;
      await eel.update_type_group_order(orderList)();
      await loadTypeSystem();
    };

    const addTypeItem = async () => {
      itemError.value = '';
      if (!selectedGroupCode.value || !newItemName.value.trim()) return;
      const result = await eel.add_type_item(selectedGroupCode.value, newItemName.value, newItemValue.value)();
      if (result.success) {
        newItemName.value = ''; newItemValue.value = '';
        await loadTypeSystem();
      } else { itemError.value = result.error; }
    };

    const deleteTypeItem = async (id) => {
      if (!confirm('항목을 삭제하시겠습니까?')) return;
      await eel.delete_type_item(id)();
      await loadTypeSystem();
    };

    const moveTypeItem = async (idx, dir) => {
      const list   = currentGroupItems.value;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= list.length) return;
      const orderList = list.map((it, i) => ({ id: it.id, sort_order: i }));
      const tmp = orderList[idx].sort_order;
      orderList[idx].sort_order   = orderList[newIdx].sort_order;
      orderList[newIdx].sort_order = tmp;
      await eel.update_type_item_order(orderList)();
      await loadTypeSystem();
    };

    // ─────────────────────────────────────────────
    const config = reactive({
      fetch_method: 'static',
      url_pattern: '', dynamic: false,
      xpath_wait_seconds: 3,
      xpath_selectors: { voc_number: '', title: '', content: '', requester: '', due_date: '', status: '', images: '' },
      api_url_pattern: '',
      api_cookies: [],
      api_field_map: { voc_number: '', title: '', content: '', requester: '', due_date: '', status: '' },
      selectors: { voc_number: '', title: '', content: '', requester: '', due_date: '', status: '', images: '' },
    });
    const configSaved       = ref(false);
    const testNum           = ref('');
    const testLoading       = ref(false);
    const testResult        = ref(null);
    const newMember         = ref('');
    const memberError       = ref('');
    const assignmentRules   = ref([]);
    const newRuleCategory   = ref('');
    const newRuleAssigneeId = ref('');
    const newRuleNote       = ref('');
    const newCookieKey      = ref('');
    const newCookieVal      = ref('');

    const fetchMethods = [
      { key: 'static',     label: '정적 HTTP',  desc: 'CSS 셀렉터' },
      { key: 'api_cookie', label: '쿠키 API',   desc: 'JSON 응답' },
      { key: 'xpath',      label: 'XPath 대기', desc: '동적 페이지' },
    ];

    const loadConfig = async () => {
      const d = await eel.get_config()();
      config.fetch_method       = d.fetch_method || 'static';
      config.url_pattern        = d.url_pattern || '';
      config.dynamic            = d.dynamic || false;
      config.xpath_wait_seconds = d.xpath_wait_seconds ?? 3;
      config.api_url_pattern    = d.api_url_pattern || '';
      config.api_cookies        = (d.api_cookies || []).map(c => ({ ...c }));
      Object.assign(config.api_field_map,   d.api_field_map   || {});
      Object.assign(config.selectors,       d.selectors       || {});
      Object.assign(config.xpath_selectors, d.xpath_selectors || {});
    };

    const saveConfig = async () => {
      const payload = {
        ...config,
        selectors:       { ...config.selectors },
        xpath_selectors: { ...config.xpath_selectors },
        api_field_map:   { ...config.api_field_map },
        api_cookies:     config.api_cookies.map(c => ({ ...c })),
      };
      await eel.save_config(payload)();
      configSaved.value = true; setTimeout(() => configSaved.value = false, 2000);
    };

    const addApiCookie = () => {
      if (!newCookieKey.value.trim()) return;
      config.api_cookies.push({ key: newCookieKey.value.trim(), value: newCookieVal.value });
      newCookieKey.value = ''; newCookieVal.value = '';
    };
    const removeApiCookie = (idx) => { config.api_cookies.splice(idx, 1); };

    const testFetch = async () => {
      if (!testNum.value.trim()) return;
      testLoading.value = true; testResult.value = null;
      testResult.value  = await eel.fetch_voc_data(testNum.value.trim())();
      testLoading.value = false;
    };

    const addMember = async () => {
      memberError.value = '';
      const result = await eel.add_assignee(newMember.value)();
      if (result.success) { newMember.value = ''; await loadAssignees(); await loadWorkload(); }
      else memberError.value = result.error;
    };

    const toggleMember = async (id) => {
      await eel.toggle_assignee(id)(); await loadAssignees(); await loadWorkload();
    };

    const moveMember = async (idx, dir) => {
      const list   = assignees.value;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= list.length) return;
      const orderList = list.map((a, i) => ({ id: a.id, turn_order: i }));
      const tmp = orderList[idx].turn_order;
      orderList[idx].turn_order   = orderList[newIdx].turn_order;
      orderList[newIdx].turn_order = tmp;
      await eel.update_turn_order(orderList)();
      await loadAssignees(); await loadNextUp();
    };

    const loadAssignmentRules = async () => { assignmentRules.value = await eel.get_assignment_rules()(); };

    const saveRule = async () => {
      if (!newRuleCategory.value.trim() || !newRuleAssigneeId.value) return;
      const result = await eel.save_assignment_rule(newRuleCategory.value.trim(), parseInt(newRuleAssigneeId.value), newRuleNote.value)();
      if (result.success) {
        newRuleCategory.value = ''; newRuleAssigneeId.value = ''; newRuleNote.value = '';
        await loadAssignmentRules(); await loadNextUp();
      }
    };

    const deleteRule = async (id) => {
      if (!confirm('규칙을 삭제하시겠습니까?')) return;
      await eel.delete_assignment_rule(id)();
      await loadAssignmentRules(); await loadNextUp();
    };

    const selectorFields = [
      { key: 'voc_number', label: 'VOC 번호' },
      { key: 'title',      label: '제목' },
      { key: 'content',    label: '내용' },
      { key: 'requester',  label: '요청자' },
      { key: 'due_date',   label: '완료요청일' },
      { key: 'status',     label: '처리상태', hint: '동기화용' },
      { key: 'images',     label: '이미지 범위', hint: '비워두면 content 영역 전체' },
    ];

    // ── 데이터 Sync 모달 ──
    const syncModalOpen    = ref(false);
    const syncModalItems   = ref([]);
    const syncModalCurrent = ref(0);
    const syncModalRunning = ref(false);

    const openSyncModal = async () => {
      const vocs = await eel.get_vocs('in_progress')();
      syncModalItems.value   = vocs.map(v => ({
        id: v.id, voc_number: v.voc_number || ('#' + v.id),
        title: v.title, status: 'pending', error: '',
      }));
      syncModalCurrent.value = 0;
      syncModalRunning.value = false;
      syncModalOpen.value    = true;
    };

    const runBatchSync = async () => {
      if (syncModalRunning.value) return;
      syncModalRunning.value = true;
      syncModalCurrent.value = 0;
      let done = 0;
      for (let i = 0; i < syncModalItems.value.length; i++) {
        if (syncModalItems.value[i].status !== 'pending') continue;
        syncModalItems.value[i] = { ...syncModalItems.value[i], status: 'syncing' };
        const result = await eel.sync_single_voc(syncModalItems.value[i].id)();
        done++;
        syncModalCurrent.value = done;
        if (result.success) {
          syncModalItems.value[i] = { ...syncModalItems.value[i], status: 'done', error: '' };
        } else {
          syncModalItems.value[i] = { ...syncModalItems.value[i], status: 'failed', error: result.error || '오류' };
        }
      }
      syncModalRunning.value = false;
      await loadActiveVocs();
      if (selectedVoc.value) {
        const fresh = activeVocList.value.find(v => v.id === selectedVoc.value.id);
        if (fresh) selectedVoc.value = fresh;
      }
    };

    const resetSyncModal = () => {
      syncModalItems.value = syncModalItems.value.map(i => ({ ...i, status: 'pending', error: '' }));
      syncModalCurrent.value = 0;
    };

    const closeSyncModal = () => {
      if (syncModalRunning.value) return;
      syncModalOpen.value = false;
    };

    // ── 배치 처리 모달 ──
    const _nowDate = () => {
      const n = new Date();
      return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}-01`;
    };
    const batchFromDate    = ref(_nowDate());
    const batchModalOpen   = ref(false);
    const batchModalItems  = ref([]);
    const batchModalCurrent = ref(0);
    const batchModalRunning = ref(false);

    const openBatchModal = async () => {
      if (!batchFromDate.value) return;
      const fromStr = batchFromDate.value.replace(/-/g, '');
      const all = await eel.get_vocs('all')();
      const filtered = all.filter(v => {
        const prefix = (v.voc_number || '').substring(0, 8);
        return /^\d{8}$/.test(prefix) && prefix >= fromStr;
      }).sort((a, b) => (a.voc_number || '').localeCompare(b.voc_number || ''));
      if (filtered.length === 0) {
        alert(`${batchFromDate.value} 이후 VOC 번호(8자리 날짜 prefix)가 없습니다.`);
        return;
      }
      batchModalItems.value   = filtered.map(v => ({
        id: v.id, voc_number: v.voc_number || ('#' + v.id),
        title: v.title, status: 'pending', error: '',
      }));
      batchModalCurrent.value = 0;
      batchModalRunning.value = false;
      batchModalOpen.value    = true;
    };

    const runBatchModal = async () => {
      if (batchModalRunning.value) return;
      batchModalRunning.value = true;
      batchModalCurrent.value = 0;
      let done = 0;
      for (let i = 0; i < batchModalItems.value.length; i++) {
        if (batchModalItems.value[i].status !== 'pending') continue;
        batchModalItems.value[i] = { ...batchModalItems.value[i], status: 'syncing' };
        const result = await eel.sync_single_voc(batchModalItems.value[i].id)();
        done++;
        batchModalCurrent.value = done;
        batchModalItems.value[i] = result.success
          ? { ...batchModalItems.value[i], status: 'done', error: '' }
          : { ...batchModalItems.value[i], status: 'failed', error: result.error || '오류' };
      }
      batchModalRunning.value = false;
    };

    const resetBatchModal = () => {
      batchModalItems.value   = batchModalItems.value.map(i => ({ ...i, status: 'pending', error: '' }));
      batchModalCurrent.value = 0;
    };

    const closeBatchModal = () => {
      if (batchModalRunning.value) return;
      batchModalOpen.value = false;
    };

    // ── 에디터 watch (DOM이 갱신된 후 초기화) ──
    watch(kEdit, async (val) => {
      if (val) { await nextTick(); _initEditor('k-editor-container', kForm.content); }
      else      { _destroyEditor(); }
    });
    watch(postEdit, async (val) => {
      if (val) { await nextTick(); _initEditor('b-editor-container', postForm.content); }
      else      { _destroyEditor(); }
    });

    // ═══════════════════════════════════════════════
    // 메뉴 전환
    // ═══════════════════════════════════════════════
    const switchMenu = async (menu) => {
      _destroyEditor();
      activeMenu.value  = menu;
      selectedVoc.value = null;
      if (menu === 'active')    { await Promise.all([loadActiveVocs(), loadWorkload(), loadNextUp(), generateReport()]); }
      if (menu === 'allvoc')    { await loadTypeSystem(); await loadAllVoc(); }
      if (menu === 'stats')     { await loadWorkload(); await loadStats(); }
      if (menu === 'knowledge') { await loadTypeSystem(); await loadKnowledge(); }
      if (menu === 'board')     { await loadBoard(); }
      if (menu === 'settings')  {
        await Promise.all([loadConfig(), loadAssignmentRules(), loadVacations(), loadTypeSystem()]);
        if (!settingsTab.value) settingsTab.value = 'members';
      }
    };

    onMounted(async () => {
      applyZoom(uiZoom.value);
      imageSupport.value = await eel.check_image_support()();
      await Promise.all([loadAssignees(), loadWorkload(), loadActiveVocs(), loadNextUp(), generateReport(), loadTypeSystem()]);
    });

    return {
      activeMenu, switchMenu, assignees, workload, nextUp, imageSupport,
      uiZoom, setZoom,
      typeGroups, typeItems, categoryList, processTypeList, statusItemsList,
      priorityLabel, statusLabel, statusList, assignTypeLabel, assignTypeColor,
      todayStr, getDday, ddayLabel, ddayCls,
      // VOC 상세 공용
      selectedVoc, rightTab, vocHistory, vocNotes, vocImages, vocLinks,
      reassignId, reassignNote, reassignForced, showReassignPanel, showForcedPanel,
      textSimilar, similarVocs,
      memoDate, memoMinutes, memoText,
      kLinkSearch, kLinkResults, kLinkCreating, kLinkForm,
      openVoc, updateStatus, doReassign, autoAssignVoc, addNote,
      onKLinkSearch, linkKnowledge, unlinkKnowledge, saveAndLinkKnowledge,
      // 처리중인 VOC
      activeVocList, activeAssigneeId, showFetchForm,
      vocFetching, fetchError, vocNumInput, previewData,
      submitting, lastCreated, lastAssignInfo, forcedAssigneeId,
      syncing, syncResult, reportText, reportCopied,
      loadActiveVocs, fetchVoc, submitVoc, copyReport, syncStatuses, generateReport,
      // 전체 VOC
      allVocList, allVocSearch, allVocDateFrom, allVocDateTo,
      allVocStatus, allVocAssignee, allVocCategory,
      loadAllVoc, onAllVocSearch,
      // 통계
      statsMode, statsData, selectedStat,
      loadStats, formatPeriod, goToAllVocFiltered, goToActiveFiltered,
      // 레퍼런스
      knowledgeList, knowledgeSearch, knowledgeCat, knowledgeProcessType,
      selectedKnowledge, kEdit, kRightTab, kForm, kSaving, kVocs,
      renderContent,
      loadKnowledge, onKSearch, openKnowledge, newKnowledge, editKnowledge,
      saveKnowledge, deleteKnowledge, goToKnowledge, goToVocFromKnowledge,
      // 공유문서
      boardList, boardSearch, boardCat, boardCats,
      selectedPost, postEdit, postForm, postSaving, fileUploading,
      loadBoard, onBSearch, openPost, newPost, editPost, savePost, deletePost,
      handleFileSelect, deleteFile, formatSize,
      // 설정
      settingsTab,
      config, configSaved, testNum, testLoading, testResult,
      fetchMethods, newCookieKey, newCookieVal, addApiCookie, removeApiCookie,
      newMember, memberError, assignmentRules, newRuleCategory, newRuleAssigneeId, newRuleNote,
      loadConfig, saveConfig, testFetch, addMember, toggleMember, moveMember,
      loadAssignmentRules, saveRule, deleteRule, selectorFields,
      // 데이터 Sync 모달
      syncModalOpen, syncModalItems, syncModalCurrent, syncModalRunning,
      openSyncModal, runBatchSync, resetSyncModal, closeSyncModal,
      // 휴가
      vacations, newVacAssigneeId, newVacDate, newVacType,
      vacHistoryYear, vacHistoryMonth, vacHistoryYears, vacHistoryFiltered,
      loadVacations, addVacation, deleteVacation,
      // 배치 처리
      batchFromDate, batchModalOpen, batchModalItems, batchModalCurrent, batchModalRunning,
      openBatchModal, runBatchModal, resetBatchModal, closeBatchModal,
      // 유형 관리
      PROTECTED_GROUPS, selectedGroupCode, newGroupCode, newGroupLabel, groupError,
      newItemName, newItemValue, itemError,
      currentGroup, currentGroupItems,
      selectGroup, addTypeGroup, deleteTypeGroup, moveTypeGroup,
      addTypeItem, deleteTypeItem, moveTypeItem,
    };
  }
}).mount('#app');
