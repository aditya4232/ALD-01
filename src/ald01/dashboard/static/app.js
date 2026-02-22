/**
 * ALD-01 Dashboard Application Logic v2
 * Handles: Brain, Skills, MCP, Integrations, Cron, Settings, Enhanced Chat
 */

(function () {
  'use strict';

  const V2 = '/api/v2';

  async function fetchJSON(url, opts) {
    const resp = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  /* ─────────────────────────────────────────────
   * PAGE ROUTER EXTENSION
   * ───────────────────────────────────────────── */

  const PAGE_HANDLERS = {
    brain: loadBrain,
    skills: loadSkills,
    mcp: loadMCP,
    integrations: scanIntegrations,
    cron: loadCron,
    settings: () => showSettingsTab('general'),
    chat: loadChatHistory,
  };

  // Patch the existing showPage function
  const _origShowPage = window.showPage;
  window.showPage = function (page) {
    if (typeof _origShowPage === 'function') _origShowPage(page);
    const handler = PAGE_HANDLERS[page];
    if (handler) handler();
  };

  /* ─────────────────────────────────────────────
   * BRAIN
   * ───────────────────────────────────────────── */

  async function loadBrain() {
    try {
      const data = await fetchJSON('/api/ext/brain');
      renderBrainStats(data);
      renderBrainCanvas(data);
      renderBrainSkills(data);
      renderBrainGrowth(data);
    } catch (e) {
      console.warn('Brain load failed:', e);
      renderBrainEmpty();
    }
  }

  function renderBrainStats(data) {
    const stats = data.stats || {};
    const el = document.getElementById('brainStats');
    if (!el) return;
    el.innerHTML = [
      cardStat(stats.total_nodes || 0, 'Neural Nodes'),
      cardStat(stats.total_connections || 0, 'Connections'),
      cardStat(stats.skills_count || 0, 'Skills'),
      cardStat((stats.growth_rate || 0).toFixed(1) + '%', 'Growth'),
    ].join('');
  }

  function renderBrainCanvas(data) {
    const canvas = document.getElementById('brainCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;
    const nodes = data.nodes || data.visualization?.nodes || [];
    const connections = data.connections || data.visualization?.connections || [];

    ctx.clearRect(0, 0, W, H);

    // Category colors
    const COLORS = {
      skill: '#3b82f6', memory: '#8b5cf6', reasoning: '#06b6d4',
      aptitude: '#10b981', knowledge: '#f59e0b', tool: '#ef4444',
      language: '#ec4899', personality: '#a78bfa', default: '#64748b',
    };

    // Layout nodes in a circular pattern per category
    const categories = {};
    nodes.forEach((n) => {
      const cat = n.category || 'default';
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push(n);
    });

    const catKeys = Object.keys(categories);
    const positioned = {};
    const centerX = W / 2;
    const centerY = H / 2;
    const outerR = Math.min(W, H) * 0.38;

    catKeys.forEach((cat, ci) => {
      const angle0 = (ci / catKeys.length) * Math.PI * 2 - Math.PI / 2;
      const items = categories[cat];
      items.forEach((node, ni) => {
        const spread = 0.6 / Math.max(items.length, 1);
        const a = angle0 + (ni - items.length / 2) * spread;
        const r = outerR * (0.55 + Math.random() * 0.45);
        positioned[node.id] = {
          x: centerX + Math.cos(a) * r,
          y: centerY + Math.sin(a) * r,
          node,
        };
      });
    });

    // Draw connections
    ctx.lineWidth = 0.5;
    connections.forEach((c) => {
      const from = positioned[c.from];
      const to = positioned[c.to];
      if (!from || !to) return;
      const alpha = Math.min(0.6, (c.strength || 0.1) * 2);
      ctx.strokeStyle = `rgba(59,130,246,${alpha})`;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    // Draw nodes
    Object.values(positioned).forEach((p) => {
      const strength = p.node.strength || 0.3;
      const radius = 3 + strength * 8;
      const color = COLORS[p.node.category] || COLORS.default;

      // Glow
      ctx.shadowColor = color;
      ctx.shadowBlur = 6;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Label (only for strong nodes)
      if (strength > 0.4) {
        ctx.fillStyle = '#94a3b8';
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(p.node.label || p.node.id, p.x, p.y + radius + 12);
      }
    });

    // Center label
    ctx.fillStyle = 'rgba(59,130,246,0.12)';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 28, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#e2e8f0';
    ctx.font = '600 13px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('ALD', centerX, centerY);
  }

  function renderBrainSkills(data) {
    const el = document.getElementById('brainSkillsList');
    if (!el) return;
    const nodes = (data.nodes || []).filter((n) => n.category === 'skill');
    if (!nodes.length) {
      el.innerHTML = '<p style="color:var(--text-dim)">No active skills yet.</p>';
      return;
    }
    nodes.sort((a, b) => (b.strength || 0) - (a.strength || 0));
    el.innerHTML = nodes
      .map((n) => {
        const pct = Math.round((n.strength || 0) * 100);
        return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
          <span style="flex:1;font-size:13px">${n.label || n.id}</span>
          <div style="width:120px;height:6px;background:var(--bg-primary);border-radius:3px;overflow:hidden">
            <div style="width:${pct}%;height:100%;background:var(--accent);border-radius:3px"></div>
          </div>
          <span style="font-size:11px;color:var(--text-dim);min-width:32px;text-align:right">${pct}%</span>
        </div>`;
      })
      .join('');
  }

  function renderBrainGrowth(data) {
    const el = document.getElementById('brainGrowth');
    if (!el) return;
    const stats = data.stats || {};
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        ${miniStat(stats.topics_learned || 0, 'Topics Learned')}
        ${miniStat(stats.total_interactions || 0, 'Interactions')}
        ${miniStat(stats.strongest_category || 'N/A', 'Top Category')}
        ${miniStat(stats.weakest_category || 'N/A', 'Needs Growth')}
      </div>`;
  }

  function renderBrainEmpty() {
    const el = document.getElementById('brainStats');
    if (el) el.innerHTML = [cardStat(0, 'Neural Nodes'), cardStat(0, 'Connections'), cardStat(0, 'Skills'), cardStat('0%', 'Growth')].join('');
  }

  /* ─────────────────────────────────────────────
   * SKILLS
   * ───────────────────────────────────────────── */

  async function loadSkills() {
    try {
      const [available, stats] = await Promise.all([
        fetchJSON(V2 + '/skills/available'),
        fetchJSON(V2 + '/skills/stats'),
      ]);
      renderSkillStats(stats);
      renderSkillList(available);
    } catch (e) {
      console.warn('Skills load failed:', e);
    }
  }

  function renderSkillStats(s) {
    const el = document.getElementById('skillStats');
    if (!el) return;
    el.innerHTML = [
      cardStat(s.total_available || 0, 'Available'),
      cardStat(s.installed || 0, 'Installed'),
      cardStat(s.enabled || 0, 'Enabled'),
      cardStat((s.categories || []).length, 'Categories'),
    ].join('');
  }

  function renderSkillList(skills) {
    const el = document.getElementById('skillsList');
    if (!el) return;
    el.innerHTML = skills
      .map(
        (s) => `
        <div class="card" style="padding:0">
          <div class="card-body" style="padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:8px">
              <strong style="font-size:13px">${esc(s.name)}</strong>
              <span class="badge ${s.installed ? (s.enabled ? 'badge-success' : 'badge-warning') : 'badge-danger'}">${s.installed ? (s.enabled ? 'Active' : 'Disabled') : 'Not Installed'}</span>
            </div>
            <p style="font-size:12px;color:var(--text-secondary);margin-bottom:10px;line-height:1.5">${esc(s.description)}</p>
            <div style="display:flex;gap:4px">
              ${s.installed
                ? `<button class="btn btn-sm" onclick="toggleSkill('${s.id}',${!s.enabled})">${s.enabled ? 'Disable' : 'Enable'}</button>
                   <button class="btn btn-sm" onclick="uninstallSkill('${s.id}')">Remove</button>`
                : `<button class="btn btn-primary btn-sm" onclick="installSkill('${s.id}')">Install</button>`}
            </div>
          </div>
        </div>`
      )
      .join('');
  }

  window.installSkill = async (id) => {
    await fetchJSON(V2 + `/skills/${id}/install`, { method: 'POST' });
    loadSkills();
  };
  window.uninstallSkill = async (id) => {
    await fetchJSON(V2 + `/skills/${id}/uninstall`, { method: 'POST' });
    loadSkills();
  };
  window.toggleSkill = async (id, enable) => {
    await fetchJSON(V2 + `/skills/${id}/${enable ? 'enable' : 'disable'}`, { method: 'POST' });
    loadSkills();
  };

  /* ─────────────────────────────────────────────
   * MCP
   * ───────────────────────────────────────────── */

  async function loadMCP() {
    try {
      const [available, stats] = await Promise.all([
        fetchJSON(V2 + '/mcp/available'),
        fetchJSON(V2 + '/mcp/stats'),
      ]);
      renderMCPStats(stats);
      renderMCPList(available);
    } catch (e) {
      console.warn('MCP load failed:', e);
    }
  }

  function renderMCPStats(s) {
    const el = document.getElementById('mcpStats');
    if (!el) return;
    el.innerHTML = [
      cardStat(s.available || 0, 'Available'),
      cardStat(s.installed || 0, 'Installed'),
      cardStat(s.enabled || 0, 'Enabled'),
      cardStat(s.running || 0, 'Running'),
    ].join('');
  }

  function renderMCPList(servers) {
    const el = document.getElementById('mcpList');
    if (!el) return;
    el.innerHTML = servers
      .map(
        (s) => `
        <div class="card" style="padding:0">
          <div class="card-body" style="padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
              <strong style="font-size:13px">${esc(s.name)}</strong>
              <span class="badge ${s.installed ? 'badge-success' : 'badge-danger'}">${s.installed ? 'Installed' : 'Available'}</span>
            </div>
            <p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">${esc(s.description)}</p>
            <div style="display:flex;gap:4px">
              ${s.installed
                ? `<button class="btn btn-sm" onclick="uninstallMCP('${s.id}')">Remove</button>`
                : `<button class="btn btn-primary btn-sm" onclick="installMCP('${s.id}')">Install</button>`}
            </div>
          </div>
        </div>`
      )
      .join('');
  }

  window.installMCP = async (id) => {
    await fetchJSON(V2 + `/mcp/${id}/install`, { method: 'POST' });
    loadMCP();
  };
  window.uninstallMCP = async (id) => {
    await fetchJSON(V2 + `/mcp/${id}/uninstall`, { method: 'POST' });
    loadMCP();
  };

  /* ─────────────────────────────────────────────
   * INTEGRATIONS
   * ───────────────────────────────────────────── */

  async function scanIntegrations() {
    const el = document.getElementById('integrationsList');
    if (!el) return;
    el.innerHTML = '<p style="color:var(--text-dim)">Scanning system...</p>';
    try {
      const data = await fetchJSON(V2 + '/integrations/scan');
      const tools = data.tools || [];
      if (!tools.length) {
        el.innerHTML = '<p style="color:var(--text-dim)">No external tools detected.</p>';
        return;
      }
      el.innerHTML = tools
        .map(
          (t) => `
          <div class="card" style="padding:0">
            <div class="card-body" style="padding:14px">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <i class="lucide-check-circle" style="color:var(--success);font-size:14px"></i>
                <strong style="font-size:13px">${esc(t.display_name)}</strong>
              </div>
              <p style="font-size:11px;color:var(--text-dim);margin-bottom:4px">${esc(t.path)}</p>
              <p style="font-size:11px;color:var(--text-secondary)">${esc(t.version || 'Version unknown')}</p>
            </div>
          </div>`
        )
        .join('');
    } catch (e) {
      el.innerHTML = `<p style="color:var(--danger)">Scan failed: ${esc(e.message)}</p>`;
    }
  }

  /* ─────────────────────────────────────────────
   * CRON JOBS
   * ───────────────────────────────────────────── */

  async function loadCron() {
    const el = document.getElementById('cronList');
    if (!el) return;
    try {
      const data = await fetchJSON('/api/ext/scheduler/jobs');
      const jobs = Array.isArray(data) ? data : data.jobs || [];
      if (!jobs.length) {
        el.innerHTML = '<p style="color:var(--text-dim)">No scheduled jobs.</p>';
        return;
      }
      el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="border-bottom:1px solid var(--border);text-align:left">
          <th style="padding:8px">Name</th><th style="padding:8px">Schedule</th>
          <th style="padding:8px">Last Run</th><th style="padding:8px">Status</th>
        </tr></thead>
        <tbody>${jobs
          .map(
            (j) => `<tr style="border-bottom:1px solid rgba(255,255,255,0.03)">
              <td style="padding:8px;font-weight:500">${esc(j.name || j.id)}</td>
              <td style="padding:8px;font-family:var(--mono);font-size:12px">${esc(j.schedule || 'N/A')}</td>
              <td style="padding:8px;font-size:12px;color:var(--text-dim)">${j.last_run ? new Date(j.last_run * 1000).toLocaleString() : 'Never'}</td>
              <td style="padding:8px"><span class="badge ${j.enabled ? 'badge-success' : 'badge-danger'}">${j.enabled ? 'Active' : 'Disabled'}</span></td>
            </tr>`
          )
          .join('')}
        </tbody></table>`;
    } catch (e) {
      el.innerHTML = `<p style="color:var(--text-dim)">No scheduler data available.</p>`;
    }
  }

  /* ─────────────────────────────────────────────
   * SETTINGS (7 sub-tabs)
   * ───────────────────────────────────────────── */

  let _activeSettingsTab = 'general';

  function showSettingsTab(tab) {
    _activeSettingsTab = tab;
    document.querySelectorAll('[id^="stab-"]').forEach((b) => {
      b.className = b.id === `stab-${tab}` ? 'btn btn-primary btn-sm' : 'btn btn-sm';
    });

    const handlers = {
      general: loadSettingsGeneral,
      config: loadSettingsConfig,
      test: loadSettingsTest,
      database: loadSettingsDatabase,
      snapshots: loadSettingsSnapshots,
      language: loadSettingsLanguage,
      about: loadSettingsAbout,
    };
    (handlers[tab] || handlers.general)();
  }

  async function loadSettingsGeneral() {
    const el = document.getElementById('settingsContent');
    try {
      const data = await fetchJSON(V2 + '/settings/all');
      el.innerHTML = `
        <div class="card"><div class="card-header">General Settings</div><div class="card-body">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
            ${settingRow('Brain Power', data.brain_power || 5, 'Range: 1-10')}
            ${settingRow('Language', data.language || 'en', 'en / hi / hinglish')}
            ${settingRow('Autostart', data.autostart ? 'Enabled' : 'Disabled', '')}
            ${settingRow('Voice', data.voice_enabled ? 'On' : 'Off', '')}
          </div>
        </div></div>`;
    } catch {
      el.innerHTML = '<p style="color:var(--text-dim)">Could not load settings.</p>';
    }
  }

  async function loadSettingsConfig() {
    const el = document.getElementById('settingsContent');
    try {
      const data = await fetchJSON(V2 + '/config/all');
      const categories = {};
      Object.entries(data).forEach(([key, info]) => {
        const cat = info.category || 'other';
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push({ key, ...info });
      });
      el.innerHTML = Object.entries(categories)
        .map(
          ([cat, items]) => `
          <div class="card" style="margin-bottom:12px">
            <div class="card-header" style="text-transform:capitalize">${esc(cat)}</div>
            <div class="card-body">
              ${items
                .map(
                  (i) => `<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                    <div><div style="font-size:13px;font-weight:500">${esc(i.key)}</div><div style="font-size:11px;color:var(--text-dim)">${esc(i.description)}</div></div>
                    <div style="font-family:var(--mono);font-size:12px;color:var(--accent)">${esc(String(i.value))}</div>
                  </div>`
                )
                .join('')}
            </div>
          </div>`
        )
        .join('');
    } catch {
      el.innerHTML = '<p style="color:var(--text-dim)">Config not available.</p>';
    }
  }

  async function loadSettingsTest() {
    const el = document.getElementById('settingsContent');
    el.innerHTML = '<div class="card"><div class="card-body"><p style="color:var(--text-dim)">Running diagnostics...</p></div></div>';
    try {
      const data = await fetchJSON(V2 + '/settings/test');
      const tests = data.tests || [];
      const summary = data.summary || {};
      el.innerHTML = `
        <div class="card">
          <div class="card-header">System Test Results
            <span class="badge ${summary.health === 'healthy' ? 'badge-success' : 'badge-warning'}">${summary.health || 'unknown'}</span>
          </div>
          <div class="card-body">
            ${tests
              .map(
                (t) => `<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                  <i class="lucide-${t.status === 'pass' ? 'check-circle' : 'x-circle'}" style="color:${t.status === 'pass' ? 'var(--success)' : 'var(--danger)'};font-size:16px"></i>
                  <div style="flex:1"><div style="font-size:13px;font-weight:500">${esc(t.name)}</div><div style="font-size:11px;color:var(--text-dim)">${esc(t.detail)}</div></div>
                </div>`
              )
              .join('')}
            <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--border);display:flex;gap:24px">
              ${miniStat(summary.passed || 0, 'Passed')}
              ${miniStat(summary.failed || 0, 'Failed')}
              ${miniStat(summary.total || 0, 'Total')}
            </div>
          </div>
        </div>`;
    } catch (e) {
      el.innerHTML = `<p style="color:var(--danger)">Test failed: ${esc(e.message)}</p>`;
    }
  }

  async function loadSettingsDatabase() {
    const el = document.getElementById('settingsContent');
    try {
      const data = await fetchJSON(V2 + '/database/overview');
      if (!data.exists) {
        el.innerHTML = '<p style="color:var(--text-dim)">No database found.</p>';
        return;
      }
      const tables = data.tables || [];
      const maxRows = Math.max(...tables.map((t) => t.row_count), 1);

      el.innerHTML = `
        <div class="grid grid-4" style="margin-bottom:16px">
          ${cardStat(data.table_count || 0, 'Tables')}
          ${cardStat(data.total_rows || 0, 'Total Rows')}
          ${cardStat((data.size_mb || 0) + ' MB', 'Size')}
          ${cardStat(data.integrity === 'ok' ? 'OK' : 'Issue', 'Integrity')}
        </div>
        <div class="card">
          <div class="card-header">Table Overview</div>
          <div class="card-body">
            ${tables
              .map((t) => {
                const pct = Math.round((t.row_count / maxRows) * 100);
                return `<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="font-size:13px;font-weight:500;font-family:var(--mono)">${esc(t.name)}</span>
                    <span style="font-size:12px;color:var(--text-dim)">${t.row_count} rows · ${t.column_count} cols</span>
                  </div>
                  <div style="width:100%;height:6px;background:var(--bg-primary);border-radius:3px;overflow:hidden">
                    <div style="width:${pct}%;height:100%;background:var(--accent);border-radius:3px;transition:width 0.5s"></div>
                  </div>
                </div>`;
              })
              .join('')}
          </div>
        </div>`;
    } catch {
      el.innerHTML = '<p style="color:var(--text-dim)">Database overview not available.</p>';
    }
  }

  async function loadSettingsSnapshots() {
    const el = document.getElementById('settingsContent');
    try {
      const snapshots = await fetchJSON(V2 + '/revert/snapshots');
      el.innerHTML = `
        <div class="card">
          <div class="card-header">System Snapshots
            <button class="btn btn-primary btn-sm" onclick="createSnapshot()">Create Snapshot</button>
          </div>
          <div class="card-body">
            ${!snapshots.length
              ? '<p style="color:var(--text-dim)">No snapshots yet.</p>'
              : snapshots
                  .map(
                    (s) => `<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                      <div>
                        <div style="font-size:13px;font-weight:500;font-family:var(--mono)">${esc(s.name)}</div>
                        <div style="font-size:11px;color:var(--text-dim)">${s.label ? esc(s.label) + ' · ' : ''}${s.files?.length || 0} files</div>
                      </div>
                      <div style="display:flex;gap:4px">
                        <button class="btn btn-sm" onclick="restoreSnapshot('${esc(s.name)}')">Restore</button>
                        <button class="btn btn-sm" onclick="deleteSnapshot('${esc(s.name)}')">Delete</button>
                      </div>
                    </div>`
                  )
                  .join('')}
          </div>
        </div>`;
    } catch {
      el.innerHTML = '<p style="color:var(--text-dim)">Snapshots not available.</p>';
    }
  }

  window.createSnapshot = async () => {
    await fetchJSON(V2 + '/revert/snapshot', { method: 'POST', body: JSON.stringify({ label: 'manual' }) });
    loadSettingsSnapshots();
  };
  window.restoreSnapshot = async (name) => {
    if (!confirm('Restore this snapshot? Current config will be backed up first.')) return;
    await fetchJSON(V2 + `/revert/restore/${name}`, { method: 'POST' });
    loadSettingsSnapshots();
  };
  window.deleteSnapshot = async (name) => {
    await fetchJSON(V2 + `/revert/snapshots/${name}`, { method: 'DELETE' });
    loadSettingsSnapshots();
  };

  function loadSettingsLanguage() {
    const el = document.getElementById('settingsContent');
    el.innerHTML = `
      <div class="card"><div class="card-header">Language</div><div class="card-body">
        <div style="display:flex;gap:12px">
          <button class="btn btn-sm" onclick="setLang('en')">English</button>
          <button class="btn btn-sm" onclick="setLang('hi')">Hindi</button>
          <button class="btn btn-sm" onclick="setLang('hinglish')">Hinglish</button>
        </div>
      </div></div>`;
  }

  window.setLang = async (lang) => {
    try { await fetchJSON('/api/ext/language/' + lang, { method: 'POST' }); } catch {}
    loadSettingsLanguage();
  };

  function loadSettingsAbout() {
    const el = document.getElementById('settingsContent');
    el.innerHTML = `
      <div class="card"><div class="card-header">About ALD-01</div><div class="card-body">
        <div style="text-align:center;padding:20px">
          <div style="width:64px;height:64px;background:var(--gradient-2);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:22px;color:white;margin-bottom:12px">AI</div>
          <h2 style="font-size:20px;font-weight:700;margin-bottom:4px">ALD-01</h2>
          <p style="color:var(--text-dim);font-size:13px;margin-bottom:16px">Advanced Local Desktop Intelligence</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;max-width:300px;margin:0 auto;text-align:left">
            ${aboutRow('Version', '2.0.0')}
            ${aboutRow('Runtime', 'Python 3.12+')}
            ${aboutRow('License', 'MIT')}
            ${aboutRow('Author', 'Aditya Shenvi')}
          </div>
          <p style="color:var(--text-dim);font-size:11px;margin-top:16px">Open Source · Local First · Privacy Focused</p>
        </div>
      </div></div>`;
  }

  /* ─────────────────────────────────────────────
   * ENHANCED CHAT
   * ───────────────────────────────────────────── */

  async function loadChatHistory() {
    const el = document.getElementById('chatHistory');
    if (!el) return;
    try {
      const convs = await fetchJSON(V2 + '/chat/conversations');
      if (!convs.length) {
        el.innerHTML = '<p style="padding:12px;font-size:12px;color:var(--text-dim)">No conversations yet.</p>';
        return;
      }
      el.innerHTML = convs
        .map(
          (c) => `<div class="nav-item" style="font-size:12px;padding:8px 10px;margin-bottom:1px"
            onclick="openConversation('${c.id}')">
            <i class="lucide-message-square" style="font-size:13px"></i>
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.title)}</span>
          </div>`
        )
        .join('');
    } catch {
      el.innerHTML = '<p style="padding:12px;font-size:12px;color:var(--text-dim)">Chat history unavailable.</p>';
    }
  }

  window.openConversation = async (id) => {
    window.conversationId = id;
    try {
      const msgs = await fetchJSON(V2 + `/chat/conversations/${id}/messages`);
      const el = document.getElementById('chatMessages');
      if (!el) return;
      el.innerHTML = msgs
        .map(
          (m) => `<div class="chat-message ${m.role}">
            <div>${formatContent(m.content)}</div>
            <div class="meta">${m.agent || ''} ${m.model ? '· ' + m.model : ''}</div>
          </div>`
        )
        .join('');
      el.scrollTop = el.scrollHeight;
    } catch {}
  };

  window.newChat = async () => {
    try {
      const conv = await fetchJSON(V2 + '/chat/new', {
        method: 'POST',
        body: JSON.stringify({}),
      });
      window.conversationId = conv.id;
      document.getElementById('chatMessages').innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:12px">
          <div style="width:48px;height:48px;background:var(--gradient-2);border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:700;color:white">AI</div>
          <div style="font-size:18px;font-weight:600">ALD-01</div>
          <div style="color:var(--text-dim);text-align:center;max-width:400px">New conversation started. Ask me anything.</div>
        </div>`;
      loadChatHistory();
    } catch {}
  };

  window.toggleVoice = async (enabled) => {
    try {
      await fetchJSON(V2 + '/chat/voice/toggle', {
        method: 'POST',
        body: JSON.stringify({ enabled }),
      });
    } catch {}
  };

  /* ─────────────────────────────────────────────
   * SHARED UTILITIES
   * ───────────────────────────────────────────── */

  function cardStat(value, label) {
    return `<div class="card"><div class="stat"><div class="stat-value">${esc(String(value))}</div><div class="stat-label">${esc(label)}</div></div></div>`;
  }

  function miniStat(value, label) {
    return `<div style="text-align:center"><div style="font-size:18px;font-weight:700;color:var(--accent)">${esc(String(value))}</div><div style="font-size:11px;color:var(--text-dim)">${esc(label)}</div></div>`;
  }

  function settingRow(label, value, hint) {
    return `<div style="padding:8px 0"><div style="font-size:13px;font-weight:500">${esc(label)}</div><div style="font-size:14px;color:var(--accent);font-weight:600">${esc(String(value))}</div>${hint ? `<div style="font-size:11px;color:var(--text-dim)">${esc(hint)}</div>` : ''}</div>`;
  }

  function aboutRow(label, value) {
    return `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03)"><span style="color:var(--text-dim);font-size:12px">${esc(label)}</span><span style="font-size:12px">${esc(value)}</span></div>`;
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function formatContent(s) {
    return esc(s)
      .replace(/\n/g, '<br>')
      .replace(
        /```([\s\S]*?)```/g,
        '<pre style="background:var(--bg-input);padding:12px;border-radius:8px;overflow-x:auto;margin:8px 0;font-family:var(--mono);font-size:12px">$1</pre>'
      );
  }

  // Expose page loaders globally
  window.loadBrain = loadBrain;
  window.loadSkills = loadSkills;
  window.loadMCP = loadMCP;
  window.scanIntegrations = scanIntegrations;
  window.loadCron = loadCron;
  window.showSettingsTab = showSettingsTab;
  window.loadChatHistory = loadChatHistory;
})();
