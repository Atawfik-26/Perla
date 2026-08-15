/* PERLA FRONTEND */

let currentChatId = null;
let isStreaming = false;
let mediaRecorder = null;
let recordedChunks = [];
let recordingInterval = null;
let recordingSeconds = 0;
let attachedFile = null;
let planMode = false;
let isDarkMode = false;
let currentAudio = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    chat: $('#chat'),
    welcome: $('#welcome'),
    messageInput: $('#messageInput'),
    sendButton: $('#sendButton'),
    voiceButton: $('#voiceButton'),
    attachButton: $('#attachButton'),
    fileInput: $('#fileInput'),
    filePreview: $('#filePreview'),
    audioPreview: $('#audioPreview'),
    previewImage: $('#previewImage'),
    previewVideo: $('#previewVideo'),
    previewLabel: $('#previewLabel'),
    removeFile: $('#removeFile'),
    removeAudio: $('#removeAudio'),
    audioPlayer: $('#audioPlayer'),
    recordingBar: $('#recordingBar'),
    recordingTimer: $('#recordingTimer'),
    stopRecording: $('#stopRecording'),
    planButton: $('#planButton'),
    planModeBar: $('#planModeBar'),
    cancelPlanMode: $('#cancelPlanMode'),
    history: $('#history'),
    newChat: $('#newChat'),
    status: $('#status'),
    darkModeToggle: $('#darkModeToggle'),
    remindersButton: $('#remindersButton'),
    remindersPanel: $('#remindersPanel'),
    remindersList: $('#remindersList'),
    reminderDot: $('#reminderDot'),
    exportButton: $('#exportButton'),
    settingsButton: $('#settingsButton'),
    mobileMenu: $('#mobileMenu'),
    sidebar: $('#sidebar'),
    sidebarOverlay: $('#sidebarOverlay'),
};

async function init() {
    setupEventListeners();
    setupTextarea();
    await loadCurrentChat();
    await loadChats();
    await checkReminders();
    setupDarkMode();
}

document.addEventListener('DOMContentLoaded', init);

function setupEventListeners() {
    els.sendButton.addEventListener('click', handleSend);
    els.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    });
    els.voiceButton.addEventListener('click', toggleRecording);
    els.stopRecording.addEventListener('click', stopRecording);
    els.removeAudio.addEventListener('click', clearAudio);
    els.attachButton.addEventListener('click', () => els.fileInput.click());
    els.fileInput.addEventListener('change', handleFileSelect);
    els.removeFile.addEventListener('click', clearFile);
    els.planButton.addEventListener('click', () => setPlanMode(true));
    els.cancelPlanMode.addEventListener('click', () => setPlanMode(false));
    els.newChat.addEventListener('click', createNewChat);
    els.mobileMenu.addEventListener('click', toggleSidebar);
    els.sidebarOverlay.addEventListener('click', closeSidebar);
    els.remindersButton.addEventListener('click', toggleReminders);
    els.darkModeToggle.addEventListener('click', toggleDarkMode);
    els.exportButton.addEventListener('click', exportCurrentChat);
    els.settingsButton.addEventListener('click', openSettings);
    $$('.quick-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const msg = btn.dataset.message;
            if (msg) { els.messageInput.value = msg; handleSend(); }
        });
    });
    document.addEventListener('click', (e) => {
        if (!els.remindersButton.contains(e.target) && !els.remindersPanel.contains(e.target)) {
            els.remindersPanel.hidden = true;
        }
    });
}

function setupTextarea() {
    const ta = els.messageInput;
    ta.addEventListener('input', () => {
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
    });
}

async function loadCurrentChat() {
    try {
        const res = await fetch('/current-chat');
        const data = await res.json();
        currentChatId = data.chat?.id;
        renderChat(data.chat);
    } catch (e) { console.error('Failed to load chat:', e); }
}

async function loadChats() {
    try {
        const res = await fetch('/chats');
        const data = await res.json();
        renderHistory(data.chats);
    } catch (e) { console.error('Failed to load chats:', e); }
}

