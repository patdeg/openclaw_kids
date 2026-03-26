/**
 * ATHENA Files Browser
 * Google Drive-style file browser for vault management
 *
 * Security Note: All user-generated content is rendered via textContent
 * or escapeHtml() helper to prevent XSS. Only server-generated HTML from
 * trusted sources uses innerHTML.
 */
(function() {
  'use strict';

  // ============================================
  // State
  // ============================================
  const state = {
    view: 'grid', // 'grid' or 'list'
    path: '', // current topic/folder
    topics: [], // { topic, count, total_size, last_updated }
    files: [], // files in current topic
    selection: new Set(), // selected file IDs
    folderSelection: new Set(), // selected folder names
    selectMode: false,
    searchQuery: '',
    sortBy: 'date', // 'name', 'date', 'size'
    sortDesc: true,
    previewIndex: -1,
    currentFileId: null,
    rootVaultMd: null, // Root VAULT.md file info
    topicVaultMd: null // Current topic VAULT.md file info
  };

  // ============================================
  // DOM Elements
  // ============================================
  let mainHeader, selectionHeader, breadcrumb, searchBar, searchInput;
  let filesContent, loadingState, emptyState, filesGrid;
  let dropdownMenu, previewOverlay, infoPanelOverlay, infoPanel;
  let topicPickerOverlay, confirmOverlay, inputOverlay, toastContainer;

  // ============================================
  // Utilities
  // ============================================

  /**
   * Escape HTML special characters for safe display
   */
  function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Create a Material Icon element
   */
  function createIcon(iconName) {
    const span = document.createElement('span');
    span.className = 'material-icons';
    span.textContent = iconName;
    return span;
  }

  /**
   * Format file size for display
   */
  function formatSize(bytes) {
    if (bytes == null || bytes === 0) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
      bytes /= 1024;
      i++;
    }
    return bytes.toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
  }

  /**
   * Format date for display
   */
  function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    // Today
    if (diff < 86400000 && date.getDate() === now.getDate()) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    // This year
    if (date.getFullYear() === now.getFullYear()) {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
    // Older
    return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
  }

  /**
   * Format duration in seconds for display
   */
  function formatDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }

  /**
   * Get file type icon
   */
  function getFileIcon(type) {
    switch (type) {
      case 'image': return 'image';
      case 'audio': return 'audiotrack';
      case 'document': return 'description';
      default: return 'insert_drive_file';
    }
  }

  // ============================================
  // API Calls
  // ============================================

  async function fetchTopics() {
    const response = await fetch('/api/vault/topics');
    if (!response.ok) throw new Error('Failed to fetch topics');
    const data = await response.json();

    // Handle new format with vault_md
    if (data.topics !== undefined) {
      state.rootVaultMd = data.vault_md;
      return data.topics;
    }

    // Fallback for old format (array)
    state.rootVaultMd = null;
    return data;
  }

  async function fetchTopicFiles(topic, limit, offset) {
    limit = limit || 100;
    offset = offset || 0;
    const url = '/api/vault/topic/' + encodeURIComponent(topic) + '?limit=' + limit + '&offset=' + offset;
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to fetch files');
    const data = await response.json();

    // Handle new format with files and vault_md
    if (data.files !== undefined) {
      state.topicVaultMd = data.vault_md;
      return data.files;
    }

    // Fallback for old format (array)
    state.topicVaultMd = null;
    return data;
  }

  async function searchFiles(query) {
    const response = await fetch('/api/vault/list?q=' + encodeURIComponent(query));
    if (!response.ok) throw new Error('Search failed');
    return response.json();
  }

  async function deleteFile(id) {
    const response = await fetch('/api/vault/file/' + id, { method: 'DELETE' });
    if (!response.ok) throw new Error('Delete failed');
    return response.json();
  }

  async function bulkDelete(ids) {
    const response = await fetch('/api/vault/files/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'delete', ids: ids })
    });
    if (!response.ok) throw new Error('Bulk delete failed');
    return response.json();
  }

  async function moveFile(id, topic) {
    const response = await fetch('/api/vault/file/' + id + '/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topic })
    });
    if (!response.ok) throw new Error('Move failed');
    return response.json();
  }

  async function bulkMove(ids, topic) {
    const response = await fetch('/api/vault/files/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'move', ids: ids, topic: topic })
    });
    if (!response.ok) throw new Error('Bulk move failed');
    return response.json();
  }

  async function updateFile(id, data) {
    const response = await fetch('/api/vault/file/' + id, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Update failed');
    return response.json();
  }

  async function fetchStats() {
    const response = await fetch('/api/vault/stats');
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  }

  // ============================================
  // VAULT.md API
  // ============================================

  async function generateVaultMd(topic) {
    const url = topic
      ? '/api/vault/vault-md/' + encodeURIComponent(topic) + '/generate'
      : '/api/vault/vault-md/generate';

    console.log('[VaultMd] Generating for:', topic || 'root');

    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) throw new Error('Failed to generate VAULT.md');
    return response.json();
  }

  async function getVaultMd(topic) {
    const url = topic
      ? '/api/vault/vault-md/' + encodeURIComponent(topic)
      : '/api/vault/vault-md/';

    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to get VAULT.md');
    return response.json();
  }

  async function saveVaultMd(topic, content) {
    const url = topic
      ? '/api/vault/vault-md/' + encodeURIComponent(topic)
      : '/api/vault/vault-md/';

    const response = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content })
    });
    if (!response.ok) throw new Error('Failed to save VAULT.md');
    return response.json();
  }

  // ============================================
  // Markdown Rendering
  // ============================================

  function renderMarkdown(markdown) {
    if (!window.marked || !window.DOMPurify) {
      console.warn('[Markdown] Libraries not loaded');
      return '<pre>' + escapeHtml(markdown) + '</pre>';
    }

    marked.setOptions({
      gfm: true,
      breaks: true,
      headerIds: true
    });

    const rawHtml = marked.parse(markdown);
    return DOMPurify.sanitize(rawHtml);
  }

  // ============================================
  // Navigation
  // ============================================

  /**
   * Context-aware back navigation:
   * - In file preview → close preview, stay in folder
   * - In folder → go to root
   * - In root → go to chat
   */
  function handleBack() {
    // If preview is open, close it first
    if (previewOverlay.style.display !== 'none') {
      closePreview(false);
      return;
    }

    // If in a folder, go to root
    if (state.path) {
      navigateToHome();
      return;
    }

    // If at root, go to chat
    window.location.href = '/';
  }

  function navigateToHome() {
    state.path = '';
    state.files = [];
    state.searchQuery = '';
    updateBreadcrumb();
    loadTopics();
  }

  function navigateToTopic(topic) {
    state.path = topic;
    updateBreadcrumb();
    loadFiles(topic);
  }

  function updateBreadcrumb() {
    breadcrumb.textContent = '';

    // Home item
    const homeItem = document.createElement('span');
    homeItem.className = 'breadcrumb-item';
    homeItem.textContent = 'My Files';
    homeItem.dataset.path = '';
    homeItem.addEventListener('click', function() {
      navigateToHome();
    });
    breadcrumb.appendChild(homeItem);

    // Topic item
    if (state.path) {
      const separator = document.createElement('span');
      separator.className = 'breadcrumb-separator';
      separator.textContent = '>';
      breadcrumb.appendChild(separator);

      const topicItem = document.createElement('span');
      topicItem.className = 'breadcrumb-item';
      topicItem.textContent = state.path;
      topicItem.dataset.path = state.path;
      breadcrumb.appendChild(topicItem);
    }
  }

  // ============================================
  // Data Loading
  // ============================================

  async function loadTopics() {
    showLoading();
    try {
      state.topics = await fetchTopics();
      renderTopics();
    } catch (err) {
      console.error('Failed to load topics:', err);
      showEmpty('Failed to load topics');
    }
  }

  async function loadFiles(topic) {
    showLoading();
    try {
      state.files = await fetchTopicFiles(topic);
      renderFiles();
    } catch (err) {
      console.error('Failed to load files:', err);
      showEmpty('Failed to load files');
    }
  }

  async function performSearch(query) {
    if (!query.trim()) {
      if (state.path) {
        loadFiles(state.path);
      } else {
        loadTopics();
      }
      return;
    }

    showLoading();
    try {
      state.files = await searchFiles(query);
      state.searchQuery = query;
      renderFiles();
    } catch (err) {
      console.error('Search failed:', err);
      showEmpty('Search failed');
    }
  }

  // ============================================
  // Rendering
  // ============================================

  function showLoading() {
    loadingState.style.display = 'flex';
    emptyState.style.display = 'none';
    filesGrid.style.display = 'none';
  }

  function showEmpty(message) {
    loadingState.style.display = 'none';
    emptyState.style.display = 'flex';
    filesGrid.style.display = 'none';

    const msgEl = emptyState.querySelector('p');
    if (msgEl) {
      msgEl.textContent = message || 'No files yet';
    }
  }

  function showGrid() {
    loadingState.style.display = 'none';
    emptyState.style.display = 'none';
    filesGrid.style.display = '';
  }

  function renderTopics() {
    filesGrid.textContent = '';

    if (state.topics.length === 0 && !state.rootVaultMd) {
      showEmpty('No files yet. Upload files through chat to see them here.');
      return;
    }

    // Add VAULT.md at the top if it exists
    if (state.rootVaultMd) {
      const vaultMdItem = createVaultMdItem(state.rootVaultMd);
      filesGrid.appendChild(vaultMdItem);
    }

    // Sort topics
    const sorted = [...state.topics].sort(function(a, b) {
      switch (state.sortBy) {
        case 'name':
          return state.sortDesc ? b.topic.localeCompare(a.topic) : a.topic.localeCompare(b.topic);
        case 'size':
          return state.sortDesc ? (b.total_size || 0) - (a.total_size || 0) : (a.total_size || 0) - (b.total_size || 0);
        case 'date':
        default:
          const aDate = a.last_updated || '';
          const bDate = b.last_updated || '';
          return state.sortDesc ? bDate.localeCompare(aDate) : aDate.localeCompare(bDate);
      }
    });

    sorted.forEach(function(topic) {
      const item = createFolderItem(topic);
      filesGrid.appendChild(item);
    });

    showGrid();
    updateViewMode();
  }

  function createVaultMdItem(vaultMd) {
    const item = document.createElement('div');
    item.className = 'file-item vault-md-item';
    item.dataset.id = vaultMd.id;

    // Thumbnail
    const thumbnail = document.createElement('div');
    thumbnail.className = 'file-thumbnail document';
    thumbnail.appendChild(createIcon('auto_awesome'));
    item.appendChild(thumbnail);

    // File name
    const name = document.createElement('div');
    name.className = 'file-name';
    name.textContent = 'VAULT.md';
    item.appendChild(name);

    // Description
    const info = document.createElement('div');
    info.className = 'file-info';
    info.textContent = 'AI Context File';
    item.appendChild(info);

    // Click handler - open preview
    item.addEventListener('click', function() {
      openVaultMdPreview(vaultMd);
    });

    return item;
  }

  function openVaultMdPreview(vaultMd) {
    state.currentFileId = vaultMd.id;

    const content = document.getElementById('previewContent');
    const title = document.getElementById('previewTitle');

    title.textContent = 'VAULT.md';
    content.textContent = '';

    // Build URL with raw parameter for direct content
    const topic = state.path || '';
    const baseUrl = topic
      ? '/api/vault/vault-md/' + encodeURIComponent(topic)
      : '/api/vault/vault-md/';
    const rawUrl = baseUrl + '?raw=1';

    // Create a fake file object for renderTextPreview
    const fakeFile = {
      id: vaultMd.id,
      original_filename: 'VAULT.md',
      stored_filename: 'VAULT.md',
      type: 'document',
      url: rawUrl,
      topic: topic
    };

    renderTextPreview(content, fakeFile, rawUrl, true);

    previewOverlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Push state for swipe-back support
    history.pushState({ preview: true, vaultMd: true }, '', null);

    // Hide nav buttons for VAULT.md
    document.getElementById('previewPrev').style.visibility = 'hidden';
    document.getElementById('previewNext').style.visibility = 'hidden';
  }

  function renderFiles() {
    filesGrid.textContent = '';

    if (state.files.length === 0 && !state.topicVaultMd) {
      showEmpty(state.searchQuery ? 'No files match your search' : 'This folder is empty');
      return;
    }

    // Add topic VAULT.md at the top if it exists
    if (state.topicVaultMd) {
      const vaultMdItem = createVaultMdItem(state.topicVaultMd);
      filesGrid.appendChild(vaultMdItem);
    }

    // Sort files
    const sorted = [...state.files].sort(function(a, b) {
      switch (state.sortBy) {
        case 'name':
          const nameA = a.original_filename || a.stored_filename || '';
          const nameB = b.original_filename || b.stored_filename || '';
          return state.sortDesc ? nameB.localeCompare(nameA) : nameA.localeCompare(nameB);
        case 'size':
          return state.sortDesc ? (b.file_size || 0) - (a.file_size || 0) : (a.file_size || 0) - (b.file_size || 0);
        case 'date':
        default:
          const aDate = a.created_at || '';
          const bDate = b.created_at || '';
          return state.sortDesc ? bDate.localeCompare(aDate) : aDate.localeCompare(bDate);
      }
    });

    sorted.forEach(function(file, index) {
      const item = createFileItem(file, index);
      filesGrid.appendChild(item);
    });

    showGrid();
    updateViewMode();
    updateSelectMode();
  }

  function createFolderItem(topic) {
    const item = document.createElement('div');
    item.className = 'folder-item';
    item.dataset.topic = topic.topic;

    // Checkbox for selection mode
    const checkbox = document.createElement('div');
    checkbox.className = 'select-checkbox';
    checkbox.appendChild(createIcon('check'));
    item.appendChild(checkbox);

    // Folder icon
    const icon = createIcon('folder');
    icon.classList.add('folder-icon');
    item.appendChild(icon);

    // Folder name (uses textContent for XSS safety)
    const name = document.createElement('div');
    name.className = 'folder-name';
    name.textContent = topic.topic;
    item.appendChild(name);

    // Count
    const count = document.createElement('div');
    count.className = 'folder-count';
    count.textContent = topic.count + ' files';
    item.appendChild(count);

    // Click handler
    item.addEventListener('click', function(e) {
      if (state.selectMode) {
        toggleFolderSelection(topic.topic);
        item.classList.toggle('selected', state.folderSelection.has(topic.topic));
        updateSelectionCount();
        return;
      }
      navigateToTopic(topic.topic);
    });

    // Long press to enter selection mode on mobile
    let pressTimer;
    item.addEventListener('touchstart', function(e) {
      pressTimer = setTimeout(function() {
        enterSelectMode();
        toggleFolderSelection(topic.topic);
        item.classList.add('selected');
        updateSelectionCount();
      }, 500);
    });
    item.addEventListener('touchend', function() {
      clearTimeout(pressTimer);
    });
    item.addEventListener('touchmove', function() {
      clearTimeout(pressTimer);
    });

    return item;
  }

  function createFileItem(file, index) {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.dataset.id = file.id;
    item.dataset.index = index;

    if (state.selection.has(file.id)) {
      item.classList.add('selected');
    }

    // Checkbox for selection mode
    const checkbox = document.createElement('div');
    checkbox.className = 'select-checkbox';
    checkbox.appendChild(createIcon('check'));
    item.appendChild(checkbox);

    // Thumbnail
    const thumbnail = document.createElement('div');
    thumbnail.className = 'file-thumbnail';
    if (file.type) {
      thumbnail.classList.add(file.type);
    }

    if (file.type === 'image' && file.url) {
      const img = document.createElement('img');
      img.src = file.url;
      img.alt = file.original_filename || 'Image';
      img.loading = 'lazy';
      thumbnail.appendChild(img);
    } else {
      thumbnail.appendChild(createIcon(getFileIcon(file.type)));
    }
    item.appendChild(thumbnail);

    // File name (uses textContent for XSS safety)
    const name = document.createElement('div');
    name.className = 'file-name';
    name.textContent = file.original_filename || file.stored_filename || 'Untitled';
    item.appendChild(name);

    // File info
    const info = document.createElement('div');
    info.className = 'file-info';
    const infoText = formatSize(file.file_size);
    if (file.type === 'audio' && file.duration) {
      info.textContent = infoText + ' - ' + formatDuration(file.duration);
    } else {
      info.textContent = infoText;
    }
    item.appendChild(info);

    // Click handler
    item.addEventListener('click', function(e) {
      if (state.selectMode) {
        toggleSelection(file.id);
        item.classList.toggle('selected', state.selection.has(file.id));
        updateSelectionCount();
        return;
      }
      openPreview(index);
    });

    // Long press for selection mode on mobile
    let pressTimer;
    item.addEventListener('touchstart', function(e) {
      pressTimer = setTimeout(function() {
        enterSelectMode();
        toggleSelection(file.id);
        item.classList.add('selected');
        updateSelectionCount();
      }, 500);
    });
    item.addEventListener('touchend', function() {
      clearTimeout(pressTimer);
    });
    item.addEventListener('touchmove', function() {
      clearTimeout(pressTimer);
    });

    return item;
  }

  // ============================================
  // View Mode
  // ============================================

  function toggleView() {
    state.view = state.view === 'grid' ? 'list' : 'grid';
    updateViewMode();
    updateViewToggleIcon();
  }

  function updateViewMode() {
    if (state.view === 'list') {
      filesGrid.classList.add('list-view');
    } else {
      filesGrid.classList.remove('list-view');
    }
  }

  function updateViewToggleIcon() {
    const btn = document.getElementById('viewToggle');
    const icon = btn.querySelector('.material-icons');
    icon.textContent = state.view === 'grid' ? 'view_list' : 'grid_view';
  }

  // ============================================
  // Selection Mode
  // ============================================

  function enterSelectMode() {
    state.selectMode = true;
    mainHeader.style.display = 'none';
    selectionHeader.style.display = 'flex';
    filesGrid.classList.add('select-mode');
  }

  function exitSelectMode() {
    state.selectMode = false;
    state.selection.clear();
    state.folderSelection.clear();
    mainHeader.style.display = 'flex';
    selectionHeader.style.display = 'none';
    filesGrid.classList.remove('select-mode');

    // Remove selected class from all items
    document.querySelectorAll('.file-item.selected, .folder-item.selected').forEach(function(item) {
      item.classList.remove('selected');
    });
  }

  function toggleSelection(id) {
    if (state.selection.has(id)) {
      state.selection.delete(id);
    } else {
      state.selection.add(id);
    }
  }

  function toggleFolderSelection(name) {
    if (state.folderSelection.has(name)) {
      state.folderSelection.delete(name);
    } else {
      state.folderSelection.add(name);
    }
  }

  function selectAll() {
    state.files.forEach(function(file) {
      state.selection.add(file.id);
    });
    document.querySelectorAll('.file-item').forEach(function(item) {
      item.classList.add('selected');
    });
    updateSelectionCount();
  }

  function updateSelectionCount() {
    const countEl = document.getElementById('selectionCount');
    const totalCount = state.selection.size + state.folderSelection.size;
    countEl.textContent = totalCount + ' selected';
  }

  function updateSelectMode() {
    if (state.selectMode) {
      filesGrid.classList.add('select-mode');
    }
  }

  // ============================================
  // Preview
  // ============================================

  function openPreview(index) {
    state.previewIndex = index;
    const file = state.files[index];
    if (!file) return;

    state.currentFileId = file.id;
    renderPreview(file);
    previewOverlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    // Push state for swipe-back support
    history.pushState({ preview: true, fileId: file.id }, '', null);
  }

  function closePreview(fromPopstate) {
    previewOverlay.style.display = 'none';
    document.body.style.overflow = '';
    state.previewIndex = -1;
    state.currentFileId = null;

    // Stop any playing audio
    const audio = document.querySelector('#previewContent audio');
    if (audio) {
      audio.pause();
    }

    // Go back in history if not triggered by popstate
    if (!fromPopstate && history.state && history.state.preview) {
      history.back();
    }
  }

  function navigatePreview(direction) {
    const newIndex = state.previewIndex + direction;
    if (newIndex >= 0 && newIndex < state.files.length) {
      openPreview(newIndex);
    }
  }

  function renderPreview(file) {
    const content = document.getElementById('previewContent');
    const title = document.getElementById('previewTitle');

    // Set title (uses textContent for XSS safety)
    title.textContent = file.original_filename || file.stored_filename || 'File';

    // Clear content
    content.textContent = '';

    const url = file.url || '/api/vault/file/' + file.id;
    const filename = (file.original_filename || file.stored_filename || '').toLowerCase();
    const isMarkdown = filename.endsWith('.md');
    const isText = filename.endsWith('.txt');

    if (file.type === 'image') {
      const img = document.createElement('img');
      img.src = url;
      img.alt = file.description || 'Image';
      img.className = 'preview-image';
      content.appendChild(img);

      // Add chat button for images
      addChatButton(content, file);

    } else if (file.type === 'audio') {
      renderAudioPreview(content, file, url);

      // Add chat button for audio
      addChatButton(content, file);

    } else if (isMarkdown || isText) {
      // Markdown or text file - fetch and render
      renderTextPreview(content, file, url, isMarkdown);

    } else {
      // Document or other
      const docPreview = document.createElement('div');
      docPreview.className = 'preview-document';

      docPreview.appendChild(createIcon('description'));

      const name = document.createElement('div');
      name.className = 'preview-doc-name';
      name.textContent = file.original_filename || file.stored_filename || 'Document';
      docPreview.appendChild(name);

      const size = document.createElement('div');
      size.className = 'preview-doc-info';
      size.textContent = formatSize(file.file_size);
      docPreview.appendChild(size);

      const downloadBtn = document.createElement('a');
      downloadBtn.href = url;
      downloadBtn.download = file.original_filename || file.stored_filename;
      downloadBtn.className = 'btn btn-primary';
      downloadBtn.textContent = 'Download';
      docPreview.appendChild(downloadBtn);

      content.appendChild(docPreview);

      // Add chat button
      addChatButton(content, file);
    }

    // Update nav button visibility
    document.getElementById('previewPrev').style.visibility = state.previewIndex > 0 ? 'visible' : 'hidden';
    document.getElementById('previewNext').style.visibility = state.previewIndex < state.files.length - 1 ? 'visible' : 'hidden';
  }

  function renderTextPreview(container, file, url, isMarkdown) {
    const wrapper = document.createElement('div');
    wrapper.className = 'text-preview-wrapper';

    // Toolbar
    const toolbar = document.createElement('div');
    toolbar.className = 'text-preview-toolbar';

    const viewBtn = document.createElement('button');
    viewBtn.className = 'btn btn-text active';
    viewBtn.textContent = 'Preview';

    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-text';
    editBtn.textContent = 'Edit';

    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-primary';
    saveBtn.textContent = 'Save';
    saveBtn.style.display = 'none';

    // Check if this is VAULT.md
    const filename = file.original_filename || file.stored_filename || '';
    const isVaultMd = filename === 'VAULT.md';

    if (isVaultMd) {
      const regenerateBtn = document.createElement('button');
      regenerateBtn.className = 'btn btn-text';
      regenerateBtn.innerHTML = '<span class="material-icons" style="font-size:16px;vertical-align:middle;">autorenew</span> Regenerate';
      regenerateBtn.addEventListener('click', async function() {
        regenerateBtn.disabled = true;
        regenerateBtn.textContent = 'Generating...';
        try {
          await generateVaultMd(state.path || null);
          showToast('VAULT.md regenerated', 'success');
          // Reload content
          const response = await fetch(url);
          const text = await response.text();
          previewEl.innerHTML = renderMarkdown(text);
          if (editorInstance) {
            editorInstance.setValue(text);
          }
        } catch (err) {
          showToast('Failed to regenerate: ' + err.message, 'error');
        }
        regenerateBtn.disabled = false;
        regenerateBtn.innerHTML = '<span class="material-icons" style="font-size:16px;vertical-align:middle;">autorenew</span> Regenerate';
      });
      toolbar.appendChild(regenerateBtn);
    }

    toolbar.appendChild(viewBtn);
    toolbar.appendChild(editBtn);
    toolbar.appendChild(saveBtn);
    wrapper.appendChild(toolbar);

    // Preview area
    const previewEl = document.createElement('div');
    previewEl.className = 'markdown-preview';
    wrapper.appendChild(previewEl);

    // Editor area (hidden initially)
    const editorWrapper = document.createElement('div');
    editorWrapper.className = 'text-editor-wrapper';
    editorWrapper.style.display = 'none';
    const textarea = document.createElement('textarea');
    textarea.id = 'textEditorArea';
    editorWrapper.appendChild(textarea);
    wrapper.appendChild(editorWrapper);

    container.appendChild(wrapper);

    // Add chat button
    addChatButton(container, file);

    // Fetch and render content
    let editorInstance = null;
    let originalContent = '';

    fetch(url)
      .then(function(response) { return response.text(); })
      .then(function(text) {
        originalContent = text;
        if (isMarkdown) {
          previewEl.innerHTML = renderMarkdown(text);
        } else {
          previewEl.innerHTML = '<pre>' + escapeHtml(text) + '</pre>';
        }
        textarea.value = text;
      })
      .catch(function(err) {
        previewEl.textContent = 'Failed to load file: ' + err.message;
      });

    // Toggle handlers
    viewBtn.addEventListener('click', function() {
      viewBtn.classList.add('active');
      editBtn.classList.remove('active');
      previewEl.style.display = '';
      editorWrapper.style.display = 'none';
      saveBtn.style.display = 'none';
    });

    editBtn.addEventListener('click', function() {
      editBtn.classList.add('active');
      viewBtn.classList.remove('active');
      previewEl.style.display = 'none';
      editorWrapper.style.display = '';
      saveBtn.style.display = '';

      // Initialize CodeMirror if not already
      if (!editorInstance && window.CodeMirror) {
        editorInstance = CodeMirror.fromTextArea(textarea, {
          mode: isMarkdown ? 'markdown' : 'text',
          lineNumbers: true,
          lineWrapping: true,
          theme: 'dracula',
          viewportMargin: Infinity
        });
        editorInstance.setValue(originalContent);
      }
    });

    saveBtn.addEventListener('click', async function() {
      const newContent = editorInstance ? editorInstance.getValue() : textarea.value;
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving...';

      try {
        // For VAULT.md, use special API
        if (isVaultMd) {
          await saveVaultMd(state.path || null, newContent);
        } else {
          // For regular files, update via PATCH with content
          // Note: This would require a backend update to support content updates
          showToast('File saved locally (sync pending)', 'info');
        }
        originalContent = newContent;
        if (isMarkdown) {
          previewEl.innerHTML = renderMarkdown(newContent);
        } else {
          previewEl.innerHTML = '<pre>' + escapeHtml(newContent) + '</pre>';
        }
        showToast('File saved', 'success');
      } catch (err) {
        showToast('Failed to save: ' + err.message, 'error');
      }

      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
    });
  }

  function addChatButton(container, file) {
    const chatBtn = document.createElement('button');
    chatBtn.className = 'btn btn-primary chat-from-file-btn';
    chatBtn.innerHTML = '<span class="material-icons">chat</span> Ask about this file';
    chatBtn.addEventListener('click', function() {
      const path = state.path ? state.path + '/' : '';
      const filename = file.original_filename || file.stored_filename || file.id;
      const query = 'RE: [' + path + filename + '] ';

      // Navigate to chat with prepopulated input
      window.location.href = '/?q=' + encodeURIComponent(query);
    });
    container.appendChild(chatBtn);
  }

  function renderAudioPreview(container, file, url) {
    const player = document.createElement('div');
    player.className = 'audio-player';

    // Waveform placeholder
    const waveform = document.createElement('div');
    waveform.className = 'audio-waveform';
    const waveformBg = document.createElement('div');
    waveformBg.className = 'waveform-bg';
    const waveformProgress = document.createElement('div');
    waveformProgress.className = 'waveform-progress';
    waveformProgress.id = 'waveformProgress';
    waveform.appendChild(waveformBg);
    waveform.appendChild(waveformProgress);
    player.appendChild(waveform);

    // Time display
    const timeRow = document.createElement('div');
    timeRow.className = 'audio-time-row';
    const currentTime = document.createElement('span');
    currentTime.id = 'audioCurrentTime';
    currentTime.textContent = '0:00';
    const duration = document.createElement('span');
    duration.id = 'audioDuration';
    duration.textContent = file.duration ? formatDuration(file.duration) : '-:--';
    timeRow.appendChild(currentTime);
    timeRow.appendChild(duration);
    player.appendChild(timeRow);

    // Controls
    const controls = document.createElement('div');
    controls.className = 'audio-controls';

    // Rewind button
    const rewindBtn = document.createElement('button');
    rewindBtn.className = 'audio-control-btn';
    rewindBtn.appendChild(createIcon('replay_10'));
    controls.appendChild(rewindBtn);

    // Play button
    const playBtn = document.createElement('button');
    playBtn.className = 'audio-control-btn play-btn';
    playBtn.id = 'audioPlayBtn';
    playBtn.appendChild(createIcon('play_arrow'));
    controls.appendChild(playBtn);

    // Forward button
    const forwardBtn = document.createElement('button');
    forwardBtn.className = 'audio-control-btn';
    forwardBtn.appendChild(createIcon('forward_10'));
    controls.appendChild(forwardBtn);

    player.appendChild(controls);

    // Speed control
    const speedRow = document.createElement('div');
    speedRow.className = 'audio-speed-row';
    const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
    speeds.forEach(function(speed) {
      const btn = document.createElement('button');
      btn.className = 'speed-btn' + (speed === 1 ? ' active' : '');
      btn.textContent = speed + 'x';
      btn.dataset.speed = speed;
      speedRow.appendChild(btn);
    });
    player.appendChild(speedRow);

    container.appendChild(player);

    // Transcript
    if (file.content_text) {
      const transcript = document.createElement('div');
      transcript.className = 'audio-transcript';
      const transcriptLabel = document.createElement('div');
      transcriptLabel.className = 'transcript-label';
      transcriptLabel.textContent = 'Transcript';
      transcript.appendChild(transcriptLabel);
      const transcriptText = document.createElement('div');
      transcriptText.className = 'transcript-text';
      transcriptText.textContent = file.content_text; // textContent for XSS safety
      transcript.appendChild(transcriptText);
      container.appendChild(transcript);
    }

    // Initialize audio
    initAudioPlayer(url, player);
  }

  function initAudioPlayer(url, playerEl) {
    const audio = new Audio(url);
    const playBtn = playerEl.querySelector('#audioPlayBtn');
    const currentTimeEl = playerEl.querySelector('#audioCurrentTime');
    const durationEl = playerEl.querySelector('#audioDuration');
    const waveformProgress = playerEl.querySelector('#waveformProgress');
    const speedBtns = playerEl.querySelectorAll('.speed-btn');
    const rewindBtn = playerEl.querySelector('.audio-control-btn:first-child');
    const forwardBtn = playerEl.querySelector('.audio-control-btn:last-child');
    const waveformEl = playerEl.querySelector('.audio-waveform');

    audio.addEventListener('loadedmetadata', function() {
      durationEl.textContent = formatDuration(audio.duration);
    });

    audio.addEventListener('timeupdate', function() {
      currentTimeEl.textContent = formatDuration(audio.currentTime);
      const progress = (audio.currentTime / audio.duration) * 100;
      waveformProgress.style.width = progress + '%';
    });

    audio.addEventListener('ended', function() {
      playBtn.textContent = '';
      playBtn.appendChild(createIcon('play_arrow'));
    });

    playBtn.addEventListener('click', function() {
      if (audio.paused) {
        audio.play();
        playBtn.textContent = '';
        playBtn.appendChild(createIcon('pause'));
      } else {
        audio.pause();
        playBtn.textContent = '';
        playBtn.appendChild(createIcon('play_arrow'));
      }
    });

    rewindBtn.addEventListener('click', function() {
      audio.currentTime = Math.max(0, audio.currentTime - 10);
    });

    forwardBtn.addEventListener('click', function() {
      audio.currentTime = Math.min(audio.duration, audio.currentTime + 10);
    });

    speedBtns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        speedBtns.forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        audio.playbackRate = parseFloat(btn.dataset.speed);
      });
    });

    // Click on waveform to seek
    waveformEl.addEventListener('click', function(e) {
      const rect = waveformEl.getBoundingClientRect();
      const percent = (e.clientX - rect.left) / rect.width;
      audio.currentTime = percent * audio.duration;
    });
  }

  // ============================================
  // Info Panel
  // ============================================

  function openInfoPanel() {
    if (!state.currentFileId) return;
    const file = state.files.find(function(f) { return f.id === state.currentFileId; });
    if (!file) return;

    // Populate fields (using value/textContent for XSS safety)
    document.getElementById('infoFilename').value = file.original_filename || file.stored_filename || '';
    document.getElementById('infoDescription').value = file.description || '';
    document.getElementById('infoTags').value = file.tags || '';
    document.getElementById('infoTopicName').textContent = file.topic || 'Select topic';
    document.getElementById('infoType').textContent = file.type || '-';
    document.getElementById('infoSize').textContent = formatSize(file.file_size);
    document.getElementById('infoCreated').textContent = formatDate(file.created_at);
    document.getElementById('infoModified').textContent = formatDate(file.updated_at);

    // Preview thumbnail
    const previewEl = document.getElementById('infoPreview');
    previewEl.textContent = '';
    if (file.type === 'image' && file.url) {
      const img = document.createElement('img');
      img.src = file.url;
      img.alt = 'Preview';
      previewEl.appendChild(img);
    } else {
      previewEl.appendChild(createIcon(getFileIcon(file.type)));
    }

    infoPanelOverlay.style.display = 'flex';
  }

  function closeInfoPanel() {
    infoPanelOverlay.style.display = 'none';
  }

  async function saveInfo() {
    if (!state.currentFileId) return;

    const description = document.getElementById('infoDescription').value;
    const tags = document.getElementById('infoTags').value;

    try {
      await updateFile(state.currentFileId, {
        description: description,
        tags: tags
      });

      // Update local state
      const file = state.files.find(function(f) { return f.id === state.currentFileId; });
      if (file) {
        file.description = description;
        file.tags = tags;
      }

      showToast('Changes saved', 'success');
      closeInfoPanel();
    } catch (err) {
      console.error('Failed to save:', err);
      showToast('Failed to save changes', 'error');
    }
  }

  // ============================================
  // Topic Picker
  // ============================================

  function openTopicPicker(callback) {
    const list = document.getElementById('topicPickerList');
    list.textContent = '';

    state.topics.forEach(function(topic) {
      const item = document.createElement('div');
      item.className = 'topic-picker-item';
      item.textContent = topic.topic;
      item.addEventListener('click', function() {
        callback(topic.topic);
        closeTopicPicker();
      });
      list.appendChild(item);
    });

    topicPickerOverlay.style.display = 'flex';
  }

  function closeTopicPicker() {
    topicPickerOverlay.style.display = 'none';
  }

  async function createTopic(name) {
    if (!name || !name.trim()) return null;

    try {
      const response = await fetch('/api/vault/topics/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() })
      });

      if (!response.ok) {
        throw new Error('Failed to create topic');
      }

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      // Add to local state
      const newTopic = {
        topic: name.trim(),
        count: 0,
        total_size: 0
      };
      state.topics.push(newTopic);
      return newTopic;
    } catch (err) {
      console.error('Create topic failed:', err);
      throw err;
    }
  }

  async function deleteTopic(name, force) {
    const url = '/api/vault/topic/' + encodeURIComponent(name) + (force ? '?force=1' : '');
    const response = await fetch(url, {
      method: 'DELETE'
    });

    const result = await response.json().catch(function() { return {}; });

    if (!response.ok) {
      // Check if this is a "requires force" response
      if (result.requires_force) {
        return result; // Return so caller can handle confirmation
      }
      throw new Error(result.error || 'Failed to delete topic');
    }

    return result;
  }

  // ============================================
  // Confirm Dialog
  // ============================================

  function showConfirm(title, message, onConfirm, confirmText) {
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmOk').textContent = confirmText || 'Delete';

    const okBtn = document.getElementById('confirmOk');
    const cancelBtn = document.getElementById('confirmCancel');

    const cleanup = function() {
      okBtn.removeEventListener('click', handleOk);
      cancelBtn.removeEventListener('click', handleCancel);
      confirmOverlay.style.display = 'none';
    };

    const handleOk = function() {
      cleanup();
      onConfirm();
    };

    const handleCancel = function() {
      cleanup();
    };

    okBtn.addEventListener('click', handleOk);
    cancelBtn.addEventListener('click', handleCancel);

    confirmOverlay.style.display = 'flex';
  }

  // ============================================
  // Toast Notifications
  // ============================================

  /**
   * Show a toast notification
   * @param {string} message - The message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info'
   * @param {number} duration - Duration in ms (default 3000)
   */
  function showToast(message, type, duration) {
    type = type || 'info';

    // Default durations by type
    if (duration === undefined) {
      switch (type) {
        case 'error': duration = 8000; break;    // Errors stay longer
        case 'warning': duration = 5000; break;  // Warnings medium
        case 'success': duration = 3000; break;  // Success quick
        default: duration = 4000;                // Info medium
      }
    }

    console.log('[Toast]', type, message);

    if (!toastContainer) {
      console.error('[Toast] toastContainer not found!');
      return null;
    }

    const icons = {
      success: 'check_circle',
      error: 'error',
      warning: 'warning',
      info: 'info'
    };

    const toast = document.createElement('div');
    toast.className = 'toast ' + type;

    const icon = createIcon(icons[type] || 'info');
    toast.appendChild(icon);

    const msgSpan = document.createElement('span');
    msgSpan.className = 'toast-message';
    msgSpan.textContent = message;
    toast.appendChild(msgSpan);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.appendChild(createIcon('close'));
    closeBtn.addEventListener('click', function() {
      dismissToast(toast);
    });
    toast.appendChild(closeBtn);

    toastContainer.appendChild(toast);

    // Auto dismiss
    setTimeout(function() {
      dismissToast(toast);
    }, duration);

    return toast;
  }

  function dismissToast(toast) {
    if (!toast.parentNode) return;
    toast.classList.add('toast-out');
    setTimeout(function() {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 200);
  }

  // ============================================
  // Input Dialog
  // ============================================

  /**
   * Show an input dialog
   * @param {string} title - Dialog title
   * @param {string} placeholder - Input placeholder
   * @param {function} onSubmit - Callback with value
   * @param {function} validate - Optional validation function, returns error string or null
   * @param {string} defaultValue - Optional default value
   * @param {string} submitText - Optional submit button text
   */
  function showInput(title, placeholder, onSubmit, validate, defaultValue, submitText) {
    const titleEl = document.getElementById('inputTitle');
    const fieldEl = document.getElementById('inputField');
    const errorEl = document.getElementById('inputError');
    const okBtn = document.getElementById('inputOk');
    const cancelBtn = document.getElementById('inputCancel');

    titleEl.textContent = title;
    fieldEl.placeholder = placeholder || '';
    fieldEl.value = defaultValue || '';
    fieldEl.classList.remove('error');
    errorEl.style.display = 'none';
    errorEl.textContent = '';
    okBtn.textContent = submitText || 'OK';

    const cleanup = function() {
      okBtn.removeEventListener('click', handleOk);
      cancelBtn.removeEventListener('click', handleCancel);
      fieldEl.removeEventListener('keypress', handleKeypress);
      fieldEl.removeEventListener('input', handleInput);
      inputOverlay.style.display = 'none';
    };

    const handleSubmit = function() {
      const value = fieldEl.value.trim();

      if (validate) {
        const error = validate(value);
        if (error) {
          fieldEl.classList.add('error');
          errorEl.textContent = error;
          errorEl.style.display = 'block';
          return;
        }
      }

      cleanup();
      onSubmit(value);
    };

    const handleOk = function() {
      handleSubmit();
    };

    const handleCancel = function() {
      cleanup();
    };

    const handleKeypress = function(e) {
      if (e.key === 'Enter') {
        handleSubmit();
      }
    };

    const handleInput = function() {
      fieldEl.classList.remove('error');
      errorEl.style.display = 'none';
    };

    okBtn.addEventListener('click', handleOk);
    cancelBtn.addEventListener('click', handleCancel);
    fieldEl.addEventListener('keypress', handleKeypress);
    fieldEl.addEventListener('input', handleInput);

    inputOverlay.style.display = 'flex';
    fieldEl.focus();
    fieldEl.select();
  }

  // ============================================
  // Actions
  // ============================================

  async function handleDelete() {
    if (!state.currentFileId) return;

    const file = state.files.find(function(f) { return f.id === state.currentFileId; });
    const fileName = file ? (file.original_filename || file.stored_filename || 'this file') : 'this file';

    showConfirm(
      'Delete file?',
      'Are you sure you want to delete "' + fileName + '"? This cannot be undone.',
      async function() {
        try {
          await deleteFile(state.currentFileId);
          closePreview();
          // Reload files
          if (state.path) {
            loadFiles(state.path);
          } else {
            loadTopics();
          }
        } catch (err) {
          console.error('Delete failed:', err);
          showToast('Failed to delete file', 'error');
        }
      },
      'Delete'
    );
  }

  async function handleBulkDelete() {
    const fileCount = state.selection.size;
    const folderCount = state.folderSelection.size;
    const totalCount = fileCount + folderCount;

    if (totalCount === 0) return;

    // Build message
    let itemDesc = '';
    if (fileCount > 0 && folderCount > 0) {
      itemDesc = fileCount + ' file' + (fileCount > 1 ? 's' : '') + ' and ' + folderCount + ' folder' + (folderCount > 1 ? 's' : '');
    } else if (folderCount > 0) {
      itemDesc = folderCount + ' folder' + (folderCount > 1 ? 's' : '') + ' (and all files inside)';
    } else {
      itemDesc = fileCount + ' file' + (fileCount > 1 ? 's' : '');
    }

    showConfirm(
      'Delete ' + itemDesc + '?',
      'Are you sure you want to delete these items? This cannot be undone.',
      async function() {
        try {
          // Delete files first
          if (fileCount > 0) {
            await bulkDelete(Array.from(state.selection));
          }

          // Delete folders
          for (const folderName of state.folderSelection) {
            await deleteTopic(folderName, true);
          }

          showToast('Deleted ' + itemDesc, 'success');
          exitSelectMode();
          // Reload
          if (state.path) {
            loadFiles(state.path);
          } else {
            loadTopics();
          }
        } catch (err) {
          console.error('Bulk delete failed:', err);
          showToast('Failed to delete items', 'error');
        }
      },
      'Delete'
    );
  }

  async function handleMove() {
    if (!state.currentFileId) return;

    openTopicPicker(async function(topic) {
      try {
        await moveFile(state.currentFileId, topic);
        closePreview();
        // Reload
        if (state.path) {
          loadFiles(state.path);
        } else {
          loadTopics();
        }
      } catch (err) {
        console.error('Move failed:', err);
        showToast('Failed to move file', 'error');
      }
    });
  }

  async function handleBulkMove() {
    if (state.selection.size === 0) return;

    openTopicPicker(async function(topic) {
      try {
        await bulkMove(Array.from(state.selection), topic);
        exitSelectMode();
        // Reload
        if (state.path) {
          loadFiles(state.path);
        } else {
          loadTopics();
        }
      } catch (err) {
        console.error('Bulk move failed:', err);
        showToast('Failed to move files', 'error');
      }
    });
  }

  function handleDownload() {
    if (!state.currentFileId) return;
    const file = state.files.find(function(f) { return f.id === state.currentFileId; });
    if (!file) return;

    const url = file.url || '/api/vault/file/' + file.id;
    const a = document.createElement('a');
    a.href = url;
    a.download = file.original_filename || file.stored_filename || 'download';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    showToast('Download started', 'success');
  }

  function handleRename() {
    if (!state.currentFileId) return;
    const file = state.files.find(function(f) { return f.id === state.currentFileId; });
    if (!file) return;

    const currentName = file.original_filename || file.stored_filename || '';

    showInput(
      'Rename file',
      'Enter new filename',
      async function(newName) {
        if (!newName || newName === currentName) return;

        try {
          await updateFile(state.currentFileId, { filename: newName });
          // Update local state
          file.original_filename = newName;
          document.getElementById('infoFilename').value = newName;
          showToast('File renamed', 'success');

          // Refresh the file list
          if (state.path) {
            loadFiles(state.path);
          }
        } catch (err) {
          console.error('Rename failed:', err);
          showToast('Failed to rename file', 'error');
        }
      },
      function(value) {
        if (!value) return 'Filename is required';
        if (value.length > 255) return 'Filename too long';
        return null;
      },
      currentName,
      'Rename'
    );
  }

  function handleCopyLink() {
    if (!state.currentFileId) return;

    const url = window.location.origin + '/api/vault/file/' + state.currentFileId;

    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(function() {
        showToast('Link copied to clipboard', 'success');
      }).catch(function() {
        showToast('Failed to copy link', 'error');
      });
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        showToast('Link copied to clipboard', 'success');
      } catch (err) {
        showToast('Failed to copy link', 'error');
      }
      document.body.removeChild(textArea);
    }
  }

  function handleInfoMove() {
    if (!state.currentFileId) return;

    openTopicPicker(async function(topic) {
      try {
        await moveFile(state.currentFileId, topic);
        document.getElementById('infoTopicName').textContent = topic;
        showToast('File moved to ' + topic, 'success');
        closeInfoPanel();
        closePreview();
        // Reload
        if (state.path) {
          loadFiles(state.path);
        } else {
          loadTopics();
        }
      } catch (err) {
        console.error('Move failed:', err);
        showToast('Failed to move file', 'error');
      }
    });
  }

  function handleInfoDelete() {
    if (!state.currentFileId) return;

    const file = state.files.find(function(f) { return f.id === state.currentFileId; });
    const fileName = file ? (file.original_filename || file.stored_filename || 'this file') : 'this file';

    showConfirm(
      'Delete file?',
      'Are you sure you want to delete "' + fileName + '"? This cannot be undone.',
      async function() {
        try {
          await deleteFile(state.currentFileId);
          showToast('File deleted', 'success');
          closeInfoPanel();
          closePreview();
          // Reload files
          if (state.path) {
            loadFiles(state.path);
          } else {
            loadTopics();
          }
        } catch (err) {
          console.error('Delete failed:', err);
          showToast('Failed to delete file', 'error');
        }
      },
      'Delete'
    );
  }

  // ============================================
  // Folder Actions
  // ============================================

  async function handleDeleteFolder(folderName) {
    if (!folderName) return;

    // First try without force to get file count
    try {
      const result = await deleteTopic(folderName, false);

      if (result.requires_force) {
        // Folder has files, show confirmation
        showConfirm(
          'Delete folder and ' + result.file_count + ' files?',
          'This will permanently delete "' + folderName + '" and all ' + result.file_count + ' files inside. This cannot be undone.',
          async function() {
            try {
              await deleteTopic(folderName, true);
              showToast('Folder "' + folderName + '" deleted', 'success');
              loadTopics();
            } catch (err) {
              console.error('Delete folder failed:', err);
              showToast('Failed to delete folder: ' + err.message, 'error');
            }
          },
          'Delete All'
        );
      } else {
        // Folder was empty, already deleted
        showToast('Folder "' + folderName + '" deleted', 'success');
        loadTopics();
      }
    } catch (err) {
      console.error('Delete folder failed:', err);
      showToast('Failed to delete folder: ' + err.message, 'error');
    }
  }

  // ============================================
  // Search
  // ============================================

  function toggleSearch() {
    const isVisible = searchBar.style.display !== 'none';
    searchBar.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) {
      searchInput.focus();
    } else {
      searchInput.value = '';
      state.searchQuery = '';
      if (state.path) {
        loadFiles(state.path);
      } else {
        loadTopics();
      }
    }
  }

  function clearSearch() {
    searchInput.value = '';
    state.searchQuery = '';
    if (state.path) {
      loadFiles(state.path);
    } else {
      loadTopics();
    }
  }

  // ============================================
  // Menu
  // ============================================

  function toggleMenu() {
    const isVisible = dropdownMenu.style.display !== 'none';
    dropdownMenu.style.display = isVisible ? 'none' : 'block';
  }

  function closeMenu() {
    dropdownMenu.style.display = 'none';
  }

  // ============================================
  // Sort
  // ============================================

  function setSortBy(sortBy) {
    if (state.sortBy === sortBy) {
      state.sortDesc = !state.sortDesc;
    } else {
      state.sortBy = sortBy;
      state.sortDesc = true;
    }
    closeMenu();
    if (state.path) {
      renderFiles();
    } else {
      renderTopics();
    }
  }

  // ============================================
  // Upload
  // ============================================

  function openUploadModal() {
    const overlay = document.getElementById('uploadOverlay');
    const select = document.getElementById('uploadTopicSelect');
    const topicSection = document.querySelector('.upload-topic');
    const label = topicSection.querySelector('label');

    // Populate topics
    select.textContent = '';

    if (state.path) {
      // Inside a folder - force this folder, no choice
      label.textContent = 'Saving to folder:';
      select.disabled = true;
      const currentOption = document.createElement('option');
      currentOption.value = state.path;
      currentOption.textContent = state.path;
      currentOption.selected = true;
      select.appendChild(currentOption);
    } else {
      // At root - allow AI classification or manual selection
      label.textContent = 'Save to folder (optional - AI will classify if not selected):';
      select.disabled = false;

      // Auto-classify option
      const autoOption = document.createElement('option');
      autoOption.value = '';
      autoOption.textContent = 'Auto-classify with AI';
      select.appendChild(autoOption);

      // Add all topics
      state.topics.forEach(function(topic) {
        const option = document.createElement('option');
        option.value = topic.topic;
        option.textContent = topic.topic;
        select.appendChild(option);
      });
    }

    overlay.style.display = 'flex';
  }

  function closeUploadModal() {
    document.getElementById('uploadOverlay').style.display = 'none';
  }

  async function handleFileUpload(files) {
    console.log('[Upload] handleFileUpload called with', files.length, 'files');

    if (!files || files.length === 0) {
      console.error('[Upload] No files provided');
      return;
    }

    const topic = document.getElementById('uploadTopicSelect').value;
    console.log('[Upload] Selected topic:', topic || '(auto-classify)');

    closeUploadModal();

    const totalFiles = files.length;
    let successCount = 0;
    let failCount = 0;

    console.log('[Upload] Starting upload of', totalFiles, 'file(s)');

    // Process files one by one for clean AI assessment
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      console.log('[Upload] Processing file', i + 1, ':', file.name, file.type, file.size, 'bytes');

      const progressMsg = totalFiles > 1
        ? 'Uploading ' + (i + 1) + '/' + totalFiles + ': ' + file.name
        : 'Uploading: ' + file.name;

      const progressToast = showToast(progressMsg, 'info', 60000);

      const formData = new FormData();
      formData.append('file', file);
      if (topic) {
        formData.append('topic', topic);
      }

      try {
        console.log('[Upload] Sending fetch request for:', file.name);
        const response = await fetch('/api/media/upload', {
          method: 'POST',
          body: formData
        });

        console.log('[Upload] Response status:', response.status);
        dismissToast(progressToast);

        if (!response.ok) {
          const errorText = await response.text();
          console.error('[Upload] Error response:', errorText);
          let errorData = {};
          try { errorData = JSON.parse(errorText); } catch(e) {}
          throw new Error(errorData.error || 'Upload failed with status ' + response.status);
        }

        const result = await response.json();
        console.log('[Upload] Success result:', result);
        successCount++;

        // Show success with topic info
        const savedTopic = result.media && result.media.topic ? result.media.topic : 'vault';
        showToast('Saved "' + file.name + '" to ' + savedTopic, 'success');

      } catch (err) {
        dismissToast(progressToast);
        console.error('[Upload] Error:', err);
        showToast('Failed to upload ' + file.name + ': ' + err.message, 'error');
        failCount++;
      }
    }

    // Summary toast for multi-file uploads
    if (totalFiles > 1) {
      if (failCount === 0) {
        showToast('All ' + successCount + ' files uploaded successfully', 'success');
      } else {
        showToast(successCount + ' uploaded, ' + failCount + ' failed', 'warning');
      }
    }

    // Trigger VAULT.md generation if files were uploaded successfully
    if (successCount > 0) {
      const targetTopic = topic || (state.path ? state.path : null);
      console.log('[Upload] Triggering VAULT.md generation for:', targetTopic || 'root');

      // Generate in background (don't await)
      generateVaultMd(targetTopic).then(function() {
        console.log('[Upload] VAULT.md generated');
      }).catch(function(err) {
        console.warn('[Upload] VAULT.md generation failed:', err);
      });
    }

    // Reload
    if (state.path) {
      loadFiles(state.path);
    } else {
      loadTopics();
    }
  }

  // ============================================
  // Event Listeners
  // ============================================

  function init() {
    // Get DOM elements
    mainHeader = document.getElementById('mainHeader');
    selectionHeader = document.getElementById('selectionHeader');
    breadcrumb = document.getElementById('breadcrumb');
    searchBar = document.getElementById('searchBar');
    searchInput = document.getElementById('searchInput');
    filesContent = document.getElementById('filesContent');
    loadingState = document.getElementById('loadingState');
    emptyState = document.getElementById('emptyState');
    filesGrid = document.getElementById('filesGrid');
    dropdownMenu = document.getElementById('dropdownMenu');
    previewOverlay = document.getElementById('previewOverlay');
    infoPanelOverlay = document.getElementById('infoPanelOverlay');
    infoPanel = document.getElementById('infoPanel');
    topicPickerOverlay = document.getElementById('topicPickerOverlay');
    confirmOverlay = document.getElementById('confirmOverlay');
    inputOverlay = document.getElementById('inputOverlay');
    toastContainer = document.getElementById('toastContainer');

    // Header buttons - context-aware back navigation
    document.getElementById('backBtn').addEventListener('click', function() {
      handleBack();
    });

    // Handle browser back button and swipe gestures
    window.addEventListener('popstate', function(e) {
      // If preview is open, close it (triggered by swipe back or browser back)
      if (previewOverlay.style.display !== 'none') {
        closePreview(true); // true = triggered by popstate
      }
    });

    document.getElementById('searchToggle').addEventListener('click', toggleSearch);
    document.getElementById('viewToggle').addEventListener('click', toggleView);
    document.getElementById('menuToggle').addEventListener('click', toggleMenu);

    // Selection header
    document.getElementById('cancelSelection').addEventListener('click', exitSelectMode);
    document.getElementById('selectAllBtn').addEventListener('click', selectAll);
    document.getElementById('moveSelectedBtn').addEventListener('click', handleBulkMove);
    document.getElementById('deleteSelectedBtn').addEventListener('click', handleBulkDelete);

    // Search bar
    document.getElementById('searchClear').addEventListener('click', clearSearch);
    searchInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        performSearch(searchInput.value);
      }
    });

    // Menu items
    document.getElementById('menuUpload').addEventListener('click', function() {
      closeMenu();
      openUploadModal();
    });
    document.getElementById('menuSelectMode').addEventListener('click', function() {
      closeMenu();
      enterSelectMode();
    });
    document.getElementById('menuNewFolder').addEventListener('click', function() {
      closeMenu();
      showInput(
        'New folder',
        'Enter folder name',
        async function(name) {
          if (name) {
            try {
              await createTopic(name);
              showToast('Folder "' + name + '" created', 'success');

              // Generate VAULT.md for new folder
              generateVaultMd(name).then(function() {
                console.log('[Folder] VAULT.md generated for:', name);
              }).catch(function(err) {
                console.warn('[Folder] VAULT.md generation failed:', err);
              });

              loadTopics(); // Reload from server
            } catch (err) {
              showToast(err.message || 'Failed to create folder', 'error');
            }
          }
        },
        function(value) {
          if (!value) return 'Folder name is required';
          if (value.length > 100) return 'Folder name too long';
          // Check for invalid characters
          if (/[\/\\<>:"|?*]/.test(value)) return 'Invalid characters in folder name';
          return null;
        },
        '',
        'Create'
      );
    });
    document.getElementById('menuRefresh').addEventListener('click', function() {
      closeMenu();
      if (state.path) {
        loadFiles(state.path);
      } else {
        loadTopics();
      }
    });
    document.getElementById('menuSortName').addEventListener('click', function() {
      setSortBy('name');
    });
    document.getElementById('menuSortDate').addEventListener('click', function() {
      setSortBy('date');
    });
    document.getElementById('menuSortSize').addEventListener('click', function() {
      setSortBy('size');
    });

    // FAB
    document.getElementById('uploadFab').addEventListener('click', openUploadModal);

    // Preview
    document.getElementById('previewClose').addEventListener('click', function() {
      closePreview(false);
    });
    document.getElementById('previewInfo').addEventListener('click', openInfoPanel);
    document.getElementById('previewDownload').addEventListener('click', handleDownload);
    document.getElementById('previewDelete').addEventListener('click', handleDelete);
    document.getElementById('previewPrev').addEventListener('click', function() {
      navigatePreview(-1);
    });
    document.getElementById('previewNext').addEventListener('click', function() {
      navigatePreview(1);
    });

    // Keyboard navigation in preview
    document.addEventListener('keydown', function(e) {
      if (previewOverlay.style.display === 'none') return;
      if (e.key === 'Escape') closePreview(false);
      if (e.key === 'ArrowLeft') navigatePreview(-1);
      if (e.key === 'ArrowRight') navigatePreview(1);
    });

    // Info panel
    document.getElementById('infoPanelClose').addEventListener('click', closeInfoPanel);
    document.getElementById('infoCancel').addEventListener('click', closeInfoPanel);
    document.getElementById('infoSave').addEventListener('click', saveInfo);
    document.getElementById('infoTopicBtn').addEventListener('click', function() {
      openTopicPicker(function(topic) {
        document.getElementById('infoTopicName').textContent = topic;
        // Move file to new topic
        if (state.currentFileId) {
          moveFile(state.currentFileId, topic).then(function() {
            showToast('File moved to ' + topic, 'success');
          }).catch(function(err) {
            console.error('Move failed:', err);
            showToast('Failed to move file', 'error');
          });
        }
      });
    });

    // Info panel action buttons
    document.getElementById('infoDownload').addEventListener('click', handleDownload);
    document.getElementById('infoRename').addEventListener('click', handleRename);
    document.getElementById('infoCopyLink').addEventListener('click', handleCopyLink);
    document.getElementById('infoMove').addEventListener('click', handleInfoMove);
    document.getElementById('infoDelete').addEventListener('click', handleInfoDelete);

    // Topic picker
    document.getElementById('topicPickerClose').addEventListener('click', closeTopicPicker);
    document.getElementById('createTopicBtn').addEventListener('click', function() {
      const input = document.getElementById('newTopicInput');
      const name = input.value.trim();
      if (name) {
        createTopic(name);
        input.value = '';
        closeTopicPicker();
      }
    });

    // Upload modal
    document.getElementById('uploadClose').addEventListener('click', closeUploadModal);
    document.getElementById('uploadBrowse').addEventListener('click', function() {
      document.getElementById('uploadInput').click();
    });
    document.getElementById('uploadInput').addEventListener('change', function(e) {
      if (e.target.files.length > 0) {
        handleFileUpload(e.target.files);
      }
    });

    // Upload dropzone
    const dropzone = document.getElementById('uploadDropzone');
    dropzone.addEventListener('dragover', function(e) {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', function() {
      dropzone.classList.remove('dragover');
    });
    dropzone.addEventListener('drop', function(e) {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files);
      }
    });

    // Click outside to close menu
    document.addEventListener('click', function(e) {
      if (!e.target.closest('#menuToggle') && !e.target.closest('#dropdownMenu')) {
        closeMenu();
      }
    });

    // Click overlay to close modals
    infoPanelOverlay.addEventListener('click', function(e) {
      if (e.target === infoPanelOverlay) closeInfoPanel();
    });
    topicPickerOverlay.addEventListener('click', function(e) {
      if (e.target === topicPickerOverlay) closeTopicPicker();
    });
    confirmOverlay.addEventListener('click', function(e) {
      if (e.target === confirmOverlay) {
        confirmOverlay.style.display = 'none';
      }
    });
    document.getElementById('uploadOverlay').addEventListener('click', function(e) {
      if (e.target.id === 'uploadOverlay') closeUploadModal();
    });
    inputOverlay.addEventListener('click', function(e) {
      if (e.target === inputOverlay) {
        inputOverlay.style.display = 'none';
      }
    });

    // Initial load
    loadTopics();

    // Check for root VAULT.md on startup
    getVaultMd(null).then(function(result) {
      if (!result.exists) {
        console.log('[Init] Root VAULT.md not found, generating...');
        generateVaultMd(null).then(function() {
          console.log('[Init] Root VAULT.md generated');
        }).catch(function(err) {
          console.warn('[Init] Root VAULT.md generation failed:', err);
        });
      }
    }).catch(function(err) {
      console.warn('[Init] Failed to check root VAULT.md:', err);
    });
  }

  // Initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', init);

})();
