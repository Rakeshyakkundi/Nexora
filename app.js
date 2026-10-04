// ============================================================
// Auth
// ============================================================
const API_BASE = 'http://localhost:8000';

let authToken = localStorage.getItem('authToken');
let currentUsername = localStorage.getItem('authUsername');

const authScreen = document.getElementById('authScreen');
const appShell = document.getElementById('appShell');

function clearAuthForms() {
  ['loginForm', 'signupForm', 'resetForm'].forEach((formId) => {
    const form = document.getElementById(formId);
    form.reset();
    form.querySelectorAll('input').forEach((input) => {
      input.value = '';
    });
  });
  ['loginError', 'loginSignupPrompt', 'signupError', 'resetError', 'resetSuccess'].forEach((id) => {
    document.getElementById(id).classList.add('hidden');
  });
  showAuthForm('loginForm');
}

function showAuthScreen() {
  authToken = null;
  currentUsername = null;
  localStorage.removeItem('authToken');
  localStorage.removeItem('authUsername');
  clearAuthForms();
  resetLiveWorkflow();
  authScreen.classList.remove('hidden');
  appShell.classList.add('hidden');
}

function showApp() {
  document.getElementById('currentUsernameLabel').textContent = currentUsername || '';
  authScreen.classList.add('hidden');
  appShell.classList.remove('hidden');
}

function setAuthenticated(token, username) {
  authToken = token;
  currentUsername = username;
  localStorage.setItem('authToken', token);
  localStorage.setItem('authUsername', username);
  resetLiveWorkflow();
  showApp();
  activateTab('upload');
}

function showAuthForm(name) {
  ['loginForm', 'signupForm', 'resetForm'].forEach((id) => {
    document.getElementById(id).classList.toggle('hidden', id !== name);
  });
}

document.getElementById('goToSignup').addEventListener('click', () => showAuthForm('signupForm'));
document.getElementById('goToSignupFromError').addEventListener('click', () => showAuthForm('signupForm'));
document.getElementById('goToReset').addEventListener('click', () => showAuthForm('resetForm'));
document.getElementById('goToLoginFromSignup').addEventListener('click', () => showAuthForm('loginForm'));
document.getElementById('goToLoginFromReset').addEventListener('click', () => showAuthForm('loginForm'));

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById('loginError');
  const promptEl = document.getElementById('loginSignupPrompt');
  errorEl.classList.add('hidden');
  promptEl.classList.add('hidden');

  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;

  try {
    const res = await authFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    setAuthenticated(res.token, res.username);
  } catch (err) {
    if (err.status === 404) {
      promptEl.classList.remove('hidden');
    } else {
      errorEl.textContent = err.message;
      errorEl.classList.remove('hidden');
    }
  }
});

document.getElementById('signupForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById('signupError');
  errorEl.classList.add('hidden');

  const username = document.getElementById('signupUsername').value.trim();
  const email = document.getElementById('signupEmail').value.trim();
  const password = document.getElementById('signupPassword').value;

  try {
    const res = await authFetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    setAuthenticated(res.token, res.username);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove('hidden');
  }
});

document.getElementById('resetForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById('resetError');
  const successEl = document.getElementById('resetSuccess');
  errorEl.classList.add('hidden');
  successEl.classList.add('hidden');

  const email = document.getElementById('resetEmail').value.trim();
  const new_password = document.getElementById('resetNewPassword').value;

  try {
    const res = await authFetch('/api/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, new_password }),
    });
    successEl.textContent = 'Password reset. You are now logged in.';
    successEl.classList.remove('hidden');
    setTimeout(() => setAuthenticated(res.token, res.username), 600);
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove('hidden');
  }
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } catch (_) {
    // best-effort
  }
  showAuthScreen();
});