function renderChat(chat) {
    if (!chat || !chat.messages || chat.messages.length === 0) {
        els.welcome.hidden = false;
        els.chat.innerHTML = '';
        els.chat.appendChild(els.welcome);
        return;
    }
    els.welcome.hidden = true;
    els.chat.innerHTML = '';
    chat.messages.forEach(msg => appendMessage(msg.role, msg.content, msg.image, msg.video, false));
    scrollToBottom();
}

function renderHistory(chats) {
    els.history.innerHTML = '';
    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = 'history-item' + (chat.id === currentChatId ? ' active' : '');
        item.innerHTML = `<span class="history-item-title">${escapeHtml(chat.title || 'محادثة جديدة')}</span><span class="history-item-delete" title="مسح">🗑️</span>`;
        item.querySelector('.history-item-title').addEventListener('click', () => switchChat(chat.id));
        item.querySelector('.history-item-delete').addEventListener('click', (e) => { e.stopPropagation(); deleteChat(chat.id); });
        els.history.appendChild(item);
    });
}

async function handleSend() {
    const text = els.messageInput.value.trim();
    if (!text && !attachedFile) return;
    if (isStreaming) return;
    els.welcome.hidden = true;
    let userContent = text;
    if (attachedFile) {
        const label = attachedFile.type.startsWith('video/') ? '[فيديو مرفق]' : '[صورة مرفقة]';
        userContent = text ? text + '\n\n' + label : label;
    }
    appendMessage('user', userContent, null, null, true);
    els.messageInput.value = '';
    els.messageInput.style.height = 'auto';
    const fileToSend = attachedFile;
    clearFile();
    setStatus('thinking');
    if (fileToSend) await sendMultimodal(text, fileToSend);
    else if (planMode) await sendPlan(text);
    else await sendStream(text);
}

async function sendStream(message) {
    isStreaming = true;
    els.sendButton.disabled = true;
    const bubble = appendMessage('assistant', '', null, null, true);
    bubble.classList.add('streaming-text');
    let fullText = '';
    try {
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6).trim();
                if (!data) continue;
                try {
                    const parsed = JSON.parse(data);
                    if (parsed.type === 'chunk') {
                        fullText += parsed.content;
                        bubble.innerHTML = formatMessage(fullText);
                        scrollToBottom();
                    } else if (parsed.type === 'done') {
                        bubble.classList.remove('streaming-text');
                        bubble.innerHTML = formatMessage(fullText);
                        addCopyButtons(bubble);
                        currentChatId = parsed.chat_id;
                    } else if (parsed.type === 'planned') {
                        bubble.classList.remove('streaming-text');
                        bubble.innerHTML = formatPlan(parsed.content);
                        currentChatId = parsed.chat_id;
                    } else if (parsed.type === 'error') {
                        bubble.classList.remove('streaming-text');
                        bubble.textContent = parsed.content;
                    }
                } catch (e) {}
            }
        }
    } catch (e) {
        bubble.classList.remove('streaming-text');
        bubble.textContent = 'حصل خطأ في الاتصال 😕';
    } finally {
        isStreaming = false;
        els.sendButton.disabled = false;
        setStatus('ready');
        await loadChats();
    }
}

async function sendMultimodal(message, file) {
    isStreaming = true;
    els.sendButton.disabled = true;
    setStatus('thinking');
    const formData = new FormData();
    formData.append('message', message || '');
    formData.append('file', file);
    const endpoint = file.type.startsWith('video/') ? '/chat/video' : '/chat/multimodal';
    try {
        const res = await fetch(endpoint, { method: 'POST', body: formData });
        const data = await res.json();
        appendMessage('assistant', data.response, null, null, true);
        currentChatId = data.chat_id;
    } catch (e) {
        appendMessage('assistant', 'حصل خطأ في رفع الملف 😕', null, null, true);
    } finally {
        isStreaming = false;
        els.sendButton.disabled = false;
        setStatus('ready');
        await loadChats();
    }
}

function setPlanMode(active) {
    planMode = active;
    els.planModeBar.hidden = !active;
    els.planButton.classList.toggle('active', active);
}

