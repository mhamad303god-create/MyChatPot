/* ======================================================
   STATE
====================================================== */
let currentChatId = null;
const csrftoken = getCookie('csrftoken');
let editingMessageId = null;
let editingMessageEl = null;
let pendingUserMessageEl = null;

/* ======================================================
   HELPERS
====================================================== */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function scrollToBottom() {
    const container = document.getElementById("messagesContainer");
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function getMessageDirection(text) {
    const isArabic = /[\u0600-\u06FF]/.test(text || "");
    return {
        dir: isArabic ? "rtl" : "ltr",
        align: isArabic ? "right" : "left"
    };
}

function buildImageHtml(imageFile, imageUrl) {
    if (imageFile) {
        const url = URL.createObjectURL(imageFile);
        return `<div style="margin-bottom:0.5rem;"><img src="${url}" style="max-width:300px; border-radius:0.5rem; border:1px solid rgba(255,255,255,0.1);"></div>`;
    }
    if (imageUrl) {
        return `<div style="margin-bottom:0.5rem;"><img src="${imageUrl}" style="max-width:300px; border-radius:0.5rem; border:1px solid rgba(255,255,255,0.1);"></div>`;
    }
    return "";
}

function getExistingImageHtml(messageContentEl) {
    const img = messageContentEl.querySelector("img");
    if (!img) return "";
    const wrapper = img.closest("div");
    return wrapper ? wrapper.outerHTML : img.outerHTML;
}

function removeMessagesAfter(messageEl) {
    const box = document.getElementById("messages");
    let next = messageEl.nextElementSibling;
    while (next && next.parentElement === box) {
        const toRemove = next;
        next = next.nextElementSibling;
        toRemove.remove();
    }
}

/* ======================================================
   INPUT HANDLING
====================================================== */
function handleInput(textarea) {
    // Auto-resize
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';

    // Toggle Send Button
    const btn = document.getElementById("sendBtn");
    if (textarea.value.trim().length > 0) {
        btn.classList.add("active");
    } else {
        btn.classList.remove("active");
    }
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
    }
}

/* ======================================================
   SIDEBAR
====================================================== */
/* ======================================================
   SIDEBAR TOGGLE
====================================================== */
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");

    if (window.innerWidth <= 768) {
        // Mobile: Slide handling
        sidebar.classList.toggle("open");
        if (sidebar.classList.contains("open")) {
            overlay.style.display = "block";
        } else {
            overlay.style.display = "none";
        }
    } else {
        // Desktop: Collapse handling
        sidebar.classList.toggle("collapsed");
    }
}

/* ======================================================
   API CALLS
====================================================== */
async function fetchChats() {
    try {
        const res = await fetch('/api/chats/');
        const chats = await res.json();
        renderChats(chats);
    } catch (e) { console.error("Fetch chats failed", e); }
}

async function createNewChat() {
    try {
        const res = await fetch('/api/chats/new/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
        });
        const chat = await res.json();
        currentChatId = chat.id;
        // Reset UI
        document.getElementById("messages").innerHTML = "";
        document.getElementById("chatTitle").textContent = "New Conversation";
        document.getElementById("input").focus();
        clearEditingState();
        // Refresh list
        await fetchChats();
        // Hide sidebar on mobile if open
        document.getElementById("sidebar").classList.remove("open");
        document.getElementById("overlay").style.display = "none";
    } catch (e) { console.error("Create chat failed", e); }
}

async function loadChat(id) {
    try {
        currentChatId = id;
        const res = await fetch(`/api/chats/${id}/`);
        const data = await res.json();

        document.getElementById("chatTitle").textContent = data.title;
        renderMessages(data.messages);
        clearEditingState();

        // Highlight active
        document.querySelectorAll('.chat-item').forEach(el => el.classList.remove('active'));
        const activeItem = document.querySelector(`.chat-item[data-id="${id}"]`);
        if (activeItem) activeItem.classList.add("active");

        // Hide sidebar on mobile
        document.getElementById("sidebar").classList.remove("open");
        document.getElementById("overlay").style.display = "none";
    } catch (e) { console.error("Load chat failed", e); }
}

