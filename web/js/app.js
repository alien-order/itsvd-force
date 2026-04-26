const { createApp, ref, reactive, computed, onMounted } = Vue;

createApp({
  setup() {

    // ═══════════════════════════════════════════════
    // 공통
    // ═══════════════════════════════════════════════
    // Menu: active | allvoc | stats | knowledge | board | settings
    const activeMenu   = ref('active');
    const assignees    = ref([]);
    const workload     = ref([]);
    const nextUp       = ref(null);
    const imageSupport = ref(false);
    const categoryList = ref([]);

    const loadAssignees  = async () => { assignees.value  = await eel.get_assignees()(); };
    const loadWorkload   = async () => { workload.value   = await eel.get_workload()(); };
    const loadNextUp     = async () => { nextUp.value     = await eel.get_next_up()(); };
    const loadCategoryList = async () => { categoryList.value = await eel.get_category_list()(); };

    const priorityLabel   = { low:'낮음', normal:'보통', high:'높음', urgent:'긴급' };
    const statusLabel     = { open:'접수', in_progress:'처리중', resolved:'해결', closed:'종료' };
    const statusList      = ['open','in_progress','resolved','closed'];
    const assignTypeLabel = { auto:'자동', forced:'지정', dedicated:'전담', skipped:'보류', manual:'수동' };
    const assignTypeColor = {
      auto:'bg-slate-100 text-slate-600', forced:'bg-orange-100 text-orange-700',
      dedicated:'bg-blue-100 text-blue-700', skipped:'bg-red-100 text-red-600',
      manual:'bg-slate-100 text-slate-600',
    };

    const todayStr = () => new Date().toISOString().slice(0, 10);

    const getDday = (d) => {
      if (!d) return null;
      const today = new Date(); today.setHours(0,0,0,0);
      const due   = new Date(d); due.setHours(0,0,0,0);
      return Math.ceil((due - today) / 86400000);
    };
    const ddayLabel = (d) => {
      const n = getDday(d);
      if (n === null) return '';
      if (n < 0)  return `D+${Math.abs(n)}`;
      if (n === 0) return 'D-Day';
      return `D-${n}`;
    };
    const ddayCls = (d) => {
      const n = getDday(d);
      if (n === null) return 'dday-normal';
      if (n < 0)  return 'dday-past';
      if (n === 0) return 'dday-today';
      if (n <= 3) return 'dday-soon';
      return 'dday-normal';
    };

    // ═══════════════════════════════════════════════
    // VOC 상세 (active + allvoc 공용)
    // ═══════════════════════════════════════════════
    const selectedVoc       = ref(null);
    const rightTab          = ref('detail'); // detail | refTab | memo | similar
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

    const similarVocs = computed(() => {
      return textSimilar.value.filter(v => v.id !== selectedVoc.value?.id);
    });

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
      vocHistory.value = history;
      vocNotes.value   = notes;
      vocImages.value  = images;
      vocLinks.value   = links;
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
        const a = assignees.value.find(x => x.id === ai.assignee_id);
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
      const result = await eel.get_vocs('active', null, activeAssigneeId.value)();
      activeVocList.value = result;
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
    const allVocList      = ref([]);
    const allVocSearch    = ref('');
    const allVocDateFrom  = ref('');
    const allVocDateTo    = ref('');
    const allVocStatus    = ref('all');
    const allVocAssignee  = ref('all');
    const allVocCategory  = ref('all');

    const loadAllVoc = async () => {
      allVocList.value = await eel.get_vocs(
        allVocStatus.value,
        allVocSearch.value || null,
        allVocAssignee.value,
        allVocCategory.value,
        allVocDateFrom.value || null,
        allVocDateTo.value || null
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
        const from = `${y}-${m}-01`;
        const lastDay = new Date(parseInt(y), parseInt(m), 0).getDate();
        const to = `${y}-${m}-${String(lastDay).padStart(2, '0')}`;
        return { from, to };
      }
      // weekly: period = 'YYYY-WWW'
      const [y, w] = period.split('-W');
      const jan4 = new Date(parseInt(y), 0, 4);
      const dow = jan4.getDay() || 7;
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
    const knowledgeList      = ref([]);
    const knowledgeSearch    = ref('');
    const knowledgeCat       = ref('all');
    const knowledgeProcessType = ref('all');
    const selectedKnowledge  = ref(null);
    const kEdit              = ref(false);
    const kRightTab          = ref('content'); // content | vocs
    const kForm              = reactive({ title: '', content: '', category: '', tags: '', process_type: '' });
    const kSaving            = ref(false);
    const kVocs              = ref([]);

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

    const newKnowledge  = () => { selectedKnowledge.value = null; Object.assign(kForm, { title:'', content:'', category:'', tags:'', process_type:'' }); kEdit.value = true; };
    const editKnowledge = () => { Object.assign(kForm, selectedKnowledge.value); kEdit.value = true; };

    const saveKnowledge = async () => {
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
    const newPost   = () => { selectedPost.value = null; Object.assign(postForm, { title:'', content:'', category:'' }); postEdit.value = true; };
    const editPost  = () => { Object.assign(postForm, selectedPost.value); postEdit.value = true; };

    const savePost = async () => {
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
      if (s < 1024) return s + 'B';
      if (s < 1048576) return (s/1024).toFixed(0) + 'KB';
      return (s/1048576).toFixed(1) + 'MB';
    };

    // ═══════════════════════════════════════════════
    // 6. 설정 (settings)
    // ═══════════════════════════════════════════════
    const settingsTab = ref('members'); // scraping | members | rules | vacation | categories

    // 휴가 관리
    const vacations        = ref([]);
    const newVacAssigneeId = ref('');
    const newVacDate       = ref(todayStr());
    const newVacType       = ref('연차');

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
    const newCategoryName = ref('');
    const categoryError   = ref('');

    const addCategory = async () => {
      categoryError.value = '';
      const result = await eel.add_category(newCategoryName.value)();
      if (result.success) { newCategoryName.value = ''; await loadCategoryList(); }
      else categoryError.value = result.error;
    };

    const deleteCategoryItem = async (id) => {
      if (!confirm('유형을 삭제하시겠습니까?')) return;
      await eel.delete_category(id)();
      await loadCategoryList();
    };

    const moveCategoryItem = async (idx, dir) => {
      const list = categoryList.value;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= list.length) return;
      const orderList = list.map((c, i) => ({ id: c.id, sort_order: i }));
      const tmp = orderList[idx].sort_order;
      orderList[idx].sort_order = orderList[newIdx].sort_order;
      orderList[newIdx].sort_order = tmp;
      await eel.update_category_order(orderList)();
      await loadCategoryList();
    };

    // ─────────────────────────────────────────────
    const config = reactive({
      url_pattern: '', dynamic: false,
      selectors: { voc_number:'', title:'', content:'', requester:'', due_date:'', status:'', images:'' }
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

    const loadConfig = async () => {
      const d = await eel.get_config()();
      config.url_pattern = d.url_pattern || '';
      config.dynamic = d.dynamic || false;
      Object.assign(config.selectors, d.selectors || {});
    };

    const saveConfig = async () => {
      await eel.save_config({ ...config, selectors: { ...config.selectors } })();
      configSaved.value = true; setTimeout(() => configSaved.value = false, 2000);
    };

    const testFetch = async () => {
      if (!testNum.value.trim()) return;
      testLoading.value = true; testResult.value = null;
      testResult.value = await eel.fetch_voc_data(testNum.value.trim())();
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
      const list = assignees.value;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= list.length) return;
      const orderList = list.map((a, i) => ({ id: a.id, turn_order: i }));
      const tmp = orderList[idx].turn_order;
      orderList[idx].turn_order = orderList[newIdx].turn_order;
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
      { key:'voc_number', label:'VOC 번호' },
      { key:'title',      label:'제목' },
      { key:'content',    label:'내용' },
      { key:'requester',  label:'요청자' },
      { key:'due_date',   label:'완료요청일' },
      { key:'status',     label:'처리상태', hint:'동기화용' },
      { key:'images',     label:'이미지 범위', hint:'비워두면 content 영역 전체' },
    ];

    // ═══════════════════════════════════════════════
    // 메뉴 전환
    // ═══════════════════════════════════════════════
    const switchMenu = async (menu) => {
      activeMenu.value = menu;
      selectedVoc.value = null;
      if (menu === 'active')    { await Promise.all([loadActiveVocs(), loadWorkload(), loadNextUp(), generateReport()]); }
      if (menu === 'allvoc')    { await loadCategoryList(); await loadAllVoc(); }
      if (menu === 'stats')     { await loadWorkload(); await loadStats(); }
      if (menu === 'knowledge') { await loadCategoryList(); await loadKnowledge(); }
      if (menu === 'board')     { await loadBoard(); }
      if (menu === 'settings')  { await loadConfig(); await loadAssignmentRules(); await loadVacations(); await loadCategoryList(); if (!settingsTab.value) settingsTab.value = 'members'; }
    };

    onMounted(async () => {
      imageSupport.value = await eel.check_image_support()();
      await Promise.all([loadAssignees(), loadWorkload(), loadActiveVocs(), loadNextUp(), generateReport(), loadCategoryList()]);
    });

    return {
      activeMenu, switchMenu, assignees, workload, nextUp, imageSupport,
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
      newMember, memberError, assignmentRules, newRuleCategory, newRuleAssigneeId, newRuleNote,
      loadConfig, saveConfig, testFetch, addMember, toggleMember, moveMember,
      loadAssignmentRules, saveRule, deleteRule, selectorFields,
      // 휴가
      vacations, newVacAssigneeId, newVacDate, newVacType,
      loadVacations, addVacation, deleteVacation,
      // 유형 관리
      categoryList, newCategoryName, categoryError,
      addCategory, deleteCategoryItem, moveCategoryItem,
    };
  }
}).mount('#app');