async function sendPlan(message) {
    isStreaming = true;
    els.sendButton.disabled = true;
    setStatus('thinking');
    const bubble = appendMessage('assistant', '', null, null, true);
    bubble.classList.add('streaming-text');
    try {
        const res = await fetch('/chat/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();
        bubble.classList.remove('streaming-text');
        bubble.innerHTML = formatPlan(data.response);
        currentChatId = data.chat_id;
    } catch (e) {
        bubble.classList.remove('streaming-text');
        bubble.textContent = 'حصل خطأ 😕';
    } finally {
        isStreaming = false;
        els.sendButton.disabled = false;
        setPlanMode(false);
        setStatus('ready');
        await loadChats();
    }
}

// ====== VOICE RECORDING ======

async function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') { stopRecording(); return; }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
        mediaRecorder = new MediaRecorder(stream, { mimeType });
        recordedChunks = [];
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: mimeType });
            handleVoiceUpload(blob, mimeType);
            stream.getTracks().forEach(t => t.stop());
        };
        mediaRecorder.start();
        startRecordingTimer();
        els.voiceButton.classList.add('active');
        els.recordingBar.hidden = false;
        els.messageInput.placeholder = 'بيرلا بتسمعك...';
    } catch (e) {
        alert('مش قادر أستخدم المايك. اتأكد إنك سامح للموقع يستخدم المايك.');
        console.error(e);
    }
}

function startRecordingTimer() {
    recordingSeconds = 0;
    els.recordingTimer.textContent = '00:00';
    recordingInterval = setInterval(() => {
        recordingSeconds++;
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
        const secs = String(recordingSeconds % 60).padStart(2, '0');
        els.recordingTimer.textContent = `${mins}:${secs}`;
    }, 1000);
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
    clearInterval(recordingInterval);
    els.recordingBar.hidden = true;
    els.voiceButton.classList.remove('active');
    els.messageInput.placeholder = 'اكتب رسالتك لبيرلا...';
}

function clearAudio() {
    els.audioPreview.hidden = true;
    els.audioPlayer.src = '';
    recordedChunks = [];
}

// ====== VOICE CHAT PIPELINE ======

async function handleVoiceUpload(blob, mimeType) {
    isStreaming = true;
    els.sendButton.disabled = true;
    setStatus('thinking');
    els.welcome.hidden = true;
    const audioUrl = URL.createObjectURL(blob);
    appendMessage('user', '🎤 تسجيل صوتي', null, null, true);
    const lastUserMsg = els.chat.lastElementChild;
    if (lastUserMsg) {
        const audioEl = document.createElement('audio');
        audioEl.src = audioUrl; audioEl.controls = true;
        audioEl.style.marginTop = '8px'; audioEl.style.maxWidth = '260px';
        lastUserMsg.querySelector('.message-bubble').appendChild(audioEl);
    }
    const bubble = appendMessage('assistant', '', null, null, true);
    bubble.classList.add('streaming-text');
    bubble.textContent = 'بيرلا بتسمع وبتفكر...';
    const formData = new FormData();
    formData.append('audio', blob, `recording.${mimeType.split('/')[1] || 'webm'}`);
    formData.append('message', els.messageInput.value.trim());
    formData.append('voice', 'alloy');
    try {
        const response = await fetch('/chat/voice/stream', { method: 'POST', body: formData });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let audioUrl = null;
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6).trim();
                if (!data) continue;
                try {
                    const parsed = JSON.parse(data);
                    if (parsed.type === 'transcription') {
                        if (lastUserMsg) {
                            const bubbleEl = lastUserMsg.querySelector('.message-bubble');
                            const existingAudio = bubbleEl.querySelector('audio');
                            bubbleEl.innerHTML = `🎤 ${escapeHtml(parsed.content)}`;
                            if (existingAudio) bubbleEl.appendChild(existingAudio);
                        }
                        bubble.textContent = 'بيرلا بتفكر...';
                    } else if (parsed.type === 'chunk') {
                        fullText += parsed.content;
                        bubble.classList.remove('streaming-text');
                        bubble.innerHTML = formatMessage(fullText);
                        scrollToBottom();
                    } else if (parsed.type === 'audio') {
                        audioUrl = parsed.audio_url;
                        bubble.classList.remove('streaming-text');
                        bubble.innerHTML = formatMessage(fullText);
                        addVoicePlayback(bubble, audioUrl);
                        addCopyButtons(bubble);
                    } else if (parsed.type === 'done') {
                        currentChatId = parsed.chat_id;
                        if (!audioUrl) {
                            bubble.classList.remove('streaming-text');
                            bubble.innerHTML = formatMessage(fullText);
                            addCopyButtons(bubble);
                        }
                    } else if (parsed.type === 'error') {
                        bubble.classList.remove('streaming-text');
                        bubble.textContent = parsed.content;
                    }
                } catch (e) {}
            }
        }
    } catch (e) {
        bubble.classList.remove('streaming-text');
        bubble.textContent = 'حصل خطأ في الاتصال الصوتي 😕';
        console.error(e);
    } finally {
        isStreaming = false;
        els.sendButton.disabled = false;
        setStatus('ready');
        els.messageInput.value = '';
        await loadChats();
    }
}