async function renameChatApi(id, newTitle) {
    await fetch(`/api/chats/${id}/rename/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
        body: JSON.stringify({ title: newTitle })
    });
    fetchChats();
    if (currentChatId === id) document.getElementById("chatTitle").textContent = newTitle;
}

async function deleteChatApi(id) {
    if (!confirm("Are you sure?")) return;
    await fetch(`/api/chats/${id}/delete/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrftoken }
    });
    if (currentChatId === id) {
        currentChatId = null;
        document.getElementById("messages").innerHTML = `<div class="message ai"><div class="avatar ai">AI</div><div class="message-content">Select a chat or start a new one.</div></div>`;
        document.getElementById("chatTitle").textContent = "AI Chat";
    }
    fetchChats();
}

/* ======================================================
   RENDERING
====================================================== */
function renderChats(chats) {
    const list = document.getElementById("chatList");
    list.innerHTML = "";
    chats.forEach(c => {
        const d = document.createElement("div");
        d.className = "chat-item";
        d.setAttribute("data-id", c.id);
        if (c.id === currentChatId) d.classList.add("active");

        d.innerHTML = `
            <span class="material-icons-round" style="font-size: 1.2rem;">chat_bubble_outline</span>
            <span style="flex:1; overflow:hidden; text-overflow:ellipsis;">${c.title}</span>
            <div class="chat-actions">
                <button class="action-btn" onclick="promptRename('${c.id}')"><span class="material-icons-round" style="font-size:1rem;">edit</span></button>
                <button class="action-btn" onclick="deleteChatApi(${c.id})"><span class="material-icons-round" style="font-size:1rem; color: #ef4444;">delete</span></button>
            </div>
        `;
        d.onclick = (e) => {
            if (e.target.closest('.action-btn')) return;
            loadChat(c.id);
        };
        list.appendChild(d);
    });
}

function renderMessages(messages) {
    const box = document.getElementById("messages");
    box.innerHTML = "";
    messages.forEach(m => appendMessage(m.role, m.text, null, m.image_url, m.id));
    scrollToBottom();
}

function showLoading() {
    const box = document.getElementById("messages");
    const d = document.createElement("div");
    d.id = "loading-indicator";
    d.className = "typing-indicator";
    d.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;
    box.appendChild(d);
    scrollToBottom();
}

function hideLoading() {
    const load = document.getElementById("loading-indicator");
    if (load) load.remove();
}

/* ======================================================
   FILE HANDLING
====================================================== */
let selectedFile = null;

function handleFileSelect(input) {
    if (input.files && input.files[0]) {
        selectedFile = input.files[0];
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('previewImg').src = e.target.result;
            document.getElementById('imagePreview').style.display = 'block';
            document.getElementById("sendBtn").classList.add("active");
        }
        reader.readAsDataURL(selectedFile);
    }
}

function clearImage() {
    selectedFile = null;
    document.getElementById('fileInput').value = "";
    document.getElementById('imagePreview').style.display = 'none';
    const textarea = document.getElementById("input");
    handleInput(textarea); // Re-check send button state
}

