/**
 * ATHENA AI Assistant - Frontend
 * Multi-session support with thinking bubbles and Material Design
 *
 * Security Note: innerHTML is used intentionally for assistant messages because
 * the HTML is generated server-side by converting markdown with goldmark library.
 * User input is always rendered with textContent for XSS prevention.
 */
(function() {
  'use strict';

  // Configuration
  const MAX_RECORDING_SEC = 20;
  const API_BASE = '';
  const SESSIONS_KEY = 'alfred_sessions';
  const CURRENT_SESSION_KEY = 'alfred_current_session';
  const PENDING_JOB_KEY = 'alfred_pending_job'; // {jobId, threadId}
  const JOB_POLL_INTERVAL = 3000; // 3 seconds

  // State
  let mediaRecorder = null;
  let audioChunks = [];
  let recordingTimer = null;
  let recordingStartTime = null;
  let currentAudio = null;
  let pttState = 'idle'; // idle, recording, processing, playing

  // Multi-session state
  let sessions = {}; // { sessionId: { title, messages, lastUpdated } }
  let currentSessionId = null;
  let userProfile = null;

  // Async job polling state
  let activeJobPollTimer = null;
  let activeJobId = null;

  // Media upload state
  let selectedMedia = null; // { file, type, previewUrl }
  let mediaUploadRecorder = null;
  let mediaAudioChunks = [];
  let mediaRecordingTimer = null;
  let mediaRecordingSeconds = 0;
  const MAX_MEDIA_RECORDING_SEC = 120; // 2 minutes

  // DOM Elements
  let messagesEl, textInput, sendBtn, pttBtn, logoutBtn;
  let sidebar, sidebarOverlay, menuBtn, newChatBtn, chatList;
  let userAvatar, userName;
  let textInputWrapper, expandBtn;
  let fullscreenInputOverlay, fullscreenInputText, fullscreenInputClose, fullscreenInputSend;
  let scrollToBottomBtn;
  let lightboxOverlay, lightboxImage, lightboxClose;
  let logPanel, logPanelContent, logLevelSelect, logRefreshBtn, logCopyBtn, logCloseBtn, logsBtn;

  // Pull-to-refresh state
  let pullStartY = 0;
  let isPulling = false;
  let pullRefreshIndicator = null;

  // Media elements
  let addMediaBtn, mediaModalOverlay, mediaModalClose;
  let mediaCameraBtn, mediaGalleryBtn, mediaAudioBtn, mediaFileBtn;
  let cameraInput, galleryInput, fileInput;
  let mediaPreview, mediaPreviewImage, mediaPreviewFile, mediaPreviewName, mediaPreviewRemove;
  let audioModalOverlay, audioTimer, audioStopBtn, audioCancelBtn;

  // Initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    // Get DOM elements
    messagesEl = document.getElementById('messages');
    textInput = document.getElementById('textInput');
    sendBtn = document.getElementById('sendBtn');
    pttBtn = document.getElementById('pttBtn');
    logoutBtn = document.getElementById('logoutBtn');

    // Sidebar elements
    sidebar = document.getElementById('sidebar');
    sidebarOverlay = document.getElementById('sidebarOverlay');
    menuBtn = document.getElementById('menuBtn');
    newChatBtn = document.getElementById('newChatBtn');
    chatList = document.getElementById('chatList');
    userAvatar = document.getElementById('userAvatar');
    userName = document.getElementById('userName');

    // Media elements
    addMediaBtn = document.getElementById('addMediaBtn');
    mediaModalOverlay = document.getElementById('mediaModalOverlay');
    mediaModalClose = document.getElementById('mediaModalClose');
    mediaCameraBtn = document.getElementById('mediaCameraBtn');
    mediaGalleryBtn = document.getElementById('mediaGalleryBtn');
    mediaAudioBtn = document.getElementById('mediaAudioBtn');
    mediaFileBtn = document.getElementById('mediaFileBtn');
    cameraInput = document.getElementById('cameraInput');
    galleryInput = document.getElementById('galleryInput');
    fileInput = document.getElementById('fileInput');
    mediaPreview = document.getElementById('mediaPreview');
    mediaPreviewImage = document.getElementById('mediaPreviewImage');
    mediaPreviewFile = document.getElementById('mediaPreviewFile');
    mediaPreviewName = document.getElementById('mediaPreviewName');
    mediaPreviewRemove = document.getElementById('mediaPreviewRemove');
    audioModalOverlay = document.getElementById('audioModalOverlay');
    audioTimer = document.getElementById('audioTimer');
    audioStopBtn = document.getElementById('audioStopBtn');
    audioCancelBtn = document.getElementById('audioCancelBtn');

    // Text input expansion elements
    textInputWrapper = textInput.parentElement;
    expandBtn = document.getElementById('expandBtn');
    fullscreenInputOverlay = document.getElementById('fullscreenInputOverlay');
    fullscreenInputText = document.getElementById('fullscreenInputText');
    fullscreenInputClose = document.getElementById('fullscreenInputClose');
    fullscreenInputSend = document.getElementById('fullscreenInputSend');

    // Event listeners - chat input
    sendBtn.addEventListener('click', sendTextMessage);
    textInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendTextMessage();
      }
    });

    // Textarea auto-expand
    textInput.addEventListener('input', handleTextInputChange);
    textInput.addEventListener('focus', function() {
      updateExpandButtonVisibility();
    });
    textInput.addEventListener('blur', function() {
      // Delay to allow click on expand button
      setTimeout(updateExpandButtonVisibility, 100);
    });

    // Expand button
    expandBtn.addEventListener('click', openFullscreenInput);

    // Fullscreen input modal
    fullscreenInputClose.addEventListener('click', closeFullscreenInput);
    fullscreenInputSend.addEventListener('click', sendFromFullscreen);

    pttBtn.addEventListener('click', handlePTTClick);

    // Header buttons
    document.getElementById('newChatHeaderBtn').addEventListener('click', createNewSession);
    document.getElementById('schoolBtn').addEventListener('click', function() {
      window.location.href = '/school';
    });
    document.getElementById('filesBtn').addEventListener('click', function() {
      window.location.href = '/files';
    });
    logoutBtn.addEventListener('click', function() {
      window.location.href = '/auth/logout';
    });

    // Sidebar event listeners
    menuBtn.addEventListener('click', toggleSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);
    newChatBtn.addEventListener('click', createNewSession);

    // Media event listeners
    addMediaBtn.addEventListener('click', openMediaModal);
    mediaModalOverlay.addEventListener('click', function(e) {
      if (e.target === mediaModalOverlay) closeMediaModal();
    });
    mediaModalClose.addEventListener('click', closeMediaModal);
    mediaCameraBtn.addEventListener('click', function() { triggerFileInput(cameraInput); });
    mediaGalleryBtn.addEventListener('click', function() { triggerFileInput(galleryInput); });
    mediaAudioBtn.addEventListener('click', startMediaAudioRecording);
    mediaFileBtn.addEventListener('click', function() { triggerFileInput(fileInput); });
    cameraInput.addEventListener('change', handleImageSelect);
    galleryInput.addEventListener('change', handleImageSelect);
    fileInput.addEventListener('change', handleFileSelect);
    mediaPreviewRemove.addEventListener('click', clearSelectedMedia);
    audioStopBtn.addEventListener('click', stopMediaAudioRecording);
    audioCancelBtn.addEventListener('click', cancelMediaAudioRecording);

    // Check microphone support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      pttBtn.disabled = true;
      pttBtn.title = 'Microphone not supported';
    }

    // Flush pending saves when leaving the page or switching tabs
    // Note: We intentionally do NOT clear PENDING_JOB_KEY — it must survive page reloads
    window.addEventListener('beforeunload', function() {
      if (saveTimeout) {
        clearTimeout(saveTimeout);
        saveSessionsSync();
      }
    });
    document.addEventListener('visibilitychange', function() {
      if (document.visibilityState === 'hidden' && saveTimeout) {
        clearTimeout(saveTimeout);
        saveTimeout = null;
        saveSessionsSync();
      }
    });

    // Load user profile
    fetchUserProfile();

    // Load sessions and current session (async)
    initSessions();

    // Check for prepopulated query from ?q= parameter
    var urlParams = new URLSearchParams(window.location.search);
    var queryParam = urlParams.get('q');
    if (queryParam) {
      textInput.value = queryParam;
      textInput.focus();
      // Clean up URL without reloading
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Setup scroll-to-bottom button
    setupScrollToBottom();

    // Setup pull-to-refresh for mobile
    setupPullToRefresh();

    // Setup lightbox for images
    setupLightbox();

    // Setup log panel
    setupLogPanel();
  }

  // ============================================
  // User Profile
  // ============================================

  function fetchUserProfile() {
    fetch(API_BASE + '/api/user/profile')
      .then(function(response) {
        if (!response.ok) throw new Error('Failed to fetch profile');
        return response.json();
      })
      .then(function(data) {
        userProfile = data;
        if (data.picture) {
          userAvatar.src = data.picture;
        }
        if (data.name) {
          userName.textContent = data.name;
        } else if (data.email) {
          userName.textContent = data.email.split('@')[0];
        }
      })
      .catch(function(err) {
        console.error('Failed to load user profile:', err);
      });
  }

  // ============================================
  // Sidebar Management
  // ============================================

  function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('active');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
  }

  // ============================================
  // Multi-Session Management
  // ============================================

  function generateSessionId() {
    return 'thread_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  async function initSessions() {
    await loadSessions();

    // If no sessions exist, create one
    if (Object.keys(sessions).length === 0) {
      await createNewSession();
    } else if (!currentSessionId || !sessions[currentSessionId]) {
      // Select the most recent session
      const sortedIds = Object.keys(sessions).sort(function(a, b) {
        return (sessions[b].lastUpdated || 0) - (sessions[a].lastUpdated || 0);
      });
      await switchSession(sortedIds[0]);
    } else {
      // Reload current session
      await switchSession(currentSessionId);
    }

    // Render sidebar chat list
    renderChatList();
  }

  async function createNewSession() {
    const sessionId = generateSessionId();

    try {
      // Create on server
      const response = await fetch('/api/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: sessionId,
          title: 'New Chat',
          messages: '[]'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create thread');
      }
    } catch (err) {
      console.error('Failed to create session:', err);
      // Continue anyway - will work offline
    }

    sessions[sessionId] = {
      title: 'New Chat',
      messages: [],
      lastUpdated: Date.now()
    };
    currentSessionId = sessionId;
    localStorage.setItem(CURRENT_SESSION_KEY, sessionId);
    renderChatList();
    await switchSession(sessionId);
    closeSidebar();

    // Add welcome message and persist it immediately
    addMessage('assistant', 'Hello! I\'m ATHENA, your AI assistant. Tap the microphone to speak, or type a message below.');
    saveSessions();
  }

  async function switchSession(sessionId) {
    if (!sessions[sessionId]) return;

    // Stop polling for previous thread's job
    if (activeJobPollTimer) {
      clearTimeout(activeJobPollTimer);
      activeJobPollTimer = null;
    }

    currentSessionId = sessionId;
    localStorage.setItem(CURRENT_SESSION_KEY, sessionId);

    // Clear messages and thinking bubble
    messagesEl.textContent = '';
    const session = sessions[sessionId];

    // Load messages from server if not already loaded
    if (!session.messages || session.messages.length === 0) {
      try {
        const response = await fetch('/api/threads/' + sessionId);
        if (response.ok) {
          const data = await response.json();
          session.messages = data.messages || [];
        }
      } catch (err) {
        console.error('Failed to load thread messages:', err);
      }
    }

    // Render messages
    (session.messages || []).forEach(function(msg) {
      renderMessage(msg);
    });

    // Update active state in chat list
    document.querySelectorAll('.chat-list-item').forEach(function(item) {
      item.classList.toggle('active', item.dataset.sessionId === sessionId);
    });

    // Scroll to bottom
    messagesEl.scrollTop = messagesEl.scrollHeight;

    // Check for pending/completed async jobs on this thread
    checkPendingJob(sessionId);
  }

  function deleteSession(sessionId) {
    showConfirm(
      'Delete chat?',
      'This conversation will be permanently deleted.',
      async function() {
        try {
          await fetch('/api/threads/' + sessionId, { method: 'DELETE' });
        } catch (err) {
          console.error('Failed to delete from server:', err);
        }

        delete sessions[sessionId];
        renderChatList();

        // If deleted current session, switch to another or create new
        if (sessionId === currentSessionId) {
          const remainingIds = Object.keys(sessions);
          if (remainingIds.length > 0) {
            switchSession(remainingIds[0]);
          } else {
            createNewSession();
          }
        }
      },
      'Delete'
    );
  }

  function renderChatList() {
    chatList.textContent = '';

    // Sort sessions by lastUpdated (newest first)
    const sortedIds = Object.keys(sessions).sort(function(a, b) {
      return (sessions[b].lastUpdated || 0) - (sessions[a].lastUpdated || 0);
    });

    sortedIds.forEach(function(sessionId) {
      const session = sessions[sessionId];
      const item = document.createElement('div');
      item.className = 'chat-list-item' + (sessionId === currentSessionId ? ' active' : '');
      item.dataset.sessionId = sessionId;

      const icon = document.createElement('span');
      icon.className = 'material-icons';
      icon.textContent = 'chat_bubble_outline';

      const title = document.createElement('span');
      title.className = 'chat-item-title';
      title.textContent = session.title || 'New Chat';

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'chat-item-delete';
      const deleteIcon = document.createElement('span');
      deleteIcon.className = 'material-icons';
      deleteIcon.textContent = 'close';
      deleteBtn.appendChild(deleteIcon);
      deleteBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        deleteSession(sessionId);
      });

      item.appendChild(icon);
      item.appendChild(title);
      item.appendChild(deleteBtn);

      item.addEventListener('click', function() {
        switchSession(sessionId);
        closeSidebar();
      });

      chatList.appendChild(item);
    });
  }

  async function loadSessions() {
    try {
      // Fetch threads from server
      const response = await fetch('/api/threads');
      if (!response.ok) {
        throw new Error('Failed to load threads');
      }
      const data = await response.json();

      sessions = {};
      (data.threads || []).forEach(function(t) {
        sessions[t.id] = {
          title: t.title,
          messages: [], // Messages loaded when switching
          lastUpdated: new Date(t.updated_at).getTime(),
          messageCount: t.message_count
        };
      });

      // Get last session from localStorage (just for current session preference)
      currentSessionId = localStorage.getItem(CURRENT_SESSION_KEY);
    } catch (err) {
      console.error('Failed to load sessions:', err);
      sessions = {};
    }
  }

  // Debounced save to avoid too many API calls
  let saveTimeout = null;
  function saveSessions() {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveSessionsNow, 1000);
  }

  function buildSavePayload() {
    if (!currentSessionId || !sessions[currentSessionId]) return null;
    var session = sessions[currentSessionId];
    var messagesJson = JSON.stringify(
      (session.messages || []).slice(-100).map(function(m) {
        return {
          id: m.id,
          role: m.role,
          text: m.text,
          audioUrl: m.audioUrl,
          timestamp: m.timestamp
        };
      })
    );
    return {
      url: '/api/threads/' + currentSessionId,
      body: JSON.stringify({ title: session.title, messages: messagesJson })
    };
  }

  async function saveSessionsNow() {
    var payload = buildSavePayload();
    if (!payload) return;

    try {
      var resp = await fetch(payload.url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: payload.body
      });

      if (resp.status === 401) {
        console.warn('Session expired during save — messages preserved in memory');
      }

      // Also keep localStorage for current session preference
      localStorage.setItem(CURRENT_SESSION_KEY, currentSessionId);
    } catch (err) {
      console.error('Failed to save session:', err);
    }
  }

  // Synchronous save for beforeunload/visibilitychange — uses sendBeacon for reliability
  function saveSessionsSync() {
    var payload = buildSavePayload();
    if (!payload) return;
    navigator.sendBeacon(payload.url, new Blob([payload.body], { type: 'application/json' }));
    localStorage.setItem(CURRENT_SESSION_KEY, currentSessionId);
  }

  function updateSessionTitle(text) {
    if (!currentSessionId || !sessions[currentSessionId]) return;
    const session = sessions[currentSessionId];

    // Only update if still "New Chat"
    if (session.title === 'New Chat') {
      // First user message becomes the title (truncated)
      session.title = text.length > 30 ? text.substring(0, 30) + '...' : text;
      saveSessions();
      renderChatList();
    }
  }

  // ============================================
  // PTT State
  // ============================================

  function setPTTState(state) {
    pttState = state;
    pttBtn.className = 'icon-btn mic ' + state;

    // Update icon
    const iconEl = pttBtn.querySelector('.material-icons');
    const icons = { idle: 'mic', recording: 'stop', processing: 'hourglass_empty', playing: 'volume_up' };
    iconEl.textContent = icons[state] || 'mic';

    // Remove existing timer if any
    const existingTimer = pttBtn.querySelector('.ptt-timer');
    if (existingTimer) {
      existingTimer.remove();
    }

    // Add timer for recording state
    if (state === 'recording') {
      const timerEl = document.createElement('div');
      timerEl.className = 'ptt-timer';
      timerEl.id = 'pttTimer';
      timerEl.textContent = MAX_RECORDING_SEC + 's';
      pttBtn.appendChild(timerEl);
    }
  }

  // ============================================
  // Thinking Bubble
  // ============================================

  function showThinkingBubble(status) {
    // Create thinking bubble as a message
    const msgEl = document.createElement('div');
    msgEl.className = 'message assistant thinking';
    msgEl.id = 'thinking-bubble';

    const avatarEl = document.createElement('img');
    avatarEl.className = 'message-avatar';
    avatarEl.alt = 'ATHENA';
    avatarEl.src = '/static/img/avatar.png';

    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';

    const indicator = document.createElement('div');
    indicator.className = 'thinking-indicator';

    const dots = document.createElement('div');
    dots.className = 'thinking-dots';
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'thinking-dot';
      dots.appendChild(dot);
    }

    const statusText = document.createElement('span');
    statusText.className = 'thinking-status';
    statusText.id = 'thinking-status';
    statusText.textContent = status || 'Thinking...';

    indicator.appendChild(dots);
    indicator.appendChild(statusText);
    contentEl.appendChild(indicator);
    msgEl.appendChild(avatarEl);
    msgEl.appendChild(contentEl);

    messagesEl.appendChild(msgEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function updateThinkingStatus(status) {
    const statusEl = document.getElementById('thinking-status');
    if (statusEl) {
      statusEl.textContent = status;
    }
  }

  function removeThinkingBubble() {
    const bubble = document.getElementById('thinking-bubble');
    if (bubble) {
      bubble.remove();
    }
  }

  // ============================================
  // Transcribing Message (User Side)
  // ============================================

  function addTranscribingMessage() {
    const msgId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

    const msgEl = document.createElement('div');
    msgEl.className = 'message user transcribing';
    msgEl.id = msgId;

    // Avatar
    const avatarEl = document.createElement('img');
    avatarEl.className = 'message-avatar';
    avatarEl.alt = 'user';
    avatarEl.src = (userProfile && userProfile.picture)
      ? userProfile.picture
      : 'https://www.gravatar.com/avatar/?d=mp';

    // Content container
    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';

    // Transcribing indicator (same style as thinking)
    const indicator = document.createElement('div');
    indicator.className = 'thinking-indicator';

    const dots = document.createElement('div');
    dots.className = 'thinking-dots';
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('div');
      dot.className = 'thinking-dot';
      dots.appendChild(dot);
    }

    const statusText = document.createElement('span');
    statusText.className = 'thinking-status';
    statusText.textContent = 'Transcribing...';

    indicator.appendChild(dots);
    indicator.appendChild(statusText);
    contentEl.appendChild(indicator);
    msgEl.appendChild(avatarEl);
    msgEl.appendChild(contentEl);

    messagesEl.appendChild(msgEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    return msgId;
  }

  function convertTranscribingToText(msgId, text) {
    const msgEl = document.getElementById(msgId);
    if (!msgEl) return;

    // Remove transcribing class
    msgEl.classList.remove('transcribing');

    // Replace content with text
    const contentEl = msgEl.querySelector('.message-content');
    if (contentEl) {
      contentEl.textContent = '';
      const textEl = document.createElement('div');
      textEl.className = 'message-text';
      textEl.textContent = text;
      contentEl.appendChild(textEl);
    }

    // Store in session
    if (currentSessionId && sessions[currentSessionId]) {
      const msgData = {
        id: msgId,
        role: 'user',
        text: text,
        audioUrl: '',
        audioBase64: '',
        timestamp: Date.now()
      };
      sessions[currentSessionId].messages.push(msgData);
      sessions[currentSessionId].lastUpdated = Date.now();
    }
  }

  // ============================================
  // Recording and Voice
  // ============================================

  async function handlePTTClick() {
    if (pttState === 'idle') {
      await startRecording();
    } else if (pttState === 'recording') {
      stopRecording();
    } else if (pttState === 'playing') {
      stopPlayback();
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Determine supported MIME type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';

      mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = function(e) {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = function() {
        stream.getTracks().forEach(function(track) {
          track.stop();
        });
        processRecording();
      };

      mediaRecorder.start();
      recordingStartTime = Date.now();
      setPTTState('recording');

      // Start countdown timer
      let remaining = MAX_RECORDING_SEC;
      recordingTimer = setInterval(function() {
        remaining--;
        const timerEl = document.getElementById('pttTimer');
        if (timerEl) {
          timerEl.textContent = remaining + 's';
        }

        if (remaining <= 0) {
          stopRecording();
        }
      }, 1000);

    } catch (err) {
      console.error('Failed to start recording:', err);
    }
  }

  function stopRecording() {
    if (recordingTimer) {
      clearInterval(recordingTimer);
      recordingTimer = null;
    }

    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
    }
  }

  // Track whether the current job originated from voice (for TTS after completion)
  var pendingVoiceJobId = null;

  async function processRecording() {
    setPTTState('processing');

    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });

    // Add user message with transcribing indicator
    const userMsgId = addTranscribingMessage();

    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('session_id', currentSessionId);

      // SSE endpoint: does STT then creates an async job (same as text chat)
      const response = await fetch(API_BASE + '/api/voice/stream', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Voice API error: ' + response.status);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEventType = line.slice(6).trim();
            continue;
          }
          if (!line.startsWith('data:')) continue;

          try {
            const data = JSON.parse(line.slice(5).trim());

            if (currentEventType === 'transcript') {
              // Update user message with transcript
              convertTranscribingToText(userMsgId, data.transcript);
              updateSessionTitle(data.transcript);
            } else if (currentEventType === 'job') {
              // Job created — switch to same polling as text chat
              showThinkingBubble('Thinking...');
              pendingVoiceJobId = data.job_id;
              startJobPolling(data.job_id, currentSessionId);
              // PTT stays in processing state until job completes + TTS plays
            } else if (currentEventType === 'error') {
              throw new Error(data.error);
            }
            currentEventType = '';
          } catch (parseErr) {
            if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr;
          }
        }
      }

      saveSessions();

    } catch (err) {
      console.error('Voice processing error:', err);
      setPTTState('idle');
      removeThinkingBubble();
      convertTranscribingToText(userMsgId, '[Voice failed: ' + err.message + ']');
    }
  }

  // Fetch TTS for voice-originated responses
  async function fetchTTS(responseText) {
    try {
      showThinkingBubble('Generating audio...');
      const response = await fetch(API_BASE + '/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: responseText })
      });
      removeThinkingBubble();

      if (!response.ok) {
        console.error('TTS failed:', response.status);
        setPTTState('idle');
        return;
      }

      const data = await response.json();
      if (data.audio_base64 || data.audio_url) {
        playAudioResponse(data.audio_url, data.audio_base64);
      } else {
        setPTTState('idle');
      }
    } catch (err) {
      console.error('TTS error:', err);
      removeThinkingBubble();
      setPTTState('idle');
    }
  }

  function playAudioResponse(url, base64) {
    setPTTState('playing');

    let audioSrc = url;
    if (!audioSrc && base64) {
      audioSrc = 'data:audio/mp3;base64,' + base64;
    }

    if (!audioSrc) {
      setPTTState('idle');
      return;
    }

    currentAudio = new Audio(audioSrc);
    currentAudio.onended = function() {
      setPTTState('idle');
      currentAudio = null;
    };
    currentAudio.onerror = function() {
      console.error('Audio playback error');
      setPTTState('idle');
      currentAudio = null;
    };
    currentAudio.play().catch(function(err) {
      console.error('Audio play error:', err);
      setPTTState('idle');
    });
  }

  function stopPlayback() {
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    setPTTState('idle');
  }

  // ============================================
  // Text Chat
  // ============================================

  async function sendTextMessage() {
    const text = textInput.value.trim();

    // If media is selected, upload it
    if (selectedMedia) {
      textInput.value = '';
      await uploadMedia(text);
      return;
    }

    if (!text) return;

    textInput.value = '';
    sendBtn.disabled = true;

    addMessage('user', text);
    updateSessionTitle(text);
    showThinkingBubble('Thinking...');

    try {
      const response = await fetch(API_BASE + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: currentSessionId
        })
      });

      if (!response.ok) {
        if (response.status === 401) {
          window.location.href = '/login';
          return;
        }
        const errorData = await response.json().catch(function() { return {}; });
        throw new Error(errorData.error || 'Chat API error: ' + response.status);
      }

      // Detect auth redirect (fetch follows 307 → gets HTML login page)
      var contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        window.location.href = '/login';
        return;
      }

      const data = await response.json();

      if (data.job_id) {
        // Async mode — start polling for result
        startJobPolling(data.job_id, currentSessionId);
      } else if (data.response) {
        // Legacy sync response (fallback)
        removeThinkingBubble();
        addMessage('assistant', data.response, {
          audioUrl: data.audio_url,
          audioBase64: data.audio_base64
        });
        saveSessions();
      }

    } catch (err) {
      console.error('Chat error:', err);
      removeThinkingBubble();
      addMessage('assistant', 'Sorry, something went wrong: ' + err.message);
    }

    sendBtn.disabled = false;
  }

  // ============================================
  // Async Job Polling
  // ============================================

  function startJobPolling(jobId, threadId) {
    activeJobId = jobId;

    // Persist to localStorage so we can resume after page reload or device switch
    localStorage.setItem(PENDING_JOB_KEY, JSON.stringify({
      jobId: jobId,
      threadId: threadId,
      startedAt: Date.now()
    }));

    updateThinkingStatus('Processing... (you can close this page)');

    // Start polling
    pollJob(jobId, threadId);
  }

  function pollJob(jobId, threadId) {
    // Clear any existing timer
    if (activeJobPollTimer) {
      clearTimeout(activeJobPollTimer);
      activeJobPollTimer = null;
    }

    fetch(API_BASE + '/api/jobs/' + jobId)
      .then(function(response) {
        if (!response.ok) {
          if (response.status === 401) {
            window.location.href = '/login';
            return null;
          }
          throw new Error('Job poll failed: ' + response.status);
        }
        return response.json();
      })
      .then(function(job) {
        if (!job) return;

        if (job.status === 'done') {
          // Job completed — show result
          var wasVoice = (pendingVoiceJobId === jobId);
          activeJobId = null;
          localStorage.removeItem(PENDING_JOB_KEY);
          if (wasVoice) pendingVoiceJobId = null;

          // Only update UI if we're viewing the right thread
          if (currentSessionId === threadId) {
            removeThinkingBubble();
            addMessage('assistant', job.response);
            saveSessions();

            // If this was a voice request, generate TTS audio
            if (wasVoice) {
              fetchTTS(job.response);
            }
          } else {
            // Result arrived for a different thread — store it for when user switches
            storePendingResult(threadId, job);
            if (wasVoice) setPTTState('idle');
          }
        } else if (job.status === 'error') {
          // Job failed
          var wasVoiceErr = (pendingVoiceJobId === jobId);
          activeJobId = null;
          localStorage.removeItem(PENDING_JOB_KEY);
          if (wasVoiceErr) { pendingVoiceJobId = null; setPTTState('idle'); }

          if (currentSessionId === threadId) {
            removeThinkingBubble();
            addMessage('assistant', 'Sorry, something went wrong: ' + (job.error || 'Unknown error'));
            saveSessions();
          }
        } else {
          // Still running — update timer display and poll again
          var elapsed = Math.round((Date.now() - job.created_at) / 1000);
          var mins = Math.floor(elapsed / 60);
          var secs = elapsed % 60;
          var timeStr = mins > 0 ? mins + 'm ' + secs + 's' : secs + 's';
          if (currentSessionId === threadId) {
            updateThinkingStatus('Processing (' + timeStr + ')... you can close this page');
          }
          activeJobPollTimer = setTimeout(function() {
            pollJob(jobId, threadId);
          }, JOB_POLL_INTERVAL);
        }
      })
      .catch(function(err) {
        console.error('Job poll error:', err);
        // Retry on network errors
        activeJobPollTimer = setTimeout(function() {
          pollJob(jobId, threadId);
        }, JOB_POLL_INTERVAL * 2);
      });
  }

  function storePendingResult(threadId, job) {
    // Store the result so it can be displayed when user switches to that thread
    var key = 'alfred_job_result_' + threadId;
    localStorage.setItem(key, JSON.stringify({
      response: job.response,
      completedAt: job.completed_at
    }));
  }

  // Check for pending jobs on page load or thread switch
  async function checkPendingJob(threadId) {
    // First check localStorage for a pending job
    var pending = localStorage.getItem(PENDING_JOB_KEY);
    if (pending) {
      try {
        var data = JSON.parse(pending);
        if (data.threadId === threadId && data.jobId) {
          // Resume polling for this job
          showThinkingBubble('Reconnecting...');
          startJobPolling(data.jobId, data.threadId);
          return;
        }
      } catch (e) {
        localStorage.removeItem(PENDING_JOB_KEY);
      }
    }

    // Check for stored results from jobs that completed while viewing another thread
    var resultKey = 'alfred_job_result_' + threadId;
    var storedResult = localStorage.getItem(resultKey);
    if (storedResult) {
      try {
        var result = JSON.parse(storedResult);
        localStorage.removeItem(resultKey);
        addMessage('assistant', result.response);
        saveSessions();
        return;
      } catch (e) {
        localStorage.removeItem(resultKey);
      }
    }

    // Check server for any running jobs on this thread
    try {
      var response = await fetch(API_BASE + '/api/jobs?thread_id=' + threadId);
      if (response.ok) {
        var data = await response.json();
        if (data.job && data.job.status === 'running') {
          // There's an active job from another device — resume polling
          showThinkingBubble('Reconnecting to active request...');
          startJobPolling(data.job.id, threadId);
        } else if (data.job && data.job.status === 'done') {
          // Check if this result is newer than the last message in the thread
          var session = sessions[threadId];
          if (session && session.messages) {
            var lastMsg = session.messages[session.messages.length - 1];
            if (!lastMsg || lastMsg.role === 'user' || (data.job.completed_at > (lastMsg.timestamp || 0))) {
              addMessage('assistant', data.job.response);
              saveSessions();
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to check pending jobs:', err);
    }
  }

  // ============================================
  // Message Management
  // ============================================

  function addMessage(role, text, options) {
    options = options || {};
    const msgId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

    // Store message data in current session
    const msgData = {
      id: msgId,
      role: role,
      text: text,
      audioUrl: options.audioUrl || '',
      audioBase64: options.audioBase64 || '',
      timestamp: Date.now()
    };

    if (currentSessionId && sessions[currentSessionId]) {
      sessions[currentSessionId].messages.push(msgData);
      sessions[currentSessionId].lastUpdated = Date.now();
    }

    // Render the message
    renderMessage(msgData);

    return msgId;
  }

  function renderMessage(msgData) {
    const msgEl = document.createElement('div');
    msgEl.className = 'message ' + msgData.role;
    msgEl.id = msgData.id;
    msgEl.dataset.audioUrl = msgData.audioUrl || '';
    msgEl.dataset.audioBase64 = msgData.audioBase64 || '';

    // Avatar
    const avatarEl = document.createElement('img');
    avatarEl.className = 'message-avatar';
    avatarEl.alt = msgData.role;
    if (msgData.role === 'assistant') {
      avatarEl.src = '/static/img/avatar.png';
    } else {
      avatarEl.src = (userProfile && userProfile.picture)
        ? userProfile.picture
        : 'https://www.gravatar.com/avatar/?d=mp';
    }

    // Content container
    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';

    // Text content
    // Note: Assistant messages use innerHTML because HTML is generated server-side
    // by goldmark markdown library. User input always uses textContent for safety.
    const textEl = document.createElement('div');
    textEl.className = 'message-text';
    if (msgData.role === 'assistant') {
      // Server-rendered HTML from markdown conversion (safe - generated by goldmark)
      textEl.innerHTML = msgData.text;
      // Enhance vault media links to show inline previews
      enhanceVaultMedia(textEl);
      // Enhance code blocks with syntax highlighting and copy buttons
      enhanceCodeBlocks(textEl);
      // Wrap tables for mobile scroll
      wrapTables(textEl);
      // Add click-to-expand for images
      enhanceImages(textEl);
    } else {
      // User input - always escape for XSS prevention
      textEl.textContent = msgData.text;
    }
    contentEl.appendChild(textEl);

    // Add replay button if audio available
    if (msgData.audioUrl || msgData.audioBase64) {
      const actionsEl = document.createElement('div');
      actionsEl.className = 'message-actions';

      const replayBtn = document.createElement('button');
      replayBtn.className = 'replay-btn';
      replayBtn.textContent = '\u25B6 Replay';
      replayBtn.addEventListener('click', function() {
        replayAudio(msgData.id);
      });

      actionsEl.appendChild(replayBtn);
      contentEl.appendChild(actionsEl);
    }

    // Assemble message
    msgEl.appendChild(avatarEl);
    msgEl.appendChild(contentEl);

    messagesEl.appendChild(msgEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function updateMessage(msgId, newText, isHtml) {
    const msgEl = document.getElementById(msgId);
    if (msgEl) {
      const textEl = msgEl.querySelector('.message-text');
      if (textEl) {
        if (isHtml) {
          // Server-rendered HTML (safe)
          textEl.innerHTML = newText;
        } else {
          textEl.textContent = newText;
        }
      }
    }

    // Update stored message in current session
    if (currentSessionId && sessions[currentSessionId]) {
      const msg = sessions[currentSessionId].messages.find(function(m) {
        return m.id === msgId;
      });
      if (msg) {
        msg.text = newText;
      }
    }
  }

  function replayAudio(msgId) {
    const msgEl = document.getElementById(msgId);
    if (msgEl) {
      stopPlayback();
      playAudioResponse(msgEl.dataset.audioUrl, msgEl.dataset.audioBase64);
    }
  }

  // ============================================
  // Confirm Dialog
  // ============================================

  function showConfirm(title, message, onConfirm, confirmText) {
    var overlay = document.getElementById('confirmOverlay');
    var titleEl = document.getElementById('confirmTitle');
    var messageEl = document.getElementById('confirmMessage');
    var okBtn = document.getElementById('confirmOk');
    var cancelBtn = document.getElementById('confirmCancel');

    titleEl.textContent = title;
    messageEl.textContent = message;
    okBtn.textContent = confirmText || 'Confirm';

    function cleanup() {
      okBtn.removeEventListener('click', handleOk);
      cancelBtn.removeEventListener('click', handleCancel);
      overlay.removeEventListener('click', handleOverlay);
      overlay.style.display = 'none';
    }

    function handleOk() {
      cleanup();
      onConfirm();
    }

    function handleCancel() {
      cleanup();
    }

    function handleOverlay(e) {
      if (e.target === overlay) {
        cleanup();
      }
    }

    okBtn.addEventListener('click', handleOk);
    cancelBtn.addEventListener('click', handleCancel);
    overlay.addEventListener('click', handleOverlay);

    overlay.style.display = 'flex';
  }

  // ============================================
  // Toast Notifications
  // ============================================

  function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || (type === 'error' ? 5000 : 3000);

    var container = document.getElementById('toastContainer');
    if (!container) return;

    var icons = {
      success: 'check_circle',
      error: 'error',
      warning: 'warning',
      info: 'info'
    };

    var toast = document.createElement('div');
    toast.className = 'toast ' + type;

    var icon = document.createElement('span');
    icon.className = 'material-icons';
    icon.textContent = icons[type] || 'info';
    toast.appendChild(icon);

    var msg = document.createElement('span');
    msg.textContent = message;
    toast.appendChild(msg);

    container.appendChild(toast);

    setTimeout(function() {
      toast.classList.add('toast-out');
      setTimeout(function() {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 200);
    }, duration);
  }

  function clearChat() {
    showConfirm(
      'Clear chat?',
      'This will clear all messages in this conversation.',
      function() {
        if (currentSessionId && sessions[currentSessionId]) {
          sessions[currentSessionId].messages = [];
          sessions[currentSessionId].title = 'New Chat';
          sessions[currentSessionId].lastUpdated = Date.now();
          saveSessions();
          renderChatList();
        }

        messagesEl.textContent = '';
        addMessage('assistant', 'Chat cleared. How can I help you?');
      },
      'Clear'
    );
  }

  // ============================================
  // Media Upload Functions
  // ============================================

  function openMediaModal() {
    mediaModalOverlay.style.display = 'flex';
  }

  function closeMediaModal() {
    mediaModalOverlay.style.display = 'none';
  }

  function triggerFileInput(input) {
    closeMediaModal();
    input.click();
  }

  function handleImageSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    selectedMedia = {
      file: file,
      type: 'image',
      previewUrl: URL.createObjectURL(file)
    };

    showMediaPreview();
    e.target.value = ''; // Reset input
  }

  function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    selectedMedia = {
      file: file,
      type: 'document',
      previewUrl: null
    };

    showMediaPreview();
    e.target.value = '';
  }

  function showMediaPreview() {
    if (!selectedMedia) return;

    if (selectedMedia.type === 'image' && selectedMedia.previewUrl) {
      mediaPreviewImage.src = selectedMedia.previewUrl;
      mediaPreviewImage.style.display = 'block';
      mediaPreviewFile.style.display = 'none';
    } else {
      mediaPreviewImage.style.display = 'none';
      mediaPreviewFile.style.display = 'flex';
      mediaPreviewName.textContent = selectedMedia.file.name;
    }

    mediaPreview.style.display = 'flex';
  }

  function clearSelectedMedia() {
    if (selectedMedia && selectedMedia.previewUrl) {
      URL.revokeObjectURL(selectedMedia.previewUrl);
    }
    selectedMedia = null;
    mediaPreview.style.display = 'none';
    mediaPreviewImage.style.display = 'none';
    mediaPreviewFile.style.display = 'none';
  }

  // Audio recording for media upload (separate from PTT)
  async function startMediaAudioRecording() {
    closeMediaModal();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';

      mediaUploadRecorder = new MediaRecorder(stream, { mimeType: mimeType });
      mediaAudioChunks = [];
      mediaRecordingSeconds = 0;

      mediaUploadRecorder.ondataavailable = function(e) {
        if (e.data.size > 0) {
          mediaAudioChunks.push(e.data);
        }
      };

      mediaUploadRecorder.onstop = function() {
        stream.getTracks().forEach(function(track) { track.stop(); });

        if (mediaAudioChunks.length > 0) {
          const audioBlob = new Blob(mediaAudioChunks, { type: mimeType });
          selectedMedia = {
            file: new File([audioBlob], 'voice_memo.webm', { type: mimeType }),
            type: 'audio',
            previewUrl: null
          };
          showMediaPreview();
          mediaPreviewFile.style.display = 'flex';
          mediaPreviewName.textContent = 'Voice memo (' + formatTime(mediaRecordingSeconds) + ')';
        }
      };

      mediaUploadRecorder.start();
      audioModalOverlay.style.display = 'flex';
      updateAudioTimer();

      mediaRecordingTimer = setInterval(function() {
        mediaRecordingSeconds++;
        updateAudioTimer();

        if (mediaRecordingSeconds >= MAX_MEDIA_RECORDING_SEC) {
          stopMediaAudioRecording();
        }
      }, 1000);

    } catch (err) {
      console.error('Failed to start audio recording:', err);
      showToast('Could not access microphone', 'error');
    }
  }

  function updateAudioTimer() {
    const elapsed = formatTime(mediaRecordingSeconds);
    const max = formatTime(MAX_MEDIA_RECORDING_SEC);
    audioTimer.textContent = elapsed + ' / ' + max;
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins + ':' + (secs < 10 ? '0' : '') + secs;
  }

  function stopMediaAudioRecording() {
    if (mediaRecordingTimer) {
      clearInterval(mediaRecordingTimer);
      mediaRecordingTimer = null;
    }
    if (mediaUploadRecorder && mediaUploadRecorder.state === 'recording') {
      mediaUploadRecorder.stop();
    }
    audioModalOverlay.style.display = 'none';
  }

  function cancelMediaAudioRecording() {
    mediaAudioChunks = [];
    stopMediaAudioRecording();
  }

  // Upload media with optional message
  async function uploadMedia(message) {
    if (!selectedMedia) return;

    const file = selectedMedia.file;
    const type = selectedMedia.type;

    // Add user message with media indicator
    const userMsgId = addMessageWithMedia('user', message || '[' + type + ' uploaded]', selectedMedia);
    updateSessionTitle(message || 'Shared ' + type);

    clearSelectedMedia();
    showThinkingBubble('Uploading...');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', type);
      formData.append('session_id', currentSessionId);
      if (message) {
        formData.append('message', message);
      }

      const response = await fetch(API_BASE + '/api/media/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(function() { return {}; });
        throw new Error(errorData.error || 'Upload failed: ' + response.status);
      }

      updateThinkingStatus('Analyzing...');

      const data = await response.json();

      removeThinkingBubble();

      if (data.success) {
        addMessage('assistant', data.response.html);
      } else {
        addMessage('assistant', 'Failed to process media: ' + (data.error || 'Unknown error'));
      }

      saveSessions();

    } catch (err) {
      console.error('Media upload error:', err);
      removeThinkingBubble();
      addMessage('assistant', 'Upload failed: ' + err.message);
    }
  }

  function addMessageWithMedia(role, text, media) {
    const msgId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

    const msgData = {
      id: msgId,
      role: role,
      text: text,
      mediaType: media.type,
      mediaPreview: media.previewUrl,
      timestamp: Date.now()
    };

    if (currentSessionId && sessions[currentSessionId]) {
      sessions[currentSessionId].messages.push(msgData);
      sessions[currentSessionId].lastUpdated = Date.now();
    }

    renderMessageWithMedia(msgData);
    return msgId;
  }

  function renderMessageWithMedia(msgData) {
    const msgEl = document.createElement('div');
    msgEl.className = 'message ' + msgData.role;
    msgEl.id = msgData.id;

    const avatarEl = document.createElement('img');
    avatarEl.className = 'message-avatar';
    avatarEl.alt = msgData.role;
    avatarEl.src = msgData.role === 'assistant'
      ? '/static/img/avatar.png'
      : (userProfile && userProfile.picture) || 'https://www.gravatar.com/avatar/?d=mp';

    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';

    // Add media preview if available
    if (msgData.mediaPreview || msgData.mediaType) {
      const mediaEl = document.createElement('div');
      mediaEl.className = 'message-media';

      if (msgData.mediaPreview && msgData.mediaType === 'image') {
        const img = document.createElement('img');
        img.src = msgData.mediaPreview;
        img.alt = 'Uploaded image';
        mediaEl.appendChild(img);
      } else {
        const fileEl = document.createElement('div');
        fileEl.className = 'message-media-file';
        const icon = document.createElement('span');
        icon.className = 'material-icons';
        icon.textContent = msgData.mediaType === 'audio' ? 'mic' : 'description';
        const label = document.createElement('span');
        label.textContent = msgData.mediaType === 'audio' ? 'Voice memo' : 'Document';
        fileEl.appendChild(icon);
        fileEl.appendChild(label);
        mediaEl.appendChild(fileEl);
      }

      contentEl.appendChild(mediaEl);
    }

    const textEl = document.createElement('div');
    textEl.className = 'message-text';
    textEl.textContent = msgData.text;
    contentEl.appendChild(textEl);

    msgEl.appendChild(avatarEl);
    msgEl.appendChild(contentEl);
    messagesEl.appendChild(msgEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ============================================
  // Vault Media Enhancement
  // ============================================

  // Enhance vault links in messages to show inline media
  function enhanceVaultMedia(container) {
    // Find all links to vault files
    const links = container.querySelectorAll('a[href*="/api/vault/file/"]');

    links.forEach(function(link) {
      const url = link.getAttribute('href');
      const id = url.split('/api/vault/file/')[1];
      if (!id) return;

      // Fetch metadata to determine type
      fetchVaultItemInfo(id, function(item) {
        if (!item) return;

        const mediaContainer = document.createElement('div');
        mediaContainer.className = 'vault-media-container';

        if (item.type === 'image') {
          // Create image preview
          const img = document.createElement('img');
          img.src = url;
          img.alt = item.description || 'Image';
          img.className = 'vault-image-preview';
          img.addEventListener('click', function() {
            window.open(url, '_blank');
          });
          mediaContainer.appendChild(img);

          // Add caption
          if (item.description) {
            const caption = document.createElement('div');
            caption.className = 'vault-media-caption';
            caption.textContent = item.description;
            mediaContainer.appendChild(caption);
          }
        } else if (item.type === 'audio') {
          // Create audio player
          const audio = document.createElement('audio');
          audio.src = url;
          audio.controls = true;
          audio.className = 'vault-audio-player';
          mediaContainer.appendChild(audio);

          // Add transcript if available
          if (item.content_text) {
            const transcript = document.createElement('div');
            transcript.className = 'vault-audio-transcript';
            transcript.textContent = item.content_text;
            mediaContainer.appendChild(transcript);
          }
        } else {
          // Document - create download button (safe: no innerHTML with user data)
          const downloadBtn = document.createElement('a');
          downloadBtn.href = url;
          downloadBtn.download = item.original_filename;
          downloadBtn.className = 'vault-download-btn';
          var downloadIcon = document.createElement('span');
          downloadIcon.className = 'material-icons';
          downloadIcon.textContent = 'download';
          downloadBtn.appendChild(downloadIcon);
          downloadBtn.appendChild(document.createTextNode(' ' + item.original_filename));
          mediaContainer.appendChild(downloadBtn);
        }

        // Replace or append to link
        link.parentNode.insertBefore(mediaContainer, link.nextSibling);
      });
    });
  }

  // Cache for vault item info
  var vaultItemCache = {};

  function fetchVaultItemInfo(id, callback) {
    if (vaultItemCache[id]) {
      callback(vaultItemCache[id]);
      return;
    }

    fetch('/api/vault/list?q=' + id)
      .then(function(response) {
        if (!response.ok) throw new Error('Failed to fetch');
        return response.json();
      })
      .then(function(items) {
        var item = items.find(function(i) { return i.id === id; });
        if (item) {
          vaultItemCache[id] = item;
        }
        callback(item);
      })
      .catch(function(err) {
        console.error('Vault fetch error:', err);
        callback(null);
      });
  }

  // ============================================
  // Textarea Auto-Expand and Fullscreen Input
  // ============================================

  function handleTextInputChange() {
    // Auto-expand textarea
    autoExpandTextarea(textInput);
    // Update expand button visibility
    updateExpandButtonVisibility();
  }

  function autoExpandTextarea(textarea) {
    // Reset height to get accurate scrollHeight
    textarea.style.height = 'auto';
    // Set height based on content, with max limit
    var newHeight = Math.min(textarea.scrollHeight, 120);
    textarea.style.height = newHeight + 'px';
  }

  function updateExpandButtonVisibility() {
    if (!textInputWrapper || !textInput) return;

    var hasContent = textInput.value.trim().length > 0;
    var hasMultipleLines = textInput.scrollHeight > 50;
    var isFocused = document.activeElement === textInput;

    // Show expand button if: has content, or has multiple lines, or is focused on mobile
    var showExpand = hasContent || hasMultipleLines || (isFocused && window.innerWidth <= 768);

    if (showExpand) {
      textInputWrapper.classList.add('has-content');
    } else {
      textInputWrapper.classList.remove('has-content');
    }
  }

  function openFullscreenInput() {
    if (!fullscreenInputOverlay || !fullscreenInputText) return;

    // Copy content from main input
    fullscreenInputText.value = textInput.value;

    // Show overlay
    fullscreenInputOverlay.style.display = 'flex';

    // Focus textarea
    setTimeout(function() {
      fullscreenInputText.focus();
      // Move cursor to end
      fullscreenInputText.selectionStart = fullscreenInputText.selectionEnd = fullscreenInputText.value.length;
    }, 100);
  }

  function closeFullscreenInput() {
    if (!fullscreenInputOverlay) return;

    // Copy content back to main input
    textInput.value = fullscreenInputText.value;

    // Hide overlay
    fullscreenInputOverlay.style.display = 'none';

    // Update main textarea
    handleTextInputChange();
  }

  function sendFromFullscreen() {
    // Copy content to main input and close
    textInput.value = fullscreenInputText.value;
    fullscreenInputOverlay.style.display = 'none';

    // Send the message
    sendTextMessage();
  }

  // ============================================
  // Scroll to Bottom Button
  // ============================================

  function setupScrollToBottom() {
    // Create scroll-to-bottom button
    scrollToBottomBtn = document.createElement('button');
    scrollToBottomBtn.className = 'scroll-to-bottom-btn';
    var icon = document.createElement('span');
    icon.className = 'material-icons';
    icon.textContent = 'keyboard_arrow_down';
    scrollToBottomBtn.appendChild(icon);
    scrollToBottomBtn.title = 'Scroll to bottom';
    scrollToBottomBtn.style.display = 'none';
    scrollToBottomBtn.addEventListener('click', scrollToBottom);

    // Insert after messages container
    messagesEl.parentNode.insertBefore(scrollToBottomBtn, messagesEl.nextSibling);

    // Show/hide button based on scroll position
    messagesEl.addEventListener('scroll', updateScrollButtonVisibility);
  }

  function updateScrollButtonVisibility() {
    if (!scrollToBottomBtn || !messagesEl) return;

    var scrollTop = messagesEl.scrollTop;
    var scrollHeight = messagesEl.scrollHeight;
    var clientHeight = messagesEl.clientHeight;

    // Show button if not near bottom (more than 200px from bottom)
    var distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    if (distanceFromBottom > 200) {
      scrollToBottomBtn.style.display = 'flex';
    } else {
      scrollToBottomBtn.style.display = 'none';
    }
  }

  function scrollToBottom() {
    if (!messagesEl) return;
    messagesEl.scrollTo({
      top: messagesEl.scrollHeight,
      behavior: 'smooth'
    });
  }

  // ============================================
  // Pull to Refresh
  // ============================================

  function setupPullToRefresh() {
    // Only on mobile
    if (window.innerWidth > 768) return;

    // Create refresh indicator
    pullRefreshIndicator = document.createElement('div');
    pullRefreshIndicator.className = 'pull-refresh-indicator';
    var refreshIcon = document.createElement('span');
    refreshIcon.className = 'material-icons';
    refreshIcon.textContent = 'refresh';
    var refreshText = document.createElement('span');
    refreshText.className = 'pull-refresh-text';
    refreshText.textContent = 'Pull to refresh';
    pullRefreshIndicator.appendChild(refreshIcon);
    pullRefreshIndicator.appendChild(refreshText);
    pullRefreshIndicator.style.display = 'none';

    // Insert before messages
    messagesEl.parentNode.insertBefore(pullRefreshIndicator, messagesEl);

    // Touch events
    messagesEl.addEventListener('touchstart', handlePullStart, { passive: true });
    messagesEl.addEventListener('touchmove', handlePullMove, { passive: false });
    messagesEl.addEventListener('touchend', handlePullEnd, { passive: true });
  }

  function handlePullStart(e) {
    // Only trigger if at top of scroll
    if (messagesEl.scrollTop <= 0) {
      pullStartY = e.touches[0].clientY;
      isPulling = true;
    }
  }

  function handlePullMove(e) {
    if (!isPulling || !pullRefreshIndicator) return;

    var currentY = e.touches[0].clientY;
    var pullDistance = currentY - pullStartY;

    // Only activate on downward pull when at top
    if (pullDistance > 0 && messagesEl.scrollTop <= 0) {
      e.preventDefault();

      // Limit pull distance
      var clampedDistance = Math.min(pullDistance, 150);

      // Show indicator with progress
      pullRefreshIndicator.style.display = 'flex';
      pullRefreshIndicator.style.transform = 'translateY(' + (clampedDistance - 50) + 'px)';

      // Update text based on pull distance
      var textEl = pullRefreshIndicator.querySelector('.pull-refresh-text');
      var iconEl = pullRefreshIndicator.querySelector('.material-icons');

      if (clampedDistance > 80) {
        textEl.textContent = 'Release to refresh';
        iconEl.style.transform = 'rotate(180deg)';
        pullRefreshIndicator.classList.add('ready');
      } else {
        textEl.textContent = 'Pull to refresh';
        iconEl.style.transform = 'rotate(0deg)';
        pullRefreshIndicator.classList.remove('ready');
      }
    }
  }

  function handlePullEnd(e) {
    if (!isPulling || !pullRefreshIndicator) return;

    isPulling = false;

    // Check if pulled far enough to trigger refresh
    if (pullRefreshIndicator.classList.contains('ready')) {
      // Show refreshing state
      var textEl = pullRefreshIndicator.querySelector('.pull-refresh-text');
      textEl.textContent = 'Refreshing...';
      pullRefreshIndicator.classList.add('refreshing');

      // Perform refresh - reload current session messages
      setTimeout(function() {
        if (currentSessionId && sessions[currentSessionId]) {
          switchSession(currentSessionId);
        }

        // Hide indicator
        pullRefreshIndicator.style.display = 'none';
        pullRefreshIndicator.style.transform = '';
        pullRefreshIndicator.classList.remove('ready', 'refreshing');
      }, 500);
    } else {
      // Cancel pull - hide indicator
      pullRefreshIndicator.style.display = 'none';
      pullRefreshIndicator.style.transform = '';
      pullRefreshIndicator.classList.remove('ready');
    }
  }

  // ============================================
  // Code Block Enhancement
  // ============================================

  function enhanceCodeBlocks(container) {
    // Find all code blocks
    var codeBlocks = container.querySelectorAll('pre code');

    codeBlocks.forEach(function(codeEl) {
      // Apply syntax highlighting if highlight.js is available
      if (typeof hljs !== 'undefined') {
        hljs.highlightElement(codeEl);
      }

      // Add copy button to parent pre element
      var preEl = codeEl.parentElement;
      if (preEl && preEl.tagName === 'PRE' && !preEl.querySelector('.code-copy-btn')) {
        var copyBtn = document.createElement('button');
        copyBtn.className = 'code-copy-btn';
        copyBtn.title = 'Copy code';

        var icon = document.createElement('span');
        icon.className = 'material-icons';
        icon.textContent = 'content_copy';
        copyBtn.appendChild(icon);

        copyBtn.addEventListener('click', function() {
          var code = codeEl.textContent;
          navigator.clipboard.writeText(code).then(function() {
            icon.textContent = 'check';
            setTimeout(function() {
              icon.textContent = 'content_copy';
            }, 2000);
          }).catch(function(err) {
            console.error('Copy failed:', err);
          });
        });

        // Wrap pre in a container for positioning
        var wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';
        preEl.parentNode.insertBefore(wrapper, preEl);
        wrapper.appendChild(preEl);
        wrapper.appendChild(copyBtn);
      }
    });
  }

  // ============================================
  // Table Wrapper for Mobile Scroll
  // ============================================

  function wrapTables(container) {
    var tables = container.querySelectorAll('table');

    tables.forEach(function(table) {
      // Skip if already wrapped
      if (table.parentElement.classList.contains('table-wrapper')) return;

      var wrapper = document.createElement('div');
      wrapper.className = 'table-wrapper';
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  }

  // ============================================
  // Image Enhancement (Lightbox)
  // ============================================

  function setupLightbox() {
    lightboxOverlay = document.getElementById('lightboxOverlay');
    lightboxImage = document.getElementById('lightboxImage');
    lightboxClose = document.getElementById('lightboxClose');

    if (lightboxOverlay && lightboxClose) {
      lightboxClose.addEventListener('click', closeLightbox);
      lightboxOverlay.addEventListener('click', function(e) {
        if (e.target === lightboxOverlay) {
          closeLightbox();
        }
      });
    }
  }

  function enhanceImages(container) {
    // Find images in message content (not avatars)
    var images = container.querySelectorAll('img:not(.message-avatar)');

    images.forEach(function(img) {
      // Add lazy loading
      img.loading = 'lazy';

      // Add click handler for lightbox
      img.style.cursor = 'pointer';
      img.addEventListener('click', function() {
        openLightbox(img.src, img.alt);
      });
    });

    // Also enhance vault image previews
    var vaultImages = container.querySelectorAll('.vault-image-preview');
    vaultImages.forEach(function(img) {
      img.style.cursor = 'pointer';
      img.addEventListener('click', function(e) {
        e.stopPropagation();
        openLightbox(img.src, img.alt);
      });
    });
  }

  function openLightbox(src, alt) {
    if (!lightboxOverlay || !lightboxImage) return;

    lightboxImage.src = src;
    lightboxImage.alt = alt || 'Image';
    lightboxOverlay.style.display = 'flex';

    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    if (!lightboxOverlay) return;

    lightboxOverlay.style.display = 'none';
    lightboxImage.src = '';

    // Restore body scroll
    document.body.style.overflow = '';
  }

  // ============================================
  // Log Panel
  // ============================================

  function setupLogPanel() {
    logPanel = document.getElementById('logPanel');
    logPanelContent = document.getElementById('logPanelContent');
    logLevelSelect = document.getElementById('logLevelSelect');
    logRefreshBtn = document.getElementById('logRefreshBtn');
    logCopyBtn = document.getElementById('logCopyBtn');
    logCloseBtn = document.getElementById('logCloseBtn');
    logsBtn = document.getElementById('logsBtn');

    if (logsBtn) {
      logsBtn.addEventListener('click', toggleLogPanel);
    }

    if (logCloseBtn) {
      logCloseBtn.addEventListener('click', closeLogPanel);
    }

    if (logRefreshBtn) {
      logRefreshBtn.addEventListener('click', refreshLogs);
    }

    if (logCopyBtn) {
      logCopyBtn.addEventListener('click', copyAllLogs);
    }

    if (logLevelSelect) {
      logLevelSelect.addEventListener('change', refreshLogs);
    }
  }

  function toggleLogPanel() {
    if (!logPanel) return;

    if (logPanel.style.display === 'none') {
      openLogPanel();
    } else {
      closeLogPanel();
    }
  }

  function openLogPanel() {
    if (!logPanel) return;

    logPanel.style.display = 'flex';
    refreshLogs();
  }

  function closeLogPanel() {
    if (!logPanel) return;
    logPanel.style.display = 'none';
  }

  function refreshLogs() {
    if (!logPanelContent || !logLevelSelect) return;

    var level = logLevelSelect.value;

    fetch('/api/logs?level=' + level + '&limit=100')
      .then(function(response) {
        if (!response.ok) throw new Error('Failed to fetch logs');
        return response.json();
      })
      .then(function(data) {
        renderLogs(data.logs || []);
      })
      .catch(function(err) {
        console.error('Failed to load logs:', err);
        logPanelContent.textContent = 'Failed to load logs: ' + err.message;
      });
  }

  function renderLogs(logs) {
    if (!logPanelContent) return;

    // Clear existing content
    logPanelContent.textContent = '';

    if (logs.length === 0) {
      var emptyEl = document.createElement('div');
      emptyEl.className = 'log-empty';
      emptyEl.textContent = 'No logs found';
      logPanelContent.appendChild(emptyEl);
      return;
    }

    logs.forEach(function(log) {
      var entryEl = document.createElement('div');
      entryEl.className = 'log-entry log-' + log.level;

      var timestampEl = document.createElement('span');
      timestampEl.className = 'log-timestamp';
      var date = new Date(log.timestamp);
      timestampEl.textContent = date.toLocaleTimeString();

      var levelEl = document.createElement('span');
      levelEl.className = 'log-level';
      levelEl.textContent = log.level.toUpperCase();

      var messageEl = document.createElement('span');
      messageEl.className = 'log-message';
      messageEl.textContent = log.message;

      entryEl.appendChild(timestampEl);
      entryEl.appendChild(levelEl);
      entryEl.appendChild(messageEl);

      if (log.source) {
        var sourceEl = document.createElement('span');
        sourceEl.className = 'log-source';
        sourceEl.textContent = '[' + log.source + ']';
        entryEl.appendChild(sourceEl);
      }

      logPanelContent.appendChild(entryEl);
    });

    // Scroll to bottom
    logPanelContent.scrollTop = logPanelContent.scrollHeight;
  }

  function copyAllLogs() {
    if (!logPanelContent) return;

    var logEntries = logPanelContent.querySelectorAll('.log-entry');
    var text = [];

    logEntries.forEach(function(entry) {
      var timestamp = entry.querySelector('.log-timestamp');
      var level = entry.querySelector('.log-level');
      var message = entry.querySelector('.log-message');

      if (timestamp && level && message) {
        text.push(timestamp.textContent + ' ' + level.textContent + ' ' + message.textContent);
      }
    });

    var logText = text.join('\n');

    navigator.clipboard.writeText(logText).then(function() {
      // Show feedback
      var icon = logCopyBtn.querySelector('.material-icons');
      if (icon) {
        icon.textContent = 'check';
        setTimeout(function() {
          icon.textContent = 'content_copy';
        }, 2000);
      }
    }).catch(function(err) {
      console.error('Copy failed:', err);
    });
  }

})();