function addVoicePlayback(bubble, audioUrl) {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'margin-top:12px;display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--paper-0);border-radius:var(--r-md);border:1px solid var(--border-subtle);';
    const playBtn = document.createElement('button');
    playBtn.textContent = '▶️'; playBtn.style.cssText = 'font-size:18px;background:none;border:none;cursor:pointer;';
    const label = document.createElement('span');
    label.textContent = 'سمع رد بيرلا'; label.style.cssText = 'font-size:12px;color:var(--text-secondary);';
    const audio = document.createElement('audio');
    audio.src = audioUrl; audio.preload = 'none';
    let isPlaying = false;
    playBtn.addEventListener('click', () => {
        if (isPlaying) { audio.pause(); playBtn.textContent = '▶️'; isPlaying = false; }
        else {
            if (currentAudio && currentAudio !== audio) { currentAudio.pause(); currentAudio.currentTime = 0; }
            audio.play(); playBtn.textContent = '⏸️'; isPlaying = true; currentAudio = audio;
        }
    });
    audio.addEventListener('ended', () => { playBtn.textContent = '▶️'; isPlaying = false; });
    wrap.appendChild(playBtn); wrap.appendChild(label); wrap.appendChild(audio);
    bubble.appendChild(wrap);
}

// ====== FILE ATTACH ======

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    attachedFile = file;
    els.filePreview.hidden = false;
    if (file.type.startsWith('image/')) {
        els.previewImage.hidden = false; els.previewVideo.hidden = true;
        els.previewImage.src = URL.createObjectURL(file);
        els.previewLabel.textContent = file.name;
    } else if (file.type.startsWith('video/')) {
        els.previewImage.hidden = true; els.previewVideo.hidden = false;
        els.previewVideo.src = URL.createObjectURL(file);
        els.previewLabel.textContent = file.name;
    }
}

function clearFile() {
    attachedFile = null;
    els.filePreview.hidden = true;
    els.previewImage.src = '';
    els.previewVideo.src = '';
    els.fileInput.value = '';
}

// ====== MESSAGES ======

function appendMessage(role, content, image, video, animate) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    if (animate) msgDiv.style.animationDelay = '0s';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = formatMessage(content);
    if (image) { const img = document.createElement('img'); img.src = image.url || image; img.alt = 'صورة مرفقة'; bubble.appendChild(img); }
    if (video) { const vid = document.createElement('video'); vid.src = video.url || video; vid.controls = true; bubble.appendChild(vid); }
    msgDiv.appendChild(bubble);
    els.chat.appendChild(msgDiv);
    scrollToBottom();
    return bubble;
}