/* ======================================================
   SEND LOGIC
====================================================== */
async function send() {
    const textarea = document.getElementById("input");
    const text = textarea.value.trim();
    const isEditing = Boolean(editingMessageId && editingMessageEl);

    // Allow sending if image is present even if text is empty
    if (!text && !selectedFile) return;

    if (!currentChatId) {
        await createNewChat();
    }

    const fileToSend = selectedFile;
    const editId = isEditing ? editingMessageId : null;

    textarea.value = "";
    textarea.style.height = 'auto'; // Reset height

    // Clear preview UI after snapshotting file
    clearImage();
    handleInput(textarea);

    let userMessageEl = null;
    if (isEditing) {
        updateUserMessageContent(editingMessageEl, text, fileToSend);
        removeMessagesAfter(editingMessageEl);
        userMessageEl = editingMessageEl;
    } else {
        userMessageEl = appendMessage('user', text, fileToSend);
    }
    pendingUserMessageEl = userMessageEl;
    clearEditingState();

    // Add Placeholder AI Message
    const aiMessageDiv = appendMessage('ai', '');
    const messageContent = aiMessageDiv.querySelector('.message-content');

    // Loading Indicator (dots)
    const loadingDiv = document.createElement("div");
    loadingDiv.className = "typing-indicator";
    loadingDiv.innerHTML = `<div class="dot"></div><div class="dot"></div><div class="dot"></div>`;
    messageContent.appendChild(loadingDiv);

    scrollToBottom();

    try {
        let response;
        const formData = new FormData();
        if (text) formData.append('text', text);
        if (fileToSend) formData.append('image', fileToSend);
        if (editId) formData.append('edit_message_id', editId);

        // Always use FormData for consistency with view
        response = await fetch(`/api/chats/${currentChatId}/message/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            body: formData
        });

        if (!response.ok) throw new Error("Network error");

        // Remove loading indicator once stream starts
        if (loadingDiv) loadingDiv.remove();

        // Streaming Reader
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiTextAccumulated = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n\n');

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const jsonStr = line.substring(6);
                    if (!jsonStr) continue;

                    try {
                        const data = JSON.parse(jsonStr);

                        if (data.error) {
                            messageContent.innerHTML += `<br><span style="color:red">Error: ${data.error}</span>`;
                        } else if (data.chunk) {
                            aiTextAccumulated += data.chunk;
                            // Incremental Markdown Rendering with Cursor
                            messageContent.innerHTML = marked.parse(aiTextAccumulated) + '<span class="cursor"></span>';
                            // Highlight New Code
                            messageContent.querySelectorAll('pre code').forEach((el) => hljs.highlightElement(el));
                        } else if (data.done) {
                            // Remove Cursor
                            const cursor = messageContent.querySelector('.cursor');
                            if (cursor) cursor.remove();

                            if (data.user_message_id && pendingUserMessageEl) {
                                pendingUserMessageEl.dataset.messageId = data.user_message_id;
                                pendingUserMessageEl = null;
                            }

                            if (data.chat_title) {
                                document.getElementById("chatTitle").textContent = data.chat_title;
                                fetchChats(); // Refresh sidebar
                            }
                        }
                        scrollToBottom();
                    } catch (e) {
                        console.error("Error parsing JSON chunk", e);
                    }
                }
            }
        }

    } catch (e) {
        if (loadingDiv) loadingDiv.remove();
        console.error(e);
        messageContent.innerHTML += `<br><span style="color:red">Connection failed.</span>`;
    }
}

/* ======================================================
   RENDERING UPDATE
====================================================== */
/* ======================================================
   PASTE HANDLING
====================================================== */
document.addEventListener('paste', function (e) {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (const item of items) {
        if (item.type.indexOf('image') !== -1) {
            const blob = item.getAsFile();
            selectedFile = blob;
            const reader = new FileReader();
            reader.onload = function (event) {
                document.getElementById('previewImg').src = event.target.result;
                document.getElementById('imagePreview').style.display = 'block';
                document.getElementById("sendBtn").classList.add("active");
            };
            reader.readAsDataURL(blob);
        }
    }
});

/* ======================================================
   RENDERING UPDATE
====================================================== */
function appendMessage(role, text, imageFile = null, imageUrl = null, messageId = null) {
    const box = document.getElementById("messages");
    const d = document.createElement("div");
    d.className = `message ${role}`;
    if (messageId !== null && messageId !== undefined) {
        d.dataset.messageId = messageId;
    }

    // Parse Markdown if AI
    let content = text;
    if (role === 'ai') {
        content = marked.parse(text || "");
    } else {
        content = text ? `<p>${escapeHtml(text)}</p>` : "";
    }

    const imageHtml = buildImageHtml(imageFile, imageUrl);

    const avatarLabel = role === 'ai' ? 'AI' : 'U';

    // Detect Language for Direction
    const { dir, align } = getMessageDirection(text);

    // Actions Bar (Copy, Edit)
    const actionsHtml = `
        <div class="message-actions">
            ${role === 'user' ? `<button class="action-btn-mini" onclick="editMessage(this)" title="Edit"><span class="material-icons-round">edit</span></button>` : ''}
            <button class="action-btn-mini" onclick="copyMessage(this)" title="Copy"><span class="material-icons-round">content_copy</span></button>
        </div>
    `;

    d.innerHTML = `
        <div class="avatar ${role}">${avatarLabel}</div>
        <div class="message-group" style="flex: 1; display: flex; flex-direction: column; align-items: ${role === 'user' ? 'flex-end' : 'flex-start'};">
            <div class="message-content prose" dir="${dir}" style="text-align: ${align};">
                ${imageHtml}
                ${content}
            </div>
            ${actionsHtml}
        </div>
    `;
    box.appendChild(d);

    // Highlight Code
    d.querySelectorAll('pre code').forEach((el) => {
        hljs.highlightElement(el);
    });

    scrollToBottom();
    return d;
}

// Helper Functions for Actions
function copyMessage(btn) {
    const messageDiv = btn.closest('.message-group').querySelector('.message-content');
    const text = messageDiv.innerText;
    navigator.clipboard.writeText(text).then(() => {
        const originalIcon = btn.innerHTML;
        btn.innerHTML = '<span class="material-icons-round" style="color: #10b981;">check</span>';
        setTimeout(() => btn.innerHTML = originalIcon, 2000);
    });
}

function clearEditingState() {
    if (editingMessageEl) {
        editingMessageEl.classList.remove('editing');
    }
    editingMessageId = null;
    editingMessageEl = null;
    const input = document.getElementById('input');
    if (input && input.dataset.defaultPlaceholder) {
        input.placeholder = input.dataset.defaultPlaceholder;
    }
    const wrapper = document.querySelector('.input-wrapper');
    if (wrapper) wrapper.classList.remove('is-editing');
}

function updateUserMessageContent(messageEl, text, imageFile = null) {
    const messageContent = messageEl.querySelector('.message-content');
    if (!messageContent) return;

    const existingImageHtml = imageFile ? "" : getExistingImageHtml(messageContent);
    const imageHtml = imageFile ? buildImageHtml(imageFile, null) : existingImageHtml;
    const safeText = text ? `<p>${escapeHtml(text)}</p>` : "";
    const { dir, align } = getMessageDirection(text);

    messageContent.innerHTML = `${imageHtml}${safeText}`;
    messageContent.setAttribute("dir", dir);
    messageContent.style.textAlign = align;
}

function editMessage(btn) {
    const messageEl = btn.closest('.message');
    if (!messageEl) return;
    const messageContent = messageEl.querySelector('.message-content');
    const text = messageContent ? messageContent.innerText.trim() : "";
    const messageId = messageEl.dataset.messageId;

    if (!messageId) {
        showToast("انتظر حتى يتم إرسال الرسالة ثم أعد المحاولة.", "warning");
        return;
    }

    clearEditingState();
    editingMessageId = messageId;
    editingMessageEl = messageEl;
    messageEl.classList.add('editing');

    const input = document.getElementById('input');
    if (input && !input.dataset.defaultPlaceholder) {
        input.dataset.defaultPlaceholder = input.placeholder;
    }
    if (input) {
        input.placeholder = "تعديل الرسالة... اضغط Enter لإعادة الإرسال";
        input.value = text;
        input.focus();
    }

    const wrapper = document.querySelector('.input-wrapper');
    if (wrapper) wrapper.classList.add('is-editing');
}

/* ======================================================
   THEME HANDLING
====================================================== */
function toggleTheme() {
    const body = document.body;
    body.classList.toggle("light-theme");
    const isLight = body.classList.contains("light-theme");
    localStorage.setItem("theme", isLight ? "light" : "dark");

    // Update Icon
    const icon = document.getElementById("themeIcon");
    if (icon) icon.textContent = isLight ? "dark_mode" : "brightness_4";
}

// Init Theme
(function initTheme() {
    const saved = localStorage.getItem("theme");
    if (saved === "light") {
        document.body.classList.add("light-theme");
        const icon = document.getElementById("themeIcon");
        if (icon) icon.textContent = "dark_mode";
    }
})();

/* ======================================================
   GLOBAL EXPORTS
====================================================== */
window.toggleSidebar = toggleSidebar;
window.toggleTheme = toggleTheme;
window.createNewChat = createNewChat;

window.promptRename = (id) => {
    const n = prompt("Rename chat to:");
    if (n) renameChatApi(id, n);
}
window.deleteChatApi = deleteChatApi;
window.send = send;
window.handleInput = handleInput;
window.handleKeyDown = handleKeyDown;
window.handleFileSelect = handleFileSelect;
window.clearImage = clearImage;

/* ======================================================
   SETTINGS HANDLING
====================================================== */
function toggleSettings() {
    const modal = document.getElementById("settingsModal");
    if (modal.style.display === "none") {
        modal.style.display = "flex";
    } else {
        modal.style.display = "none";
    }
}

function setTheme(mode) {
    const body = document.body;
    if (mode === 'dark') {
        body.classList.remove("light-theme");
        localStorage.setItem("theme", "dark");
    } else {
        body.classList.add("light-theme");
        localStorage.setItem("theme", "light");
    }

    // Update Active Button in Modal
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(mode)) btn.classList.add('active');
    });

    // Update Top Icon
    const icon = document.getElementById("themeIcon");
    if (icon) icon.textContent = mode === 'light' ? "dark_mode" : "brightness_4";
}

window.toggleSettings = toggleSettings;
window.setTheme = setTheme;

/* INIT */
// Config Marked
marked.setOptions({
    breaks: true, // Enable line breaks
    gfm: true
});

fetchChats();

/* ======================================================
   USER MENU TOGGLE - FIXED
====================================================== */
function toggleUserMenu() {
    const menu = document.getElementById("userMenu");
    if (!menu) return;

    // Toggle Logic
    if (getComputedStyle(menu).display === "none") {
        menu.style.display = "flex";
    } else {
        menu.style.display = "none";
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) {
        alert(message);
        return;
    }
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    setTimeout(() => {
        toast.classList.remove("show");
        toast.addEventListener("transitionend", () => toast.remove(), { once: true });
    }, 2800);
}

function handleUserMenu(action) {
    switch (action) {
        case "profile":
            window.location.href = "/accounts/email/";
            break;
        case "upgrade":
            showToast("ميزة الترقية قادمة قريبًا.");
            break;
        case "personalize":
        case "settings":
            toggleSettings();
            break;
        case "help":
            showToast("للدعم: تواصل معنا عبر البريد داخل حسابك.");
            break;
        default:
            showToast("قريبًا.");
    }
    toggleUserMenu();
}

// Close User Menu when clicking outside
document.addEventListener('click', function (e) {
    const menu = document.getElementById("userMenu");
    const profile = document.querySelector(".user-profile");

    if (menu && getComputedStyle(menu).display === "flex") {
        // If click is outside menu AND outside profile button
        if (!menu.contains(e.target) && (!profile || !profile.contains(e.target))) {
            menu.style.display = "none";
        }
    }
});
window.toggleUserMenu = toggleUserMenu;
window.handleUserMenu = handleUserMenu;