// Unauthenticated fetch helper for the auth endpoints themselves.
async function authFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { Accept: 'application/json', ...(options.headers || {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(body.detail || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return body;
}

// initAuth() runs at the very bottom of this file (not here) - it calls
// showAuthScreen()/resetLiveWorkflow(), which reference consts declared
// further down in this file (e.g. RISK_BADGE_CLASSES); calling it this
// early would hit those before their declarations run (temporal dead zone).

// ============================================================
// API helper (authenticated)
// ============================================================
async function apiFetch(path, options = {}) {
  const headers = { Accept: 'application/json', ...(options.headers || {}) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    showAuthScreen();
    throw new Error('Session expired. Please log in again.');
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors (422) return a list of {loc, msg, ...}.
        detail = body.detail.map((e) => e.msg || JSON.stringify(e)).join('; ');
      }
    } catch (_) {
      // ignore parse failure, use default detail
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ============================================================
// Tab navigation
// ============================================================
const tabButtons = document.querySelectorAll('.tab-btn');
const panels = {
  upload: document.getElementById('panel-upload'),
  result: document.getElementById('panel-result'),
  jobs: document.getElementById('panel-jobs'),
  'job-detail': document.getElementById('panel-job-detail'),
};

function activateTab(tabName) {
  tabButtons.forEach((btn) => {
    const isActive = btn.dataset.tab === tabName;
    btn.classList.toggle('border-indigo-600', isActive);
    btn.classList.toggle('text-indigo-600', isActive);
    btn.classList.toggle('border-transparent', !isActive);
    btn.classList.toggle('text-slate-500', !isActive);
    btn.setAttribute('aria-selected', String(isActive));
  });

  Object.entries(panels).forEach(([name, el]) => {
    el.classList.toggle('tab-panel-hidden', name !== tabName);
  });

  if (tabName === 'jobs') fetchJobs();
  // The Result tab (Agent Analysis + Final Result, stacked) is rendered
  // once at submit time. If the decision was later made from the Job
  // Detail page (or any other tab/session), re-fetch on click so this tab
  // never shows a stale decision.
  if (tabName === 'result' && currentCaseId) refreshLiveResult();
}

async function refreshLiveResult() {
  try {
    const [agentsResp, caseData] = await Promise.all([
      apiFetch(`/api/cases/${currentCaseId}/agents`),
      apiFetch(`/api/cases/${currentCaseId}`),
    ]);
    renderAgentResults(agentsResp.agents, '');
    renderResult(caseData, '');
  } catch (_) {
    // Keep whatever was already rendered rather than clearing it on a
    // transient network error.
  }
}

tabButtons.forEach((btn) => {
  btn.addEventListener('click', () => activateTab(btn.dataset.tab));
});

document.getElementById('newRequestBtn').addEventListener('click', () => {
  resetLiveWorkflow();
  activateTab('upload');
});

document.getElementById('jobDetailBackBtn').addEventListener('click', () => activateTab('jobs'));

// ============================================================
// Upload tab: file handling
// ============================================================
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const fileListEl = document.getElementById('fileList');
const submitBtn = document.getElementById('submitBtn');
const changeTitleInput = document.getElementById('changeTitle');
const changeTypeSelect = document.getElementById('changeType');
const changeDescInput = document.getElementById('changeDesc');

let selectedFiles = [];
let currentCaseId = null;

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function updateSubmitEnabled() {
  const ready =
    changeTitleInput.value.trim().length > 0 &&
    changeTypeSelect.value.length > 0 &&
    changeDescInput.value.trim().length > 0;
  submitBtn.disabled = !ready;
}

function renderFileList() {
  fileListEl.innerHTML = '';
  selectedFiles.forEach((file, index) => {
    const li = document.createElement('li');

    const label = document.createElement('span');
    label.textContent = `${file.name} · ${formatSize(file.size)}`;

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.textContent = '×';
    removeBtn.setAttribute('aria-label', `Remove ${file.name}`);
    removeBtn.addEventListener('click', () => {
      selectedFiles.splice(index, 1);
      renderFileList();
    });

    li.appendChild(label);
    li.appendChild(removeBtn);
    fileListEl.appendChild(li);
  });

  updateSubmitEnabled();
}

function addFiles(fileArray) {
  selectedFiles = selectedFiles.concat(Array.from(fileArray));
  renderFileList();
}

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  addFiles(e.target.files);
  fileInput.value = '';
});

changeTitleInput.addEventListener('input', updateSubmitEnabled);
changeTypeSelect.addEventListener('change', updateSubmitEnabled);
changeDescInput.addEventListener('input', updateSubmitEnabled);

['dragenter', 'dragover'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
});

['dragleave', 'drop'].forEach((eventName) => {
  dropZone.addEventListener(eventName, (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
  });
});

dropZone.addEventListener('drop', (e) => {
  if (e.dataTransfer?.files?.length) {
    addFiles(e.dataTransfer.files);
  }
});

const submitError = document.getElementById('submitError');

function showSubmitError(message) {
  submitError.textContent = message;
  submitError.classList.toggle('hidden', !message);
}

// ============================================================
// Agent + Result rendering (shared by the live Agent/Result tabs
// and the read-only Job Detail page - `prefix` selects which DOM
// tree to render into: '' for the live tabs, 'detail-' for Job Detail)
// ============================================================
const AGENT_IDS = ['agent1', 'agent2', 'agent3'];
const AGENT_NAME_TO_ID = {
  agent1: 'agent1',
  agent2: 'agent2',
  agent3: 'agent3',
  master_agent: 'master-agent',
};

const STATUS_CLASSES = {
  queued: ['bg-slate-100', 'text-slate-500'],
  processing: ['bg-amber-100', 'text-amber-700'],
  done: ['bg-emerald-100', 'text-emerald-700'],
  skipped: ['bg-slate-100', 'text-slate-400'],
};

function setStatusPill(pillEl, status) {
  const classes = STATUS_CLASSES[status] || STATUS_CLASSES.queued;
  Object.values(STATUS_CLASSES).forEach((c) => pillEl.classList.remove(...c));
  pillEl.classList.add(...classes);
  pillEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

const RISK_BADGE_CLASSES = {
  Low: ['bg-emerald-100', 'text-emerald-700'],
  Medium: ['bg-amber-100', 'text-amber-700'],
  High: ['bg-red-100', 'text-red-700'],
};

const RECOMMENDATION_LABELS = {
  approve: 'Approve',
  approve_with_conditions: 'Approve with Conditions',
  reject: 'Reject',
};

const OUT_OF_SCOPE_BADGE_CLASSES = ['bg-slate-200', 'text-slate-600'];

const CONFIDENCE_BAR_CLASSES = {
  high: 'bg-emerald-500',
  medium: 'bg-amber-500',
  low: 'bg-red-500',
};

function hideBadge(el) {
  if (!el) return;
  el.classList.add('hidden');
  el.textContent = '';
}

function resetAgentPanel(prefix = '') {
  AGENT_IDS.forEach((id) => {
    setStatusPill(document.getElementById(`${prefix}${id}-status`), 'queued');
    document.getElementById(`${prefix}${id}-output`).textContent = '';
    hideBadge(document.getElementById(`${prefix}${id}-provider`));
    hideBadge(document.getElementById(`${prefix}${id}-rating`));
    hideBadge(document.getElementById(`${prefix}${id}-duration`));
    document.getElementById(`${prefix}${id}-confidence-block`).classList.add('hidden');
  });
  setStatusPill(document.getElementById(`${prefix}master-agent-status`), 'queued');
  hideBadge(document.getElementById(`${prefix}master-agent-provider`));
  hideBadge(document.getElementById(`${prefix}master-agent-duration`));
}

function renderProviderBadge(prefix, domId) {
  // Provider/model name (e.g. "groq1 · openai/gpt-oss-120b") is deliberately
  // not shown to end users - keep the element (and this function) around in
  // case that changes later, but always hide it for now.
  hideBadge(document.getElementById(`${prefix}${domId}-provider`));
}

function formatDuration(ms) {
  if (ms === null || ms === undefined) return null;
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function renderAgentDuration(prefix, domId, agent) {
  const el = document.getElementById(`${prefix}${domId}-duration`);
  if (!el) return;

  const text = formatDuration(agent.duration_ms);
  if (!text) {
    hideBadge(el);
    return;
  }
  el.textContent = text;
  el.classList.remove('hidden');
}

function renderAgentConfidence(prefix, domId, agent) {
  const block = document.getElementById(`${prefix}${domId}-confidence-block`);
  if (!block) return;

  const confidence = agent.assessment?.confidence;
  if (confidence === null || confidence === undefined) {
    block.classList.add('hidden');
    return;
  }

  const label = document.getElementById(`${prefix}${domId}-confidence-label`);
  const bar = document.getElementById(`${prefix}${domId}-confidence-bar`);
  const tier = confidence >= 80 ? 'high' : confidence >= 55 ? 'medium' : 'low';

  Object.values(CONFIDENCE_BAR_CLASSES).forEach((c) => bar.classList.remove(c));
  bar.classList.add(CONFIDENCE_BAR_CLASSES[tier]);
  bar.style.width = `${confidence}%`;
  label.textContent = `${confidence}%`;
  block.classList.remove('hidden');
}

function renderAgentRatingBadge(prefix, domId, agent) {
  const el = document.getElementById(`${prefix}${domId}-rating`);
  if (!el) return;

  const rating = agent.assessment?.risk_rating;
  if (!rating) {
    hideBadge(el);
    return;
  }

  const classes = RISK_BADGE_CLASSES[rating] || RISK_BADGE_CLASSES.Medium;
  Object.values(RISK_BADGE_CLASSES).forEach((c) => el.classList.remove(...c));
  el.classList.add(...classes);
  el.classList.remove('hidden');
  el.textContent = rating;
}

function renderAgentResults(agents, prefix = '') {
  agents.forEach((agent) => {
    const domId = AGENT_NAME_TO_ID[agent.agent];
    if (!domId) return;

    setStatusPill(document.getElementById(`${prefix}${domId}-status`), agent.status);

    const roleEl = document.getElementById(`${prefix}${domId}-role`);
    if (roleEl && agent.role) roleEl.textContent = agent.role;

    const outputEl = document.getElementById(`${prefix}${domId}-output`);
    if (outputEl) outputEl.textContent = agent.output;

    renderProviderBadge(prefix, domId);
    renderAgentRatingBadge(prefix, domId, agent);
    renderAgentDuration(prefix, domId, agent);
    renderAgentConfidence(prefix, domId, agent);
  });
}

function formatTimestamp(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString();
  } catch (_) {
    return iso;
  }
}

function applyDecisionState(prefix, decision, outOfScope, decidedBy, decidedAt) {
  const acceptBtn = document.getElementById(`${prefix}acceptBtn`);
  const rejectBtn = document.getElementById(`${prefix}rejectBtn`);
  const decisionRow = document.getElementById(`${prefix}resultDecisionRow`);
  const decisionNote = document.getElementById(`${prefix}resultDecisionNote`);

  if (outOfScope) {
    decisionRow.classList.add('hidden');
    decisionNote.textContent = 'No committee decision needed — this request was out of scope for the FCRM workbench.';
    decisionNote.classList.remove('hidden');
    return;
  }

  if (decision === 'pending') {
    acceptBtn.disabled = false;
    rejectBtn.disabled = false;
    decisionRow.classList.remove('hidden');
    decisionNote.classList.add('hidden');
  } else {
    decisionRow.classList.add('hidden');
    const verb = decision === 'approved' ? 'Approved' : 'Rejected';
    const who = decidedBy ? ` by ${decidedBy}` : '';
    const when = decidedAt ? ` on ${formatTimestamp(decidedAt)}` : '';
    decisionNote.textContent = `Decision recorded: ${verb}${who}${when}`;
    decisionNote.classList.remove('hidden');
  }
}

function renderConfidenceMeter(prefix, confidence, votes) {
  const block = document.getElementById(`${prefix}resultConfidenceBlock`);
  const label = document.getElementById(`${prefix}resultConfidenceLabel`);
  const bar = document.getElementById(`${prefix}resultConfidenceBar`);

  if (confidence === null || confidence === undefined) {
    block.classList.add('hidden');
    return;
  }

  const totalAgents = votes ? Object.values(votes).reduce((a, b) => a + b, 0) : 0;
  const agreeingAgents = totalAgents > 0 ? Math.round((confidence / 100) * totalAgents) : null;

  const tier = confidence >= 90 ? 'high' : confidence >= 60 ? 'medium' : 'low';
  Object.values(CONFIDENCE_BAR_CLASSES).forEach((c) => bar.classList.remove(c));
  bar.classList.add(CONFIDENCE_BAR_CLASSES[tier]);
  bar.style.width = `${confidence}%`;

  label.textContent =
    agreeingAgents !== null ? `${confidence}% (${agreeingAgents}/${totalAgents} agents agreed)` : `${confidence}%`;

  block.classList.remove('hidden');
}

function renderResult(caseData, prefix = '') {
  document.getElementById(`${prefix}resultTitle`).textContent = caseData.title;

  const badge = document.getElementById(`${prefix}resultBadge`);
  const summaryEl = document.getElementById(`${prefix}resultSummary`);
  const conditionsEl = document.getElementById(`${prefix}resultConditions`);
  const votesEl = document.getElementById(`${prefix}resultVotes`);
  const judgeNoteEl = document.getElementById(`${prefix}resultJudgeNote`);
  const confidenceBlock = document.getElementById(`${prefix}resultConfidenceBlock`);

  if (!caseData.result) {
    applyDecisionState(prefix, caseData.decision, false, caseData.decided_by, caseData.decided_at);
    badge.textContent = '—';
    summaryEl.textContent = 'Assessment not yet available.';
    conditionsEl.classList.add('hidden');
    votesEl.classList.add('hidden');
    judgeNoteEl.classList.add('hidden');
    confidenceBlock.classList.add('hidden');
    return;
  }

  const {
    risk_rating,
    summary,
    recommendation,
    conditions,
    votes,
    confidence,
    chosen_agent,
    judge_rationale,
    out_of_scope,
  } = caseData.result;

  applyDecisionState(prefix, caseData.decision, out_of_scope, caseData.decided_by, caseData.decided_at);

  if (out_of_scope) {
    Object.values(RISK_BADGE_CLASSES).forEach((c) => badge.classList.remove(...c));
    badge.classList.remove(...OUT_OF_SCOPE_BADGE_CLASSES);
    badge.classList.add(...OUT_OF_SCOPE_BADGE_CLASSES);
    badge.textContent = 'Out of Scope';
    summaryEl.textContent = summary;
    conditionsEl.classList.add('hidden');
    votesEl.classList.add('hidden');
    judgeNoteEl.classList.add('hidden');
    confidenceBlock.classList.add('hidden');
    return;
  }

  const classes = RISK_BADGE_CLASSES[risk_rating] || RISK_BADGE_CLASSES.Medium;
  Object.values(RISK_BADGE_CLASSES).forEach((c) => badge.classList.remove(...c));
  badge.classList.remove(...OUT_OF_SCOPE_BADGE_CLASSES);
  badge.classList.add(...classes);
  badge.textContent = `${risk_rating} Risk · ${RECOMMENDATION_LABELS[recommendation] || recommendation}`;

  summaryEl.textContent = summary;

  if (conditions && conditions.length > 0) {
    conditionsEl.innerHTML = '';
    conditions.forEach((c) => {
      const li = document.createElement('li');
      li.textContent = c;
      conditionsEl.appendChild(li);
    });
    conditionsEl.classList.remove('hidden');
  } else {
    conditionsEl.classList.add('hidden');
  }

  if (votes && Object.keys(votes).length > 0) {
    const parts = Object.entries(votes).map(([rating, count]) => `${rating}: ${count}`);
    votesEl.textContent = `Agent votes — ${parts.join(', ')}`;
    votesEl.classList.remove('hidden');
  } else {
    votesEl.classList.add('hidden');
  }

  renderConfidenceMeter(prefix, confidence, votes);

  if (judge_rationale) {
    judgeNoteEl.textContent = chosen_agent
      ? `Judge selected ${chosen_agent}'s assessment: ${judge_rationale}`
      : judge_rationale;
    judgeNoteEl.classList.remove('hidden');
  } else {
    judgeNoteEl.classList.add('hidden');
  }
}

async function postDecision(caseId, decision, prefix, onDone) {
  const acceptBtn = document.getElementById(`${prefix}acceptBtn`);
  const rejectBtn = document.getElementById(`${prefix}rejectBtn`);
  acceptBtn.disabled = true;
  rejectBtn.disabled = true;

  try {
    await apiFetch(`/api/cases/${caseId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    });
    const caseData = await apiFetch(`/api/cases/${caseId}`);
    renderResult(caseData, prefix);
    if (onDone) onDone(caseData);
  } catch (err) {
    acceptBtn.disabled = false;
    rejectBtn.disabled = false;
    alert(`Failed to record decision: ${err.message}`);
  }
}

document.getElementById('acceptBtn').addEventListener('click', () => postDecision(currentCaseId, 'approved', ''));
document.getElementById('rejectBtn').addEventListener('click', () => postDecision(currentCaseId, 'rejected', ''));

document
  .getElementById('detail-acceptBtn')
  .addEventListener('click', () => postDecision(detailCaseId, 'approved', 'detail-', () => fetchJobs()));
document
  .getElementById('detail-rejectBtn')
  .addEventListener('click', () => postDecision(detailCaseId, 'rejected', 'detail-', () => fetchJobs()));

// ============================================================
// Upload -> Result tab (Agent Analysis, then Final Result, stacked)
// ============================================================
const aiProcessingOverlay = document.getElementById('aiProcessingOverlay');

function showAiProcessing() {
  aiProcessingOverlay.classList.remove('hidden');
}

function hideAiProcessing() {
  aiProcessingOverlay.classList.add('hidden');
}

submitBtn.addEventListener('click', async () => {
  showSubmitError('');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting…';

  try {
    const formData = new FormData();
    formData.append('title', changeTitleInput.value);
    formData.append('change_type', changeTypeSelect.value);
    formData.append('description', changeDescInput.value);
    selectedFiles.forEach((file) => formData.append('files', file));

    const created = await apiFetch('/api/cases', { method: 'POST', body: formData });
    currentCaseId = created.case_id;

    // Clear the Intake form now that the case is created, so navigating back
    // to it mid-pipeline (or after) shows a blank slate, not the just-submitted
    // values - past submissions stay reachable via All Jobs instead.
    selectedFiles = [];
    changeTitleInput.value = '';
    changeTypeSelect.value = '';
    changeDescInput.value = '';
    renderFileList();

    resetAgentPanel();
    AGENT_IDS.forEach((id) => setStatusPill(document.getElementById(`${id}-status`), 'processing'));
    setStatusPill(document.getElementById('master-agent-status'), 'processing');
    activateTab('result');
    showAiProcessing();

    const runResult = await apiFetch(`/api/cases/${currentCaseId}/run`, { method: 'POST' });
    renderAgentResults(runResult.agents);

    const caseData = await apiFetch(`/api/cases/${currentCaseId}`);
    renderResult(caseData);
  } catch (err) {
    showSubmitError(`Submission failed: ${err.message}`);
    activateTab('upload');
  } finally {
    hideAiProcessing();
    updateSubmitEnabled();
    submitBtn.textContent = 'Submit for Assessment';
  }
});

// ============================================================
// All Jobs tab
// ============================================================
function renderJobsList(jobs) {
  const listEl = document.getElementById('jobsList');
  const emptyEl = document.getElementById('jobsEmpty');
  listEl.innerHTML = '';

  emptyEl.classList.toggle('hidden', jobs.length > 0);
  if (jobs.length === 0) return;

  jobs.forEach((job) => {
    const li = document.createElement('li');
    li.className = 'p-4 hover:bg-slate-50 cursor-pointer flex items-start justify-between gap-4';
    li.tabIndex = 0;

    const left = document.createElement('div');
    const titleEl = document.createElement('p');
    titleEl.className = 'text-sm font-medium text-slate-900';
    titleEl.textContent = job.title;
    const metaEl = document.createElement('p');
    metaEl.className = 'text-xs text-slate-500 mt-0.5';
    let metaText = `${job.change_type} · ${formatTimestamp(job.created_at)} · ${job.status}`;
    if (job.created_by) metaText += ` · submitted by ${job.created_by}`;
    metaEl.textContent = metaText;
    left.appendChild(titleEl);
    left.appendChild(metaEl);

    const right = document.createElement('div');
    right.className = 'flex items-center gap-2 flex-shrink-0';

    if (job.risk_rating) {
      const riskBadge = document.createElement('span');
      const classes = RISK_BADGE_CLASSES[job.risk_rating] || RISK_BADGE_CLASSES.Medium;
      riskBadge.className = `text-xs font-medium px-2 py-0.5 rounded-full ${classes.join(' ')}`;
      riskBadge.textContent = `${job.risk_rating} Risk`;
      right.appendChild(riskBadge);
    }

    const decisionBadge = document.createElement('span');
    decisionBadge.className = 'text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-600';
    decisionBadge.textContent =
      job.decision === 'pending'
        ? 'Pending'
        : `${job.decision.charAt(0).toUpperCase() + job.decision.slice(1)}${job.decided_by ? ` by ${job.decided_by}` : ''}`;
    right.appendChild(decisionBadge);

    const viewBtn = document.createElement('button');
    viewBtn.type = 'button';
    viewBtn.className = 'text-xs font-medium text-indigo-600 hover:text-indigo-700 whitespace-nowrap';
    viewBtn.textContent = 'Open ▸';
    viewBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openJobDetail(job.case_id);
    });
    right.appendChild(viewBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'text-xs font-medium text-red-500 hover:text-red-700 whitespace-nowrap';
    deleteBtn.textContent = 'Delete';
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteJob(job.case_id, job.title);
    });
    right.appendChild(deleteBtn);

    li.appendChild(left);
    li.appendChild(right);

    li.addEventListener('click', () => openJobDetail(job.case_id));
    li.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openJobDetail(job.case_id);
      }
    });

    listEl.appendChild(li);
  });
}

async function fetchJobs() {
  const loadingEl = document.getElementById('jobsLoading');
  const errorEl = document.getElementById('jobsError');
  errorEl.classList.add('hidden');
  loadingEl.classList.remove('hidden');

  try {
    const jobs = await apiFetch('/api/cases');
    renderJobsList(jobs);
  } catch (err) {
    errorEl.textContent = `Failed to load jobs: ${err.message}`;
    errorEl.classList.remove('hidden');
  } finally {
    loadingEl.classList.add('hidden');
  }
}

// ============================================================
// Job Detail page: request + agent processing + result, stacked
// in one page, opened from a row in All Jobs.
// ============================================================
let detailCaseId = null;

function renderJobDetailRequest(caseData) {
  document.getElementById('detail-req-title').textContent = caseData.title;
  document.getElementById('detail-req-type').textContent = caseData.change_type;
  document.getElementById('detail-req-submitted-by').textContent = caseData.created_by || '—';
  document.getElementById('detail-req-created-at').textContent = formatTimestamp(caseData.created_at) || '—';
  document.getElementById('detail-req-files').textContent =
    caseData.filenames && caseData.filenames.length > 0 ? caseData.filenames.join(', ') : 'None';
  document.getElementById('detail-req-desc').textContent = caseData.description || '(no description provided)';

  const statusEl = document.getElementById('detail-req-status');
  statusEl.textContent = caseData.status.charAt(0).toUpperCase() + caseData.status.slice(1);
}

async function openJobDetail(caseId) {
  detailCaseId = caseId;

  resetAgentPanel('detail-');

  try {
    const [agentsResp, caseData] = await Promise.all([
      apiFetch(`/api/cases/${caseId}/agents`),
      apiFetch(`/api/cases/${caseId}`),
    ]);
    renderJobDetailRequest(caseData);
    renderAgentResults(agentsResp.agents, 'detail-');
    renderResult(caseData, 'detail-');
    activateTab('job-detail');
  } catch (err) {
    const errorEl = document.getElementById('jobsError');
    errorEl.textContent = `Failed to open job: ${err.message}`;
    errorEl.classList.remove('hidden');
    activateTab('jobs');
  }
}

async function deleteJob(caseId, title) {
  if (!window.confirm(`Delete job "${title}"? This cannot be undone.`)) return;

  const errorEl = document.getElementById('jobsError');
  try {
    await apiFetch(`/api/cases/${caseId}`, { method: 'DELETE' });
    await fetchJobs();
  } catch (err) {
    errorEl.textContent = `Failed to delete job: ${err.message}`;
    errorEl.classList.remove('hidden');
  }
}

async function deleteAllJobs() {
  if (!window.confirm('Delete ALL jobs? This cannot be undone.')) return;

  const errorEl = document.getElementById('jobsError');
  try {
    await apiFetch('/api/cases', { method: 'DELETE' });
    await fetchJobs();
  } catch (err) {
    errorEl.textContent = `Failed to delete all jobs: ${err.message}`;
    errorEl.classList.remove('hidden');
  }
}

document.getElementById('jobsRefreshBtn').addEventListener('click', fetchJobs);
document.getElementById('jobsDeleteAllBtn').addEventListener('click', deleteAllJobs);

updateSubmitEnabled();

// ============================================================
// Reset the live Upload/Agent/Result tabs to a blank slate. Called on every
// fresh login/signup and on logout, so a new session never shows leftover
// state from a previous one - past submissions are only reachable via All
// Jobs, never carried over in the live tabs.
// ============================================================
function resetResultTab(prefix) {
  document.getElementById(`${prefix}resultTitle`).textContent = 'Awaiting assessment…';

  const badge = document.getElementById(`${prefix}resultBadge`);
  Object.values(RISK_BADGE_CLASSES).forEach((c) => badge.classList.remove(...c));
  badge.classList.remove(...OUT_OF_SCOPE_BADGE_CLASSES);
  badge.classList.add('bg-slate-100', 'text-slate-500');
  badge.textContent = '—';

  document.getElementById(`${prefix}resultSummary`).textContent =
    'Submit a change request from the Intake tab to generate an assessment.';
  document.getElementById(`${prefix}resultConditions`).classList.add('hidden');
  document.getElementById(`${prefix}resultVotes`).classList.add('hidden');
  document.getElementById(`${prefix}resultJudgeNote`).classList.add('hidden');
  document.getElementById(`${prefix}resultConfidenceBlock`).classList.add('hidden');

  const acceptBtn = document.getElementById(`${prefix}acceptBtn`);
  const rejectBtn = document.getElementById(`${prefix}rejectBtn`);
  acceptBtn.disabled = true;
  rejectBtn.disabled = true;
  document.getElementById(`${prefix}resultDecisionRow`).classList.remove('hidden');
  document.getElementById(`${prefix}resultDecisionNote`).classList.add('hidden');
}

function resetLiveWorkflow() {
  currentCaseId = null;
  selectedFiles = [];
  changeTitleInput.value = '';
  changeTypeSelect.value = '';
  changeDescInput.value = '';
  renderFileList();
  showSubmitError('');
  resetAgentPanel('');
  resetResultTab('');
}

(async function initAuth() {
  if (!authToken) {
    showAuthScreen();
    return;
  }
  try {
    const me = await apiFetch('/api/auth/me');
    currentUsername = me.username;
    localStorage.setItem('authUsername', currentUsername);
    resetLiveWorkflow();
    showApp();
  } catch (_) {
    showAuthScreen();
  }
})();
