/**
 * ALD-01 Dashboard Frontend Engine
 * Handles UI routing, WebSockets, API requests, and state management.
 */

const API_EXT = '/api/ext';
const API_V2 = '/api/v2';

const app = {
    state: {
        currentPage: 'chat',
        socket: null,
        metricsInterval: null,
        chatHistory: [],
    },

    // ──────────────────────────────────────────────────────────────
    // Initialization
    // ──────────────────────────────────────────────────────────────
    init() {
        this.bindEvents();
        this.connectWebSocket();
        this.loadInitialData();
        
        // Setup Markdown simple parser for chat
        this.md = {
            render: (text) => {
                let html = text
                    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<div class="code-block">$2</div>')
                    .replace(/`([^`]+)`/g, '<span class="code-inline">$1</span>')
                    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
                    .replace(/\n\n/g, '<br><br>')
                    .replace(/\n/g, '<br>');
                return html;
            }
        };

        this.showPage('chat');
        this.toast('ALD-01 Dashboard initialized', 'success');
    },

    bindEvents() {
        // Sidebar routing
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const page = e.currentTarget.dataset.page;
                if (page) this.showPage(page);
            });
        });

        // Theme Toggle
        document.getElementById('btn-theme-toggle').addEventListener('click', () => {
            document.body.classList.toggle('light-theme'); // To be implemented in CSS
            this.toast('Theme toggled');
        });

        // Sidebar Toggle
        document.getElementById('toggle-sidebar').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('collapsed');
        });

        // Chat Input
        const chatInput = document.getElementById('chat-input');
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendChatMessage();
            }
        });

        document.getElementById('btn-send').addEventListener('click', () => {
            this.sendChatMessage();
        });

        // Terminal Execute
        const termInput = document.getElementById('term-input');
        termInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.executeTerminalCmd(termInput.value);
                termInput.value = '';
            }
        });
        document.getElementById('btn-term-run').addEventListener('click', () => {
            this.executeTerminalCmd(termInput.value);
            termInput.value = '';
        });
    },

    // ──────────────────────────────────────────────────────────────
    // Routing & UI
    // ──────────────────────────────────────────────────────────────
    showPage(pageId) {
        // Update state
        this.state.currentPage = pageId;

        // Update Nav
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.page === pageId) {
                item.classList.add('active');
                document.getElementById('current-page-title').textContent = item.querySelector('span').textContent;
            }
        });

        // Show page
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        
        const target = document.getElementById(`page-${pageId}`);
        if (target) {
            target.classList.add('active');
            target.classList.add('fade-in');
        }

        // Page specific logic
        if (pageId === 'metrics') this.refreshMetrics();
        if (pageId === 'brain') this.refreshBrain();
        if (pageId === 'webhooks') this.loadWebhooks();
    },

    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'info';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'alert-triangle';
        if (type === 'warning') icon = 'alert-circle';

        toast.innerHTML = `
            <i data-lucide="${icon}"></i>
            <div class="toast-content">
                <div class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                <div class="toast-message">${message}</div>
            </div>
        `;
        
        container.appendChild(toast);
        lucide.createIcons();

        setTimeout(() => {
            toast.classList.add('toast-out');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    // ──────────────────────────────────────────────────────────────
    // WebSocket
    // ──────────────────────────────────────────────────────────────
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.state.socket = new WebSocket(`${protocol}//${window.location.host}/ws/dashboard`);
        
        const dot = document.getElementById('ws-status-dot');
        const text = document.getElementById('ws-status-text');

        this.state.socket.onopen = () => {
            dot.style.background = 'var(--accent-green)';
            text.textContent = 'Connected';
            console.log('WS Connected');
        };

        this.state.socket.onclose = () => {
            dot.style.background = 'var(--accent-red)';
            text.textContent = 'Disconnected';
            setTimeout(() => this.connectWebSocket(), 3000);
        };

        this.state.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (e) {
                console.error('WS Parse Error', e);
            }
        };
    },

    handleWebSocketMessage(data) {
        if (data.type === 'metrics_update' && this.state.currentPage === 'metrics') {
            this.renderMetrics(data.payload);
        } else if (data.type === 'chat_response') {
            this.appendChatMessage(data.payload.message, 'assistant');
            document.getElementById('typing-indicator').style.display = 'none';
        } else if (data.type === 'chat_error') {
            this.toast('Chat Engine Error: ' + data.payload.error, 'error');
            document.getElementById('typing-indicator').style.display = 'none';
        }
    },

    // ──────────────────────────────────────────────────────────────
    // Chat System
    // ──────────────────────────────────────────────────────────────
    async sendChatMessage() {
        const input = document.getElementById('chat-input');
        const text = input.value.trim();
        if (!text) return;

        // Clear input
        input.value = '';
        input.style.height = 'auto'; // reset resize

        // Append UI
        this.appendChatMessage(text, 'user');
        document.getElementById('typing-indicator').style.display = 'flex';

        // Get options
        const model = document.getElementById('model-selector').value;
        const mode = document.getElementById('mode-selector').value;

        // Backend call
        try {
            const res = await fetch(`${API_V2}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    session_id: 'default',
                    stream: false,
                    provider: model,
                    mode: mode
                })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Failed to send message');
            
            if (!data.stream) {
                this.appendChatMessage(data.message.content, 'assistant');
                document.getElementById('typing-indicator').style.display = 'none';
                if (data.usage) {
                    document.getElementById('chat-tokens').textContent = `Tokens: ${data.usage.total_tokens}`;
                }
            }
            // If streaming is true, the websocket will handle the response
        } catch (e) {
            this.toast(e.message, 'error');
            document.getElementById('typing-indicator').style.display = 'none';
        }
    },

    appendChatMessage(text, role) {
        const container = document.getElementById('chat-messages');
        
        // Remove empty state if present
        const empty = document.getElementById('analysis-empty');
        if (container.querySelector('.empty-state')) {
            container.innerHTML = '';
        }

        const div = document.createElement('div');
        div.className = `chat-bubble ${role} slide-up`;
        
        if (role === 'assistant') {
            div.innerHTML = this.md.render(text);
        } else {
            div.textContent = text; // Prevent XSS for user input
        }

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    },

    clearChat() {
        if (confirm("Clear chat history?")) {
            document.getElementById('chat-messages').innerHTML = `
                <div class="empty-state">
                    <i data-lucide="message-square" class="empty-state-icon"></i>
                    <h3 class="empty-state-title">Chat Cleared</h3>
                    <p class="empty-state-text">Start a new conversation.</p>
                </div>
            `;
            lucide.createIcons();
            this.toast('Chat cleared');
        }
    },

    // ──────────────────────────────────────────────────────────────
    // Metrics 
    // ──────────────────────────────────────────────────────────────
    async refreshMetrics() {
        try {
            const res = await fetch(`${API_EXT}/status`);
            const data = await res.json();
            this.renderMetrics(data);
        } catch (e) {
            this.toast('Failed to load metrics', 'error');
        }
    },

    renderMetrics(data) {
        if (!data || !data.system) return;

        const sys = data.system;
        document.getElementById('stat-cpu').textContent = Math.round(sys.cpu_percent) + '%';
        document.getElementById('prog-cpu').style.width = sys.cpu_percent + '%';
        
        if (sys.memory) {
            const memUsed = (sys.memory.used / (1024 ** 3)).toFixed(1);
            document.getElementById('stat-mem').textContent = memUsed + ' GB';
            document.getElementById('prog-mem').style.width = sys.memory.percent + '%';
        }

        const uptime = data.uptime_seconds || 0;
        const hours = Math.floor(uptime / 3600);
        const mins = Math.floor((uptime % 3600) / 60);
        document.getElementById('stat-uptime').textContent = `${hours}h ${mins}m`;

        document.getElementById('stat-active').textContent = data.healthy ? "Stable" : "Degraded";
        document.getElementById('stat-active').className = `stat-value text-${data.healthy ? 'green' : 'red'}`;

        document.getElementById('stat-workers').textContent = `${data.workers?.active || 0} active`;
    },

    // ──────────────────────────────────────────────────────────────
    // Code Analyzer
    // ──────────────────────────────────────────────────────────────
    async runCodeAnalysis() {
        const path = document.getElementById('analyze-path').value || '.';
        
        this.toast(`Analyzing path: ${path}...`);
        
        try {
            const res = await fetch(`${API_EXT}/code/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Analysis failed');

            document.getElementById('analysis-empty').style.display = 'none';
            document.getElementById('analysis-results').style.display = 'block';

            // Stats
            document.getElementById('ana-score').textContent = data.quality_score;
            document.getElementById('ana-files').textContent = data.files_analyzed;
            document.getElementById('ana-sec').textContent = data.security_issues.length;
            
            // Render Hotspots
            const hsTbody = document.getElementById('sec-hotspots-body');
            hsTbody.innerHTML = '';
            
            if (data.security_issues.length === 0) {
                hsTbody.innerHTML = '<tr><td colspan="3" class="text-center text-green py-4">No critical security issues found!</td></tr>';
            } else {
                data.security_issues.slice(0, 10).forEach(issue => {
                    hsTbody.innerHTML += `
                        <tr>
                            <td class="font-mono text-xs">${issue.file.split(/[\\/]/).pop()}:${issue.line}</td>
                            <td class="text-xs">${issue.rule}</td>
                            <td><span class="badge badge-red">${issue.severity}</span></td>
                        </tr>
                    `;
                });
            }

            // Suggestions
            const suggList = document.getElementById('ana-suggestions');
            suggList.innerHTML = '';
            data.suggestions.slice(0, 5).forEach(s => {
                suggList.innerHTML += `
                    <li class="flex gap-3 text-sm border-l-2 border-accent pl-3 py-1">
                        <i data-lucide="info" class="w-4 h-4 text-accent shrink-0 mt-0.5"></i>
                        <span>${s}</span>
                    </li>
                `;
            });
            lucide.createIcons();
            
            this.toast('Analysis complete', 'success');

        } catch (e) {
            this.toast(e.message, 'error');
        }
    },

    // ──────────────────────────────────────────────────────────────
    // Terminal
    // ──────────────────────────────────────────────────────────────
    async executeTerminalCmd(cmd) {
        if (!cmd.trim()) return;

        const term = document.getElementById('term-output');
        term.innerHTML += `<div class="terminal-line"><span class="terminal-prompt">$</span> ${cmd}</div>`;
        term.scrollTop = term.scrollHeight;

        try {
            const res = await fetch(`${API_EXT}/executor/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            const data = await res.json();

            if (data.stdout) {
                term.innerHTML += `<div class="terminal-line text-muted">${data.stdout.replace(/\n/g, '<br>')}</div>`;
            }
            if (data.stderr) {
                term.innerHTML += `<div class="terminal-line terminal-error">${data.stderr.replace(/\n/g, '<br>')}</div>`;
            }
            if (!data.stdout && !data.stderr && data.success) {
                term.innerHTML += `<div class="terminal-line text-muted">[Success]</div>`;
            }
            
            if (data.working_dir) {
                document.getElementById('term-cwd').textContent = data.working_dir;
            }

            term.scrollTop = term.scrollHeight;

        } catch (e) {
            term.innerHTML += `<div class="terminal-line terminal-error">Network error: ${e.message}</div>`;
            term.scrollTop = term.scrollHeight;
        }
    },

    clearTerminal() {
        document.getElementById('term-output').innerHTML = '';
    },

    // ──────────────────────────────────────────────────────────────
    // Brain (Knowledge)
    // ──────────────────────────────────────────────────────────────
    async refreshBrain() {
        try {
            const res = await fetch(`${API_EXT}/brain/graph`);
            const data = await res.json();

            document.getElementById('stat-brain-nodes').textContent = data.stats.total_entities || 0;
            document.getElementById('stat-brain-edges').textContent = data.stats.total_relations || 0;
            
            // Populate table
            const tbody = document.querySelector('#brain-table tbody');
            tbody.innerHTML = '';
            
            if (data.entities && data.entities.length > 0) {
                // Get unique types
                const types = new Set(data.entities.map(e => e.entityType));
                document.getElementById('stat-brain-types').textContent = types.size;

                data.entities.slice(0, 10).forEach(ent => {
                    tbody.innerHTML += `
                        <tr>
                            <td class="font-medium">${ent.name}</td>
                            <td><span class="badge badge-purple">${ent.entityType}</span></td>
                            <td class="text-muted text-xs">${ent.observations.slice(0,2).join(', ')}...</td>
                            <td><button class="btn btn-sm btn-ghost">View</button></td>
                        </tr>
                    `;
                });
            } else {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-4">Knowledge graph is empty</td></tr>';
            }

        } catch (e) {
            this.toast('Failed to load brain data', 'error');
        }
    },

    // ──────────────────────────────────────────────────────────────
    // Exports
    // ──────────────────────────────────────────────────────────────
    async exportData(type) {
        try {
            this.toast(`Generating ${type} export...`);
            let endpoint = '';
            if (type === 'brain') endpoint = '/export/brain';
            else if (type === 'chat') endpoint = '/export/chat?limit=50';
            else if (type === 'full') endpoint = '/export/system';

            const res = await fetch(`${API_EXT}${endpoint}`, { method: 'POST' });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.error || 'Export failed');

            this.toast(`Export successful! Saved to: ${data.path}`, 'success');

        } catch (e) {
            this.toast(`Export error: ${e.message}`, 'error');
        }
    },

    // ──────────────────────────────────────────────────────────────
    // Webhooks & Modals
    // ──────────────────────────────────────────────────────────────
    showWebhookModal() {
        document.getElementById('modal-webhook').classList.add('active');
    },

    closeModal(name) {
        document.getElementById(`modal-${name}`).classList.remove('active');
    },

    loadInitialData() {
        // Run light initial fetches silently
    }

};

// Boot
window.document.addEventListener('DOMContentLoaded', () => {
    app.init();
});
