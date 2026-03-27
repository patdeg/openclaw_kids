(function() {
  'use strict';

  // ── State ──
  const state = {
    tasks: [],
    filter: 'all',
    search: '',
    selectedId: null,
    selectedTask: null,
  };

  // ── DOM refs ──
  let tasksList, loadingState, emptyState, detailPanel, detailBody;
  let createModal, searchInput;

  // ── Helpers ──
  function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function timeAgo(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    const days = Math.floor(hrs / 24);
    if (days < 30) return days + 'd ago';
    return d.toLocaleDateString();
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function showToast(msg) {
    const el = document.createElement('div');
    el.className = 'tasks-toast';
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }

  // ── API ──
  async function api(path, options = {}) {
    const resp = await fetch('/api/tasks' + path, options);
    if (!resp.ok) {
      const text = await resp.text();
      let msg;
      try { msg = JSON.parse(text).error; } catch { msg = text || resp.statusText; }
      throw new Error(msg);
    }
    return resp.json();
  }

  async function loadTasks() {
    const params = new URLSearchParams();
    if (state.filter !== 'all') params.set('status', state.filter);
    if (state.search) params.set('q', state.search);
    const qs = params.toString();
    const data = await api(qs ? '?' + qs : '');
    state.tasks = data.tasks || [];
  }

  async function loadTaskDetail(id) {
    const data = await api('/' + id);
    state.selectedTask = data;
    return data;
  }

  // ── Render ──
  function renderList() {
    loadingState.style.display = 'none';

    if (state.tasks.length === 0) {
      emptyState.style.display = '';
      tasksList.innerHTML = '';
      return;
    }
    emptyState.style.display = 'none';

    tasksList.innerHTML = state.tasks.map(t => {
      const isSelected = t.id === state.selectedId;
      const checkClass = t.status === 'done' ? 'done' : t.status === 'started' ? 'started' : '';
      const checkIcon = t.status === 'done' ? '<span class="material-icons">check</span>' : '';

      let meta = '';
      if (t.due_date) {
        const overdue = t.status !== 'done' && new Date(t.due_date) < new Date();
        meta += `<span class="task-meta-item" style="${overdue ? 'color:var(--bf-error)' : ''}">
          <span class="material-icons">event</span>${formatDate(t.due_date)}</span>`;
      }
      if (t.source && t.source !== 'web') {
        meta += `<span class="source-badge ${escapeHtml(t.source)}">${escapeHtml(t.source)}</span>`;
      }
      if (t.file_count > 0) {
        meta += `<span class="task-meta-item"><span class="material-icons">attach_file</span>${t.file_count}</span>`;
      }
      if (t.comment_count > 0) {
        meta += `<span class="task-meta-item"><span class="material-icons">chat_bubble_outline</span>${t.comment_count}</span>`;
      }
      meta += `<span class="task-meta-item">${timeAgo(t.updated_at)}</span>`;

      return `<div class="task-card ${isSelected ? 'selected' : ''} status-${escapeHtml(t.status)}" data-id="${escapeHtml(t.id)}">
        <div class="task-checkbox ${checkClass}" data-id="${escapeHtml(t.id)}" data-status="${escapeHtml(t.status)}">${checkIcon}</div>
        <div class="task-card-content">
          <div style="display:flex;align-items:center;gap:8px">
            <span class="priority-dot ${escapeHtml(t.priority)}"></span>
            <div class="task-card-title">${escapeHtml(t.title)}</div>
          </div>
          <div class="task-card-meta">${meta}</div>
        </div>
      </div>`;
    }).join('');

    // Attach click handlers
    tasksList.querySelectorAll('.task-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.task-checkbox')) return;
        selectTask(card.dataset.id);
      });
    });

    tasksList.querySelectorAll('.task-checkbox').forEach(cb => {
      cb.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleTaskStatus(cb.dataset.id, cb.dataset.status);
      });
    });
  }

  let detailDatePicker = null;

  function renderDetail(task) {
    if (!task) {
      detailPanel.classList.remove('open');
      return;
    }

    // Destroy previous date picker's document listener before replacing DOM
    if (detailDatePicker) { detailDatePicker.destroy(); detailDatePicker = null; }

    detailPanel.classList.add('open');

    const comments = (task.comments || []).map(c => {
      const sourceClass = 'source-' + (c.source || 'user');
      const label = c.source === 'system' ? 'System' : c.source === 'alfred' ? 'Alfred' : c.source === 'email' ? 'Email' : 'You';
      return `<div class="comment-item ${sourceClass}">
        <div class="comment-header">
          <strong>${escapeHtml(label)}</strong>
          <span>${timeAgo(c.created_at)}</span>
        </div>
        <div class="comment-body">${escapeHtml(c.body)}</div>
      </div>`;
    }).join('');

    const files = (task.files || []).map(f => {
      const name = f.original_filename || f.stored_filename || f.file_id;
      return `<div class="linked-file">
        <span class="material-icons">insert_drive_file</span>
        <a class="linked-file-name" href="/files" title="${escapeHtml(f.file_id)}">${escapeHtml(name)}</a>
        <button class="unlink-btn" data-file="${escapeHtml(f.file_id)}" title="Unlink">
          <span class="material-icons" style="font-size:16px">close</span>
        </button>
      </div>`;
    }).join('');

    detailBody.innerHTML = `
      <textarea class="detail-title" id="detailTitle" rows="1">${escapeHtml(task.title)}</textarea>

      <div class="detail-fields">
        <span class="detail-label">Status</span>
        <select class="detail-select" id="detailStatus">
          <option value="pending" ${task.status === 'pending' ? 'selected' : ''}>Pending</option>
          <option value="started" ${task.status === 'started' ? 'selected' : ''}>Started</option>
          <option value="done" ${task.status === 'done' ? 'selected' : ''}>Done</option>
          <option value="archived" ${task.status === 'archived' ? 'selected' : ''}>Archived</option>
        </select>

        <span class="detail-label">Priority</span>
        <select class="detail-select" id="detailPriority">
          <option value="low" ${task.priority === 'low' ? 'selected' : ''}>Low</option>
          <option value="medium" ${task.priority === 'medium' ? 'selected' : ''}>Medium</option>
          <option value="high" ${task.priority === 'high' ? 'selected' : ''}>High</option>
          <option value="urgent" ${task.priority === 'urgent' ? 'selected' : ''}>Urgent</option>
        </select>

        <span class="detail-label">Due Date</span>
        <div id="detailDueDatePicker"></div>

        <span class="detail-label">Source</span>
        <span class="detail-value">${escapeHtml(task.source || 'web')}</span>

        <span class="detail-label">Created</span>
        <span class="detail-value">${formatDate(task.created_at)}</span>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">
          <span class="material-icons">notes</span> Description
        </div>
        <textarea class="detail-description" id="detailDescription" placeholder="Add a description...">${escapeHtml(task.description)}</textarea>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">
          <span class="material-icons">attach_file</span> Files
        </div>
        <div class="linked-files-list">${files}</div>
        <button class="link-file-btn" id="linkFileBtn">
          <span class="material-icons">add</span> Link a vault file
        </button>
      </div>

      <div class="detail-section">
        <button class="task-chat-open-btn" id="taskChatOpenBtn">
          <span class="material-icons">smart_toy</span> Chat with Alfred
        </button>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">
          <span class="material-icons">forum</span> Comments
        </div>
        <div class="comments-list">${comments || '<p style="color:var(--text-secondary);font-size:13px">No comments yet</p>'}</div>
        <div class="comment-input-row">
          <input type="text" class="comment-input" id="commentInput" placeholder="Add a comment...">
          <button class="comment-send-btn" id="commentSendBtn">Add</button>
        </div>
      </div>
    `;

    // Attach detail event handlers
    attachDetailHandlers(task);
  }

  function attachDetailHandlers(task) {
    // Auto-save title on blur
    const titleEl = document.getElementById('detailTitle');
    titleEl.addEventListener('blur', () => {
      const val = titleEl.value.trim();
      if (val && val !== task.title) {
        updateTask(task.id, { title: val });
      }
    });
    // Auto-resize title
    titleEl.addEventListener('input', () => {
      titleEl.style.height = 'auto';
      titleEl.style.height = titleEl.scrollHeight + 'px';
    });

    // Status change
    document.getElementById('detailStatus').addEventListener('change', (e) => {
      updateTask(task.id, { status: e.target.value });
    });

    // Priority change
    document.getElementById('detailPriority').addEventListener('change', (e) => {
      updateTask(task.id, { priority: e.target.value });
    });

    // Due date — custom mini calendar
    detailDatePicker = createDatePicker(
      document.getElementById('detailDueDatePicker'),
      task.due_date || null,
      (isoDate) => updateTask(task.id, { due_date: isoDate || '' })
    );

    // Description save on blur
    const descEl = document.getElementById('detailDescription');
    descEl.addEventListener('blur', () => {
      if (descEl.value !== task.description) {
        updateTask(task.id, { description: descEl.value });
      }
    });

    // Add comment
    const commentInput = document.getElementById('commentInput');
    document.getElementById('commentSendBtn').addEventListener('click', () => addComment(task.id, commentInput));
    commentInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        addComment(task.id, commentInput);
      }
    });

    // Unlink file buttons
    detailBody.querySelectorAll('.unlink-btn').forEach(btn => {
      btn.addEventListener('click', () => unlinkFile(task.id, btn.dataset.file));
    });

    // Link file button
    document.getElementById('linkFileBtn').addEventListener('click', () => promptLinkFile(task.id));

    // Chat with Alfred — navigate to main chat page with task context
    document.getElementById('taskChatOpenBtn').addEventListener('click', () => {
      const q = '[Task #' + task.id + ' | "' + task.title + '"] ';
      window.location.href = '/?q=' + encodeURIComponent(q) + '&new=1';
    });
  }

  // ── Actions ──
  async function selectTask(id) {
    state.selectedId = id;
    renderList();
    try {
      const task = await loadTaskDetail(id);
      renderDetail(task);
    } catch (e) {
      showToast('Failed to load task');
    }
  }

  async function toggleTaskStatus(id, currentStatus) {
    const nextStatus = currentStatus === 'done' ? 'pending' : currentStatus === 'started' ? 'done' : 'started';
    try {
      await api('/' + id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus }),
      });
      await refresh();
    } catch (e) {
      showToast('Failed to update: ' + e.message);
    }
  }

  async function updateTask(id, fields) {
    try {
      await api('/' + id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
      });
      // Refresh list but don't re-render detail (avoid flicker)
      await loadTasks();
      renderList();
    } catch (e) {
      showToast('Failed to update: ' + e.message);
    }
  }

  async function createTask() {
    const title = document.getElementById('newTitle').value.trim();
    if (!title) {
      showToast('Title is required');
      return;
    }
    try {
      const data = await api('', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          description: document.getElementById('newDescription').value,
          priority: document.getElementById('newPriority').value,
          due_date: (modalDatePicker && modalDatePicker.getValue()) || null,
        }),
      });
      closeModal();
      await refresh();
      selectTask(data.id);
      showToast('Task created');
    } catch (e) {
      showToast('Failed to create: ' + e.message);
    }
  }

  async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    try {
      await api('/' + id, { method: 'DELETE' });
      state.selectedId = null;
      state.selectedTask = null;
      detailPanel.classList.remove('open');
      await refresh();
      showToast('Task deleted');
    } catch (e) {
      showToast('Failed to delete: ' + e.message);
    }
  }

  async function addComment(taskId, inputEl) {
    const body = inputEl.value.trim();
    if (!body) return;
    try {
      await api('/' + taskId + '/comments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body }),
      });
      inputEl.value = '';
      const task = await loadTaskDetail(taskId);
      renderDetail(task);
    } catch (e) {
      showToast('Failed to add comment');
    }
  }

  async function unlinkFile(taskId, fileId) {
    try {
      await api('/' + taskId + '/files/' + fileId, { method: 'DELETE' });
      const task = await loadTaskDetail(taskId);
      renderDetail(task);
    } catch (e) {
      showToast('Failed to unlink file');
    }
  }

  // ── Vault file picker ──
  let filePicker = null;

  function promptLinkFile(taskId) {
    openFilePicker(taskId);
  }

  function openFilePicker(taskId) {
    // Build modal on first use
    if (!filePicker) {
      const overlay = document.createElement('div');
      overlay.className = 'file-picker-overlay';
      overlay.innerHTML = `
        <div class="file-picker-modal">
          <div class="file-picker-header">
            <span class="material-icons">folder_open</span>
            <span>Link a vault file</span>
            <button class="icon-btn file-picker-close" id="filePickerClose">
              <span class="material-icons">close</span>
            </button>
          </div>
          <div class="file-picker-search-row">
            <span class="material-icons">search</span>
            <input type="text" id="filePickerSearch" placeholder="Search files…" autocomplete="off">
          </div>
          <div class="file-picker-results" id="filePickerResults">
            <p class="file-picker-hint">Type to search, or scroll to browse</p>
          </div>
        </div>`;
      document.body.appendChild(overlay);
      filePicker = overlay;

      document.getElementById('filePickerClose').addEventListener('click', closeFilePicker);
      overlay.addEventListener('click', e => { if (e.target === overlay) closeFilePicker(); });

      let searchTimer = null;
      document.getElementById('filePickerSearch').addEventListener('input', e => {
        clearTimeout(searchTimer);
        // Read taskId from dataset — always reflects the currently open task
        searchTimer = setTimeout(() => searchVaultFiles(e.target.value, filePicker.dataset.taskId), 300);
      });
    }

    // Update taskId closure and reset
    filePicker.dataset.taskId = taskId;
    document.getElementById('filePickerSearch').value = '';
    document.getElementById('filePickerResults').innerHTML = '<p class="file-picker-hint">Type to search, or scroll to browse</p>';
    filePicker.style.display = 'flex';
    setTimeout(() => document.getElementById('filePickerSearch').focus(), 50);

    // Load initial list
    searchVaultFiles('', taskId);
  }

  function closeFilePicker() {
    if (filePicker) filePicker.style.display = 'none';
  }

  async function searchVaultFiles(query, taskId) {
    const resultsEl = document.getElementById('filePickerResults');
    resultsEl.innerHTML = '<p class="file-picker-hint">Loading…</p>';
    try {
      const url = query
        ? `/api/vault/list?q=${encodeURIComponent(query)}&limit=30`
        : '/api/vault/list?limit=30';
      const resp = await fetch(url);
      if (!resp.ok) throw new Error('Failed');
      const data = await resp.json();
      const items = data.items || data || [];
      if (!items.length) {
        resultsEl.innerHTML = '<p class="file-picker-hint">No files found</p>';
        return;
      }
      resultsEl.innerHTML = '';
      items.forEach(f => {
        const row = document.createElement('div');
        row.className = 'file-picker-row';
        // vault list returns 'filename'; vault search returns 'original_filename'
        const name = f.filename || f.original_filename || f.stored_filename || f.id;
        const topic = f.topic ? `<span class="file-picker-topic">${escapeHtml(f.topic)}</span>` : '';
        const updated = f.updated || f.updated_at;
        const updatedStr = updated ? new Date(updated).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
        row.innerHTML = `
          <span class="material-icons file-picker-icon">${fileTypeIcon(f.type)}</span>
          <div class="file-picker-info">
            <span class="file-picker-name">${escapeHtml(name)}</span>
            ${f.description ? `<span class="file-picker-desc">${escapeHtml(f.description)}</span>` : ''}
          </div>
          <div class="file-picker-meta">
            ${topic}
            ${updatedStr ? `<span class="file-picker-date">${updatedStr}</span>` : ''}
          </div>`;
        row.addEventListener('click', () => linkFileFromPicker(filePicker.dataset.taskId, f.id, name));
        resultsEl.appendChild(row);
      });
    } catch (e) {
      resultsEl.innerHTML = '<p class="file-picker-hint">Error loading files</p>';
    }
  }

  function fileTypeIcon(type) {
    const icons = { image: 'image', video: 'videocam', audio: 'audiotrack',
      document: 'description', text: 'article', pdf: 'picture_as_pdf' };
    return icons[type] || 'insert_drive_file';
  }

  async function linkFileFromPicker(taskId, fileId, fileName) {
    closeFilePicker();
    try {
      await api('/' + taskId + '/files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_id: fileId }),
      });
      const task = await loadTaskDetail(taskId);
      renderDetail(task);
      showToast('Linked: ' + fileName);
    } catch (e) {
      showToast('Failed to link file');
    }
  }

  // ── Mini date picker ─────────────────────────────────────────────────────
  // Creates a custom date picker widget and attaches it to a container.
  // onChange(isoDate|null) is called when date changes.
  function createDatePicker(container, initialValue, onChange) {
    const DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
    const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'];

    let selected = initialValue ? new Date(initialValue + 'T12:00:00') : null;
    let view = selected ? new Date(selected) : new Date();
    view.setDate(1);

    const wrap = document.createElement('div');
    wrap.className = 'datepicker-wrap';

    const trigger = document.createElement('div');
    trigger.className = 'datepicker-trigger';
    trigger.innerHTML = `<span class="material-icons">event</span><span class="datepicker-label"></span><button class="datepicker-clear" title="Clear">×</button>`;
    wrap.appendChild(trigger);

    const popup = document.createElement('div');
    popup.className = 'datepicker-popup';
    popup.style.display = 'none';
    wrap.appendChild(popup);

    container.appendChild(wrap);

    function formatSelected() {
      if (!selected) return 'No due date';
      return selected.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function toISO(d) {
      if (!d) return '';
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    }

    function renderPopup() {
      const today = new Date(); today.setHours(0,0,0,0);
      const firstDay = new Date(view.getFullYear(), view.getMonth(), 1).getDay();
      const daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();

      let rows = '';
      let cell = 0;
      let row = '<tr>';
      for (let i = 0; i < firstDay; i++) { row += '<td></td>'; cell++; }
      for (let d = 1; d <= daysInMonth; d++) {
        const date = new Date(view.getFullYear(), view.getMonth(), d);
        date.setHours(0,0,0,0);
        const isToday = date.getTime() === today.getTime();
        const isSel = selected && toISO(date) === toISO(selected);
        row += `<td class="dp-day${isToday ? ' dp-today' : ''}${isSel ? ' dp-selected' : ''}" data-date="${toISO(date)}">${d}</td>`;
        cell++;
        if (cell % 7 === 0 && d < daysInMonth) { rows += row + '</tr>'; row = '<tr>'; }
      }
      while (cell % 7 !== 0) { row += '<td></td>'; cell++; }
      rows += row + '</tr>';

      popup.innerHTML = `
        <div class="dp-header">
          <button class="dp-nav" data-dir="-1">‹</button>
          <span class="dp-month">${MONTHS[view.getMonth()]} ${view.getFullYear()}</span>
          <button class="dp-nav" data-dir="1">›</button>
        </div>
        <table class="dp-grid">
          <thead><tr>${DAYS.map(d => `<th>${d}</th>`).join('')}</tr></thead>
          <tbody>${rows}</tbody>
        </table>`;

      popup.querySelectorAll('.dp-nav').forEach(btn => {
        btn.addEventListener('click', e => {
          e.stopPropagation();
          view.setMonth(view.getMonth() + parseInt(btn.dataset.dir));
          renderPopup();
        });
      });

      popup.querySelectorAll('.dp-day').forEach(cell => {
        cell.addEventListener('click', e => {
          e.stopPropagation();
          selected = new Date(cell.dataset.date + 'T12:00:00');
          trigger.querySelector('.datepicker-label').textContent = formatSelected();
          wrap.classList.toggle('has-date', !!selected);
          popup.style.display = 'none';
          onChange(toISO(selected));
        });
      });
    }

    trigger.querySelector('.datepicker-label').textContent = formatSelected();
    wrap.classList.toggle('has-date', !!selected);

    trigger.addEventListener('click', e => {
      if (e.target.closest('.datepicker-clear')) return;
      const isOpen = popup.style.display !== 'none';
      // Close any other open pickers
      document.querySelectorAll('.datepicker-popup').forEach(p => { p.style.display = 'none'; });
      if (!isOpen) { renderPopup(); popup.style.display = ''; }
    });

    trigger.querySelector('.datepicker-clear').addEventListener('click', e => {
      e.stopPropagation();
      selected = null;
      trigger.querySelector('.datepicker-label').textContent = formatSelected();
      wrap.classList.remove('has-date');
      popup.style.display = 'none';
      onChange(null);
    });

    // Use AbortController so the document listener is removed if the picker is destroyed
    const ac = new AbortController();
    document.addEventListener('click', e => {
      if (!wrap.contains(e.target)) popup.style.display = 'none';
    }, { signal: ac.signal });

    // Return API for reading/resetting/destroying value
    return {
      getValue: () => toISO(selected),
      reset: (newValue) => {
        selected = newValue ? new Date(newValue + 'T12:00:00') : null;
        view = selected ? new Date(selected) : new Date();
        view.setDate(1);
        trigger.querySelector('.datepicker-label').textContent = formatSelected();
        wrap.classList.toggle('has-date', !!selected);
        popup.style.display = 'none';
      },
      destroy: () => ac.abort(),
    };
  }

  // ── Modal ──
  let modalDatePicker = null;

  function openModal() {
    createModal.style.display = 'flex';
    document.getElementById('newTitle').value = '';
    document.getElementById('newDescription').value = '';
    document.getElementById('newPriority').value = 'medium';

    // Create the picker once; reset (don't recreate) on subsequent opens
    if (!modalDatePicker) {
      const pickerContainer = document.getElementById('newDueDatePicker');
      if (pickerContainer) {
        modalDatePicker = createDatePicker(pickerContainer, null, () => {});
      }
    } else {
      modalDatePicker.reset(null);
    }

    setTimeout(() => document.getElementById('newTitle').focus(), 100);
  }

  function closeModal() {
    createModal.style.display = 'none';
  }

  // ── Refresh ──
  async function refresh() {
    try {
      await loadTasks();
      renderList();
    } catch (e) {
      showToast('Failed to load tasks');
    }
  }

  // ── Init ──
  document.addEventListener('DOMContentLoaded', async () => {
    tasksList = document.getElementById('tasksList');
    loadingState = document.getElementById('loadingState');
    emptyState = document.getElementById('emptyState');
    detailPanel = document.getElementById('detailPanel');
    detailBody = document.getElementById('detailBody');
    createModal = document.getElementById('createModal');
    searchInput = document.getElementById('searchInput');

    // Navigation
    document.getElementById('backBtn').addEventListener('click', () => {
      window.location.href = '/';
    });

    // Refresh
    document.getElementById('refreshBtn').addEventListener('click', refresh);

    // Filters
    document.querySelectorAll('.filter-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        state.filter = pill.dataset.filter;
        refresh();
      });
    });

    // Search
    let searchTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.search = searchInput.value.trim();
        refresh();
      }, 300);
    });

    // Create
    document.getElementById('createFab').addEventListener('click', openModal);
    document.getElementById('closeModalBtn').addEventListener('click', closeModal);
    document.getElementById('cancelCreateBtn').addEventListener('click', closeModal);
    document.getElementById('confirmCreateBtn').addEventListener('click', createTask);
    createModal.addEventListener('click', (e) => {
      if (e.target === createModal) closeModal();
    });

    // Detail close
    document.getElementById('closeDetailBtn').addEventListener('click', () => {
      state.selectedId = null;
      state.selectedTask = null;
      detailPanel.classList.remove('open');
      renderList();
    });

    // Delete
    document.getElementById('deleteTaskBtn').addEventListener('click', () => {
      if (state.selectedId) deleteTask(state.selectedId);
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (createModal.style.display !== 'none') {
          closeModal();
        } else if (detailPanel.classList.contains('open')) {
          state.selectedId = null;
          detailPanel.classList.remove('open');
          renderList();
        }
      }
      if (e.key === 'n' && !e.ctrlKey && !e.metaKey && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        openModal();
      }
    });

    // Enter key in create modal
    document.getElementById('newTitle').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        createTask();
      }
    });

    // Load
    await refresh();
  });
})();