function formatMessage(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    html = html.replace(/```([\w]*)([\s\S]*?)```/g, (match, lang, code) => `<pre><code class="language-${lang || 'text'}">${code.trim()}</code></pre>`);
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    html = html.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function formatPlan(text) {
    if (!text) return '';
    const lines = text.split('\n').filter(l => l.trim());
    let html = '<div class="plan-steps">';
    lines.forEach((line, i) => {
        html += `<div class="plan-step"><div class="plan-step-title">خطوة ${i + 1}</div><div class="plan-step-body">${formatMessage(line)}</div></div>`;
    });
    html += '</div>';
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addCopyButtons(bubble) {
    const pres = bubble.querySelectorAll('pre');
    pres.forEach(pre => {
        const btn = document.createElement('button');
        btn.className = 'copy-code-btn';
        btn.textContent = 'نسخ';
        btn.style.cssText = 'position:absolute;top:8px;left:8px;background:var(--paper-3);border:1px solid var(--border-subtle);border-radius:var(--r-sm);padding:4px 10px;font-size:11px;cursor:pointer;opacity:0;transition:opacity 0.2s;';
        pre.style.position = 'relative';
        pre.appendChild(btn);
        pre.addEventListener('mouseenter', () => btn.style.opacity = '1');
        pre.addEventListener('mouseleave', () => btn.style.opacity = '0');
        btn.addEventListener('click', () => {
            const code = pre.querySelector('code')?.textContent || pre.textContent;
            navigator.clipboard.writeText(code);
            btn.textContent = '✓ تم';
            setTimeout(() => btn.textContent = 'نسخ', 1500);
        });
    });
}

// ====== CHAT MANAGEMENT ======

async function createNewChat() {
    try {
        const res = await fetch('/chats', { method: 'POST' });
        const data = await res.json();
        currentChatId = data.chat.id;
        renderChat(data.chat);
        await loadChats();
        closeSidebar();
    } catch (e) { console.error(e); }
}

async function switchChat(chatId) {
    try {
        const res = await fetch(`/chats/${chatId}`);
        const data = await res.json();
        currentChatId = data.chat.id;
        renderChat(data.chat);
        await loadChats();
        closeSidebar();
    } catch (e) { console.error(e); }
}

async function deleteChat(chatId) {
    if (!confirm('متأكد إنك عايز تمسح المحادثة دي؟')) return;
    try {
        const res = await fetch(`/chats/${chatId}`, { method: 'DELETE' });
        const data = await res.json();
        currentChatId = data.active_chat.id;
        renderChat(data.active_chat);
        await loadChats();
    } catch (e) { console.error(e); }
}

function setStatus(state) {
    els.status.className = `status ${state}`;
    els.status.innerHTML = state === 'thinking' ? '<span class="status-dot"></span> بتفكر...' : '<span class="status-dot"></span> جاهزة';
}

function scrollToBottom() { els.chat.scrollTop = els.chat.scrollHeight; }

function toggleSidebar() { els.sidebar.classList.toggle('open'); els.sidebarOverlay.classList.toggle('show'); }
function closeSidebar() { els.sidebar.classList.remove('open'); els.sidebarOverlay.classList.remove('show'); }

async function checkReminders() {
    try {
        const res = await fetch('/reminders/due');
        const data = await res.json();
        if (data.reminders && data.reminders.length > 0) {
            els.reminderDot.hidden = false;
            renderReminders(data.reminders);
        }
    } catch (e) { console.error(e); }
}

function toggleReminders() { els.remindersPanel.hidden = !els.remindersPanel.hidden; }

function renderReminders(reminders) {
    if (!reminders || reminders.length === 0) {
        els.remindersList.innerHTML = '<div class="reminders-empty">مفيش تذكيرات دلوقتي</div>';
        return;
    }
    els.remindersList.innerHTML = reminders.map(r => `<div class="reminder-item">${escapeHtml(r)}</div>`).join('');
}

function setupDarkMode() {
    const saved = localStorage.getItem('perla-dark-mode');
    if (saved === 'true') { document.body.classList.add('dark-mode'); isDarkMode = true; }
}

function toggleDarkMode() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('dark-mode', isDarkMode);
    localStorage.setItem('perla-dark-mode', isDarkMode);
}

async function exportCurrentChat() {
    if (!currentChatId) return;
    try {
        const res = await fetch(`/chats/${currentChatId}/export?format=markdown`);
        const data = await res.json();
        const blob = new Blob([data.markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = data.filename;
        a.click(); URL.revokeObjectURL(url);
    } catch (e) { console.error(e); }
}

function openSettings() {
    alert('الإعدادات:\n\n• Dark Mode: ' + (isDarkMode ? 'مفعل' : 'مغلق') + '\n• اضغط على 🌙 عشان تبدل\n\n(المزيد قريباً!)');
}
