/**
 * Aether - Home Concierge
 * Main application JavaScript
 */

// When served via HA ingress, window.AETHER_BASE is injected server-side.
// Fallback: derive the base from the current page URL (works when
// X-Ingress-Path is not forwarded — the browser URL already contains the
// ingress prefix, e.g. /api/hassio_ingress/TOKEN/).
const API_BASE = (window.AETHER_BASE != null && window.AETHER_BASE !== '')
    ? window.AETHER_BASE + '/api'
    : window.location.pathname.replace(/\/+$/, '') + '/api';

// Icon system - curated line icons (matching the bottom-nav style) that
// replace emoji as the storage format for room/category/checklist icons.
// Keys are stored as plain strings in the DB (e.g. room.icon = "sofa").
// renderIcon() falls back to printing the raw string for any value that
// isn't a known key, so rooms/checklists created before this change (with
// an emoji icon) keep rendering exactly as they did.
const ICON_SVGS = {
  // UI icons
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path></svg>',
  vacation: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="2"></rect><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="3" y1="13" x2="21" y2="13"></line></svg>',
  pause: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>',
  play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41L11 3.83A2 2 0 0 0 9.59 3.24L4 3a1 1 0 0 0-1 1l.24 5.59a2 2 0 0 0 .59 1.41l9.58 9.58a2 2 0 0 0 2.83 0l4.35-4.35a2 2 0 0 0 0-2.82z"></path><circle cx="7.5" cy="7.5" r="1"></circle></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>',
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>',
  chevronRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
  // Room icons
  door: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="1"></rect><circle cx="14" cy="12" r="1"></circle></svg>',
  walk: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="2"></circle><path d="M12 7v5l-3 8"></path><path d="M12 12l3 8"></path><path d="M9 11l6-1"></path></svg>',
  sofa: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12V7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v5"></path><path d="M2 12h20v5a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z"></path><line x1="4" y1="18" x2="4" y2="20"></line><line x1="20" y1="18" x2="20" y2="20"></line></svg>',
  dining: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v7c0 1.1.9 2 2 2s2-.9 2-2V2"></path><path d="M5 11v11"></path><path d="M19 2c-1.5 0-3 2-3 6s1.5 6 3 6 0-4 0-6-1.5-6 0-6z"></path><path d="M19 14v8"></path></svg>',
  bed: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 18v-6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v6"></path><path d="M2 18v2"></path><path d="M22 18v2"></path><path d="M4 10V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4"></path><line x1="2" y1="14" x2="22" y2="14"></line></svg>',
  shower: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4a4 4 0 0 1 8 0v2"></path><path d="M12 6h6a2 2 0 0 1 2 2v1"></path><line x1="3" y1="12" x2="21" y2="12"></line><line x1="7" y1="16" x2="7" y2="16.01"></line><line x1="12" y1="16" x2="12" y2="16.01"></line><line x1="17" y1="16" x2="17" y2="16.01"></line><line x1="9" y1="20" x2="9" y2="20.01"></line><line x1="15" y1="20" x2="15" y2="20.01"></line></svg>',
  toilet: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 3h8v6a4 4 0 0 1-4 4 4 4 0 0 1-4-4z"></path><path d="M6 13h12l-1.2 7.2a2 2 0 0 1-2 1.8H9.2a2 2 0 0 1-2-1.8z"></path></svg>',
  pan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="12" r="7"></circle><line x1="21" y1="12" x2="17" y2="12"></line></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8l-9-5-9 5 9 5 9-5z"></path><path d="M3 8v8l9 5 9-5V8"></path><line x1="12" y1="13" x2="12" y2="21"></line></svg>',
  leaf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 4 13c0-5 4-9 11-11 1 6-2 10-4 10s-3-2-3-4"></path><path d="M4 13c0 4 3 7 7 7"></path></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>',
  // Category icons
  vacuum: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3v6"></path><path d="M9 9a5 5 0 0 1 5 5v7H9"></path><circle cx="6" cy="21" r="1"></circle><path d="M9 21H5"></path></svg>',
  mop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="14"></line><path d="M6 14h12l1 6a1 1 0 0 1-1 2H6a1 1 0 0 1-1-2z"></path></svg>',
  dust: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="8" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="17" cy="9" r="1"></circle><path d="M4 16c3-2 6-2 8 0s5 2 8 0"></path><path d="M4 20c3-2 6-2 8 0s5 2 8 0"></path></svg>',
  declutter: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="9" width="12" height="12" rx="1"></rect><path d="M17 13l4-4-4-4"></path><line x1="21" y1="9" x2="9" y2="9"></line></svg>',
  clean: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4"></path><path d="M12 17v4"></path><path d="M3 12h4"></path><path d="M17 12h4"></path><path d="M5.6 5.6l2.8 2.8"></path><path d="M15.6 15.6l2.8 2.8"></path><path d="M18.4 5.6l-2.8 2.8"></path><path d="M8.4 15.6l-2.8 2.8"></path></svg>',
  wash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2s7 8 7 13a7 7 0 0 1-14 0c0-5 7-13 7-13z"></path></svg>',
  wipe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"></rect><path d="M8 12c1-1 2-1 3 0s2 1 3 0 2-1 3 0"></path></svg>',
  maintain: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.8 2.8-2-2z"></path></svg>',
  // Checklist icons
  clipboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="3" width="12" height="18" rx="2"></rect><rect x="9" y="1.5" width="6" height="3" rx="1"></rect><line x1="9" y1="11" x2="15" y2="11"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>',
  broom: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20l6-6"></path><path d="M9 15l7-7 3 3-7 7z"></path><path d="M16 8l3-3"></path><path d="M4 20l2-6"></path></svg>',
  party: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21l4-9 9-9"></path><path d="M12 3l2 2"></path><path d="M16 7l2 2"></path><path d="M8 15l2 2"></path><circle cx="18" cy="4" r="1"></circle><circle cx="20" cy="9" r="1"></circle><circle cx="15" cy="4" r="1"></circle></svg>',
  plane: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L2 9l7 3 3 7 10-17z"></path></svg>',
  moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path></svg>',
  sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><line x1="12" y1="2" x2="12" y2="4"></line><line x1="12" y1="20" x2="12" y2="22"></line><line x1="4.2" y1="4.2" x2="5.6" y2="5.6"></line><line x1="18.4" y1="18.4" x2="19.8" y2="19.8"></line><line x1="2" y1="12" x2="4" y2="12"></line><line x1="20" y1="12" x2="22" y2="12"></line><line x1="4.2" y1="19.8" x2="5.6" y2="18.4"></line><line x1="18.4" y1="5.6" x2="19.8" y2="4.2"></line></svg>',
  tree: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L6 10h3l-5 7h6v5h4v-5h6l-5-7h3z"></path></svg>',
  flower: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2.5"></circle><circle cx="12" cy="6" r="2.5"></circle><circle cx="12" cy="18" r="2.5"></circle><circle cx="6" cy="12" r="2.5"></circle><circle cx="18" cy="12" r="2.5"></circle><line x1="12" y1="18" x2="12" y2="22"></line></svg>',
};

const ROOM_ICON_KEYS = ['door', 'walk', 'sofa', 'dining', 'bed', 'shower', 'toilet', 'pan', 'box', 'leaf', 'home', 'tag'];
const CATEGORY_ICON_KEYS = ['vacuum', 'mop', 'dust', 'declutter', 'clean', 'wash', 'wipe', 'maintain', 'tag'];
const CHECKLIST_ICON_KEYS = ['clipboard', 'home', 'broom', 'sofa', 'shower', 'leaf', 'party', 'plane', 'moon', 'sun', 'tree', 'flower'];

// Renders a stored icon value. Known keys render as line-icon SVGs; any
// other value (e.g. an emoji saved before this system existed) is printed
// as-is so older data keeps displaying without a forced migration.
function renderIcon(key, extraClass = '') {
  if (key && ICON_SVGS[key]) {
    return `<span class="icon ${extraClass}">${ICON_SVGS[key]}</span>`;
  }
  return `<span class="icon icon-emoji ${extraClass}">${key || ''}</span>`;
}

// State
let currentView = 'home';
let currentRoomId = null;
let currentChecklistId = null;
let _editingChore = null; // Chore currently open in the edit form
let _currentChecklistChoreIds = new Set(); // IDs of chores in the open checklist
let _currentChecklist = null; // Checklist currently open in the detail view
let _currentRoom = null; // Room currently open in the detail view

// DOM Elements
const appContent = document.getElementById('app-content');
const navItems = document.querySelectorAll('.nav-item');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initModal();
  loadView('home');
});

// Modal Management
function initModal() {
  // Create modal overlay
  const modalOverlay = document.createElement('div');
  modalOverlay.id = 'modal-overlay';
  modalOverlay.className = 'modal-overlay';
  modalOverlay.innerHTML = `
    <div class="modal-sheet" id="modal-sheet">
      <div class="modal-handle"></div>
      <div id="modal-content"></div>
    </div>
  `;
  document.body.appendChild(modalOverlay);

  // Close on overlay click
  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) {
      hideModal();
    }
  });
}

function showModal(content) {
  const modalContent = document.getElementById('modal-content');
  modalContent.innerHTML = content;
  document.getElementById('modal-overlay').classList.add('visible');
}

function hideModal() {
  document.getElementById('modal-overlay').classList.remove('visible');
  pendingConfirmation = null;
}

function showDurationConfirmation(choreId, choreName, estimatedMinutes, onComplete) {
  let adjustedMinutes = estimatedMinutes;

  const content = `
    <div class="modal-title">How long did that take?</div>
    <div class="modal-subtitle">${choreName}</div>
    <div class="duration-input-group">
      <button class="duration-btn" onclick="adjustDuration(-5)">-</button>
      <div class="duration-value" id="duration-display">${estimatedMinutes} <span>min</span></div>
      <button class="duration-btn" onclick="adjustDuration(5)">+</button>
    </div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmDuration('${choreId}', true)">About right</button>
      <button class="modal-btn modal-btn-secondary" onclick="confirmDuration('${choreId}', false)">Use adjusted time</button>
      <button class="modal-btn modal-btn-tertiary" onclick="skipConfirmation()">Skip</button>
    </div>
  `;

  pendingConfirmation = {
    choreId,
    type: 'duration',
    estimatedMinutes,
    adjustedMinutes: estimatedMinutes,
    onComplete
  };
  showModal(content);
}

function adjustDuration(delta) {
  if (!pendingConfirmation) return;

  pendingConfirmation.adjustedMinutes = Math.max(1, pendingConfirmation.adjustedMinutes + delta);
  document.getElementById('duration-display').innerHTML =
    `${pendingConfirmation.adjustedMinutes} <span>min</span>`;
}

async function confirmDuration(choreId, wasAccurate) {
  if (!pendingConfirmation) return;

  try {
    // If they adjusted the time, update the chore estimate
    if (!wasAccurate && pendingConfirmation.adjustedMinutes !== pendingConfirmation.estimatedMinutes) {
      await api(`/chores/${choreId}`, {
        method: 'PUT',
        body: JSON.stringify({ estimated_minutes: pendingConfirmation.adjustedMinutes })
      });
    }

    // Record the duration feedback (already completed, just updating feedback)
    // The completion already happened, so we just close and continue

    const onComplete = pendingConfirmation.onComplete;
    hideModal();

    if (onComplete) onComplete();
  } catch (err) {
    console.error('Failed to update duration:', err);
    hideModal();
  }
}

function showIntervalConfirmation(choreId, choreName, currentInterval, suggestedInterval, context, onComplete) {
  const content = `
    <div class="modal-title">Adjust schedule?</div>
    <div class="modal-subtitle">You did "${choreName}" ${context}.</div>
    <div class="duration-input-group">
      <button class="duration-btn" onclick="adjustInterval(-1)">-</button>
      <div class="duration-value" id="interval-display">${suggestedInterval} <span>days</span></div>
      <button class="duration-btn" onclick="adjustInterval(1)">+</button>
    </div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmInterval('${choreId}')">Change to this</button>
      <button class="modal-btn modal-btn-tertiary" onclick="skipConfirmation()">Keep at ${currentInterval} days</button>
    </div>
  `;

  pendingConfirmation = {
    choreId,
    type: 'interval',
    suggestedInterval,
    onComplete
  };
  showModal(content);
}

function adjustInterval(delta) {
  if (!pendingConfirmation) return;

  pendingConfirmation.suggestedInterval = Math.max(1, pendingConfirmation.suggestedInterval + delta);
  document.getElementById('interval-display').innerHTML =
    `${pendingConfirmation.suggestedInterval} <span>days</span>`;
}

async function confirmInterval(choreId) {
  if (!pendingConfirmation) return;

  try {
    await api(`/chores/${choreId}`, {
      method: 'PUT',
      body: JSON.stringify({ interval_days: pendingConfirmation.suggestedInterval })
    });

    const onComplete = pendingConfirmation.onComplete;
    hideModal();

    if (onComplete) onComplete();
  } catch (err) {
    console.error('Failed to update interval:', err);
    hideModal();
  }
}

function skipConfirmation() {
  const onComplete = pendingConfirmation?.onComplete;
  hideModal();
  if (onComplete) onComplete();
}

// Expose modal functions globally
window.adjustDuration = adjustDuration;
window.confirmDuration = confirmDuration;
window.adjustInterval = adjustInterval;
window.confirmInterval = confirmInterval;
window.skipConfirmation = skipConfirmation;

// Navigation
function initNavigation() {
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const view = item.dataset.view;
      setActiveNav(view);
      loadView(view);
    });
  });

  // Handle back/forward
  window.addEventListener('popstate', (e) => {
    if (e.state) {
      loadView(e.state.view, e.state.id, false);
    }
  });
}

function setActiveNav(view) {
  navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.view === view);
  });
}

function loadView(view, id = null, pushState = true) {
  currentView = view;

  if (pushState) {
    history.pushState({ view, id }, '', `#${view}${id ? '/' + id : ''}`);
  }

  switch (view) {
    case 'home':
      loadHomeView();
      break;
    case 'rooms':
      if (id) {
        loadRoomDetail(id);
      } else {
        loadRoomsView();
      }
      break;
    case 'lists':
      if (id) {
        loadChecklistDetail(id);
      } else {
        loadListsView();
      }
      break;
    case 'settings':
      if (id === 'categories') {
        loadSettingsCategoriesView();
      } else if (id === 'chores') {
        loadSettingsChoresView();
      } else if (id === 'vacation-history') {
        loadSettingsVacationHistoryView();
      } else {
        loadSettingsView();
      }
      break;
  }
}

// API Helpers
async function api(endpoint, options = {}) {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `API error: ${response.status}`;
    try {
      const body = await response.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) {
      // Response wasn't JSON - keep the generic message
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

// Freshness helpers
function getFreshnessClass(percent) {
  if (percent >= 70) return 'fresh';
  if (percent >= 40) return 'aging';
  if (percent >= 0) return 'due-soon';
  return 'overdue';
}

function getProgressClass(percent) {
  if (percent >= 70) return 'progress-fresh';
  if (percent >= 40) return 'progress-aging';
  if (percent >= 0) return 'progress-due-soon';
  return 'progress-overdue';
}

function formatDueDate(daysUntilDue) {
  if (daysUntilDue < -1) return `${Math.abs(daysUntilDue)} days overdue`;
  if (daysUntilDue === -1) return '1 day overdue';
  if (daysUntilDue === 0) return 'due today';
  if (daysUntilDue === 1) return 'due tomorrow';
  return `due in ${daysUntilDue} days`;
}

// Home View
async function loadHomeView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const [briefing, vacationStatus] = await Promise.all([
      api('/dashboard/briefing'),
      api('/vacation'),
    ]);
    renderHomeView(briefing, vacationStatus);
  } catch (err) {
    appContent.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">${ICON_SVGS.warning}</div>
      <div class="empty-state-text">Could not load data</div>
    </div>`;
  }
}

function formatVacationDays(days) {
  if (days < 1) return 'less than a day';
  const whole = Math.floor(days);
  return whole === 1 ? '1 day' : `${whole} days`;
}

function renderVacationChip(status) {
  if (!status || !status.is_active) return '';
  return `<div class="vacation-chip">${ICON_SVGS.vacation} Vacation mode active</div>`;
}

function renderHomeView(briefing, vacationStatus) {
  const hasSuggested = briefing.suggested_chores.length > 0;
  const html = `
    <div class="greeting">
      <div class="greeting-text">${briefing.greeting}.</div>
      ${renderVacationChip(vacationStatus)}
    </div>

    ${hasSuggested ? `
      <div class="section-header">
        <span class="section-title">Suggested &middot; ${briefing.suggested_chores.length} &middot; ~${briefing.total_minutes} min</span>
      </div>

      <div id="chore-list">
        ${briefing.suggested_chores.map(chore => renderChoreCard(chore)).join('')}
      </div>
    ` : `
      <div class="empty-state">
        <div class="empty-state-icon">${ICON_SVGS.check}</div>
        <div class="empty-state-text">Your home is fresh</div>
      </div>
    `}

    <div class="section-header">
      <span class="section-title">I have time</span>
    </div>

    <div class="quick-time">
      <button class="quick-time-btn" onclick="loadQuickClean(15)">15 min</button>
      <button class="quick-time-btn" onclick="loadQuickClean(30)">30 min</button>
      <button class="quick-time-btn" onclick="loadQuickClean(60)">60 min</button>
    </div>
  `;

  appContent.innerHTML = html;
  initSwipeGestures();
}

function renderChoreCard(chore) {
  const statusClass = chore.is_overdue ? 'overdue' :
    chore.days_until_due <= 0 ? 'due-soon' :
    chore.days_until_due <= 3 ? 'aging' : 'fresh';

  return `
    <div class="card-swipe-container" data-chore-id="${chore.id}">
      <div class="card-swipe-bg">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      </div>
      <div class="card-content">
        <div class="chore-card">
          <div class="chore-info">
            <div class="chore-name">${chore.name}</div>
            <div class="chore-meta">
              <span>${chore.room_name || 'House-wide'}</span>
              <span>·</span>
              <span>${chore.estimated_minutes} min</span>
              <span>·</span>
              <span>${formatDueDate(chore.days_until_due)}</span>
            </div>
          </div>
          <div class="chore-card-actions">
            <button class="chore-edit-btn" onclick="openChoreEditor('${chore.id}'); event.stopPropagation();" ontouchstart="event.stopPropagation();" title="Edit chore">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
              </svg>
            </button>
            <div class="chore-status ${statusClass}"></div>
          </div>
        </div>
      </div>
    </div>
  `;
}

// Quick Clean
async function loadQuickClean(minutes) {
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const result = await api(`/dashboard/quick-clean?minutes=${minutes}`);
    renderQuickClean(result, minutes);
  } catch (err) {
    loadHomeView();
  }
}

function renderQuickClean(result, minutes) {
  const html = `
    <a href="#" class="back-btn" onclick="loadHomeView(); return false;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
      Back
    </a>

    <div class="greeting">
      <div class="greeting-text">${minutes} minutes.</div>
      <div class="greeting-sub">${result.impact_summary}</div>
    </div>

    ${result.chores.length > 0 ? `
      <div id="chore-list">
        ${(() => {
          const grouped = {};
          result.chores.forEach(chore => {
            const cat = chore.category || 'other';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(chore);
          });
          return Object.entries(grouped).map(([cat, chores]) => `
            ${chores.length > 1 ? `<div class="section-header"><span class="section-title">${cat}</span></div>` : ''}
            ${chores.map(c => renderChoreCard(c)).join('')}
          `).join('');
        })()}
      </div>

      <div class="caption mt-lg">
        Total: ~${result.total_minutes} minutes
      </div>
    ` : `
      <div class="empty-state">
        <div class="empty-state-icon">${ICON_SVGS.check}</div>
        <div class="empty-state-text">Nothing urgent right now</div>
      </div>
    `}
  `;

  appContent.innerHTML = html;
  initSwipeGestures();
}

// Rooms View
let _roomsEditMode = false;
let _roomsCache = [];

async function loadRoomsView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const rooms = await api('/rooms');
    _roomsCache = rooms;
    renderRoomsView(rooms);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load rooms</div>';
  }
}

function toggleRoomsEditMode() {
  _roomsEditMode = !_roomsEditMode;
  renderRoomsView(_roomsCache);
}

function renderRoomsView(rooms) {
  const html = `
    <div class="view-header">
      <div class="greeting-text">Rooms</div>
      <div style="display:flex;gap:var(--space-sm)">
        <button class="icon-btn ${_roomsEditMode ? 'active' : ''}" onclick="toggleRoomsEditMode()" title="Reorder rooms">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
          </svg>
        </button>
        <button class="icon-btn" onclick="showRoomForm(null)" title="Add room">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>
    </div>

    <div class="room-grid">
      ${rooms.map((room, i) => `
        <a href="#" class="room-card ${room.is_paused ? 'room-paused' : ''}"
           onclick="${_roomsEditMode ? 'return false;' : `loadRoomDetail('${room.id}'); return false;`}">
          ${room.is_paused ? `<div class="room-paused-badge">${ICON_SVGS.pause} Paused</div>` : ''}
          <div class="room-icon">${renderIcon(room.icon)}</div>
          <div class="room-name">${room.name}</div>
          <div class="room-progress">
            <div class="room-progress-bar ${getProgressClass(room.freshness_percent)}"
                 style="width: ${room.freshness_percent}%"></div>
          </div>
          <div class="room-percent">${room.freshness_percent}% fresh</div>
          ${_roomsEditMode ? `
            <div class="room-reorder-controls">
              <button class="icon-btn" ${i === 0 ? 'disabled' : ''} onclick="moveRoom('${room.id}', -1); event.preventDefault(); event.stopPropagation();">${ICON_SVGS.up}</button>
              <button class="icon-btn" ${i === rooms.length - 1 ? 'disabled' : ''} onclick="moveRoom('${room.id}', 1); event.preventDefault(); event.stopPropagation();">${ICON_SVGS.down}</button>
            </div>
          ` : ''}
        </a>
      `).join('')}
    </div>
  `;

  appContent.innerHTML = html;
}

async function moveRoom(roomId, direction) {
  const index = _roomsCache.findIndex(r => r.id === roomId);
  const swapWith = index + direction;
  if (index < 0 || swapWith < 0 || swapWith >= _roomsCache.length) return;

  const reordered = [..._roomsCache];
  [reordered[index], reordered[swapWith]] = [reordered[swapWith], reordered[index]];
  _roomsCache = reordered;
  renderRoomsView(_roomsCache);

  try {
    await api('/rooms/reorder', {
      method: 'POST',
      body: JSON.stringify(reordered.map(r => r.id)),
    });
  } catch (err) {
    console.error('Failed to reorder rooms:', err);
    loadRoomsView();
  }
}

// Room Detail
async function loadRoomDetail(roomId) {
  currentRoomId = roomId;
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const [room, chores] = await Promise.all([
      api(`/rooms/${roomId}`),
      api(`/rooms/${roomId}/chores`)
    ]);
    renderRoomDetail(room, chores);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load room</div>';
  }
}

function renderRoomDetail(room, chores) {
  _currentRoom = room;
  const overdue = chores.filter(c => c.is_overdue);
  const dueSoon = chores.filter(c => !c.is_overdue && c.days_until_due <= 3);
  const allGood = chores.filter(c => !c.is_overdue && c.days_until_due > 3);

  const html = `
    <div class="view-header">
      <a href="#" class="back-btn" onclick="loadRoomsView(); return false;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        ${room.name}
      </a>
      <div style="display:flex;gap:var(--space-sm)">
        <button class="icon-btn" onclick="${room.is_paused ? `showUnpauseRoomModal('${room.id}')` : `showPauseRoomModal('${room.id}', '${room.name.replace(/'/g, "\\'")}')`}" title="${room.is_paused ? 'Unpause room' : 'Pause room'}">
          ${room.is_paused ? ICON_SVGS.play : ICON_SVGS.pause}
        </button>
        <button class="icon-btn" onclick="showRoomForm(_currentRoom)" title="Edit room">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
          </svg>
        </button>
        <button class="icon-btn" onclick="openChoreCreator('${room.id}')" title="Add chore">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>
    </div>

    ${room.is_paused ? `<div class="room-paused-badge mb-lg">${ICON_SVGS.pause} Paused &mdash; chores are frozen</div>` : ''}

    <div class="room-progress" style="height: 8px; margin-bottom: var(--space-sm);">
      <div class="room-progress-bar ${getProgressClass(room.freshness_percent)}"
           style="width: ${room.freshness_percent}%"></div>
    </div>
    <div class="caption mb-lg">${room.freshness_percent}% fresh</div>

    ${overdue.length > 0 ? `
      <div class="section-header">
        <span class="section-title">Needs attention</span>
        <span class="section-link text-overdue">${overdue.length}</span>
      </div>
      <div id="chore-list-overdue">
        ${overdue.map(chore => renderChoreCard(chore)).join('')}
      </div>
    ` : ''}

    ${dueSoon.length > 0 ? `
      <div class="section-header">
        <span class="section-title">Coming up</span>
      </div>
      <div id="chore-list-soon">
        ${dueSoon.map(chore => renderChoreCard(chore)).join('')}
      </div>
    ` : ''}

    ${allGood.length > 0 ? `
      <div class="section-header">
        <span class="section-title">All good</span>
        <span class="section-link">${allGood.length}</span>
      </div>
      <div id="chore-list-good">
        ${allGood.map(chore => renderChoreCard(chore)).join('')}
      </div>
    ` : ''}

    ${chores.length === 0 ? `
      <div class="empty-state">
        <div class="empty-state-icon">${ICON_SVGS.check}</div>
        <div class="empty-state-text">No chores for this room</div>
      </div>
    ` : ''}
  `;

  appContent.innerHTML = html;
  initSwipeGestures();
}

// Room Management (Create / Edit / Delete / Pause)

let _selectedRoomIcon = 'home';

function showRoomForm(room) {
  const isEdit = !!room;
  _selectedRoomIcon = room ? room.icon : 'home';

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'room-form-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'room-form-sheet';

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">${isEdit ? 'Edit room' : 'New room'}</div>

    <div class="form-group">
      <label class="form-label">Icon</label>
      <div class="icon-picker">
        ${ROOM_ICON_KEYS.map(icon => `
          <button class="icon-picker-btn ${icon === _selectedRoomIcon ? 'selected' : ''}"
            data-icon="${icon}" onclick="selectRoomIcon('${icon}')">${renderIcon(icon)}</button>
        `).join('')}
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Name</label>
      <input type="text" id="room-form-name" class="form-input"
        value="${room ? room.name.replace(/"/g, '&quot;') : ''}"
        placeholder="e.g. Guest room"
        autocomplete="off" />
    </div>

    <div class="modal-buttons" style="margin-top: var(--space-lg);">
      <button class="modal-btn modal-btn-primary" onclick="submitRoomForm('${room ? room.id : ''}', ${isEdit})">
        ${isEdit ? 'Save changes' : 'Add room'}
      </button>
      ${isEdit ? `
        <button class="modal-btn modal-btn-secondary chore-delete-btn" onclick="confirmDeleteRoom()">
          Delete room
        </button>
      ` : ''}
      <button class="modal-btn modal-btn-tertiary" onclick="dismissRoomForm()">
        Cancel
      </button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissRoomForm);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
    if (!isEdit) {
      const nameInput = document.getElementById('room-form-name');
      if (nameInput) nameInput.focus();
    }
  });
}

function selectRoomIcon(icon) {
  _selectedRoomIcon = icon;
  const sheet = document.getElementById('room-form-sheet');
  if (!sheet) return;
  sheet.querySelectorAll('.icon-picker-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.icon === icon);
  });
}

async function submitRoomForm(roomId, isEdit) {
  const name = document.getElementById('room-form-name')?.value?.trim();

  if (!name) {
    const nameInput = document.getElementById('room-form-name');
    if (nameInput) { nameInput.focus(); nameInput.style.borderColor = 'var(--overdue)'; }
    return;
  }

  try {
    if (isEdit) {
      await api(`/rooms/${roomId}?${new URLSearchParams({ name, icon: _selectedRoomIcon })}`, { method: 'PUT' });
    } else {
      await api('/rooms', {
        method: 'POST',
        body: JSON.stringify({ name, icon: _selectedRoomIcon }),
      });
    }
    dismissRoomForm();
    loadRoomsView();
  } catch (err) {
    console.error('Failed to save room:', err);
  }
}

function confirmDeleteRoom() {
  if (!_currentRoom) return;
  const sheet = document.getElementById('room-form-sheet');
  if (!sheet) return;
  const name = _currentRoom.name.replace(/"/g, '&quot;');
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Delete room?</div>
    <div class="modal-subtitle">"${name}" will be removed. Its chores will become house-wide.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary chore-delete-btn" onclick="deleteRoomConfirmed()">
        Yes, delete
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissRoomForm()">
        Cancel
      </button>
    </div>
  `;
}

async function deleteRoomConfirmed() {
  if (!_currentRoom) return;
  const roomId = _currentRoom.id;
  try {
    await api(`/rooms/${roomId}`, { method: 'DELETE' });
    dismissRoomForm();
    loadRoomsView();
  } catch (err) {
    const sheet = document.getElementById('room-form-sheet');
    if (sheet) {
      sheet.innerHTML = `
        <div class="modal-handle"></div>
        <div class="modal-title">Couldn't delete room</div>
        <div class="modal-subtitle">${err.message}</div>
        <div class="modal-buttons">
          <button class="modal-btn modal-btn-tertiary" onclick="dismissRoomForm()">Close</button>
        </div>
      `;
    }
  }
}

function dismissRoomForm() {
  const overlay = document.getElementById('room-form-overlay');
  const sheet = document.getElementById('room-form-sheet');
  if (!overlay) return;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

function showPauseRoomModal(roomId, roomName) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'room-pause-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'room-pause-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Pause ${roomName}?</div>
    <div class="modal-subtitle">All chores in this room will stop counting down until you unpause it &mdash; useful while remodeling.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmPauseRoom('${roomId}')">Pause room</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissRoomPauseModal()">Cancel</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissRoomPauseModal);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

async function confirmPauseRoom(roomId) {
  dismissRoomPauseModal();
  try {
    await api(`/rooms/${roomId}/pause`, { method: 'POST' });
    loadRoomDetail(roomId);
  } catch (err) {
    console.error('Failed to pause room:', err);
  }
}

function showUnpauseRoomModal(roomId) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'room-pause-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'room-pause-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Unpause this room?</div>
    <div class="modal-subtitle">Its chores will resume counting down right where they left off.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmUnpauseRoom('${roomId}')">Unpause room</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissRoomPauseModal()">Not yet</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissRoomPauseModal);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

async function confirmUnpauseRoom(roomId) {
  dismissRoomPauseModal();
  try {
    await api(`/rooms/${roomId}/unpause`, { method: 'POST' });
    loadRoomDetail(roomId);
  } catch (err) {
    console.error('Failed to unpause room:', err);
  }
}

function dismissRoomPauseModal() {
  const overlay = document.getElementById('room-pause-modal-overlay');
  const sheet = document.getElementById('room-pause-modal-sheet');
  if (!overlay) return;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

// Lists View
async function loadListsView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const lists = await api('/checklists');
    renderListsView(lists);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load checklists</div>';
  }
}

function renderListsView(lists) {
  const html = `
    <div class="view-header">
      <div class="greeting-text">Checklists</div>
      <button class="icon-btn" onclick="showCreateChecklistForm()" title="New checklist">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>

    ${lists.length > 0 ? lists.map(list => {
      const statParts = [];
      if (list.overdue_count > 0) statParts.push(`${list.overdue_count} need attention`);
      if (list.remaining_minutes > 0) statParts.push(`~${list.remaining_minutes} min to complete`);
      return `
      <a href="#" class="card" style="display: block; margin-bottom: var(--space-md); text-decoration: none; color: inherit;"
         onclick="loadChecklistDetail('${list.id}'); return false;">
        <div class="title">${renderIcon(list.icon)} ${list.name}</div>
        ${list.description ? `<div class="caption mt-sm">${list.description}</div>` : ''}
        ${statParts.length > 0 ? `<div class="caption mt-sm" style="color:var(--text-tertiary)">${statParts.join(' · ')}</div>` : ''}
      </a>
    `}).join('') : `
      <div class="empty-state">
        <div class="empty-state-icon">${ICON_SVGS.clipboard}</div>
        <div class="empty-state-text">No checklists yet</div>
      </div>
    `}
  `;

  appContent.innerHTML = html;
}

// Checklist Detail
async function loadChecklistDetail(checklistId) {
  currentChecklistId = checklistId;
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const checklist = await api(`/checklists/${checklistId}`);
    renderChecklistDetail(checklist);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load checklist</div>';
  }
}

function renderChecklistDetail(checklist) {
  _currentChecklist = checklist;
  // Track which chores are already in this checklist (for the adder picker)
  _currentChecklistChoreIds = new Set(checklist.chores.map(c => c.id));

  const html = `
    <div class="view-header">
      <a href="#" class="back-btn" onclick="loadListsView(); return false;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        Checklists
      </a>
      <div style="display:flex;gap:var(--space-sm)">
        <button class="icon-btn" onclick="showEditChecklistForm(_currentChecklist)" title="Edit checklist">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </button>
        <button class="icon-btn" onclick="openChecklistChoreAdder()" title="Add chore">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
        <button class="icon-btn" onclick="deleteChecklist(_currentChecklist.id, _currentChecklist.name)" title="Delete checklist" style="color:var(--overdue)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
            <path d="M10 11v6"></path>
            <path d="M14 11v6"></path>
            <path d="M9 6V4h6v2"></path>
          </svg>
        </button>
      </div>
    </div>

    <div class="checklist-header">
      <div class="title">${renderIcon(checklist.icon)} ${checklist.name}</div>
      <div class="caption">${checklist.description}</div>
      <div class="checklist-meta">
        <span>~${checklist.remaining_minutes} min to complete</span>
        <span>${checklist.overdue_count} need attention</span>
      </div>
    </div>

    <div id="checklist-items">
      ${checklist.chores.length === 0 ? `
        <div class="empty-state" style="padding: var(--space-xl) 0;">
          <div class="empty-state-icon">+</div>
          <div class="empty-state-text">Tap + to add chores</div>
        </div>
      ` : [...checklist.chores].sort((a, b) => a.days_until_due - b.days_until_due).map(chore => {
        const isDone = !chore.is_overdue && chore.days_until_due > 0;
        return `
          <div class="checklist-item ${isDone ? 'done' : ''}" data-chore-id="${chore.id}">
            <div class="checklist-check ${isDone ? 'done' : ''}" onclick="completeChore('${chore.id}')">
              ${isDone ? `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              ` : ''}
            </div>
            <div class="checklist-item-info">
              <div class="checklist-item-name">${chore.name}</div>
              <div class="checklist-item-meta">
                ${chore.room_name || 'House-wide'} · ${formatDueDate(chore.days_until_due)}
              </div>
            </div>
            <button class="checklist-remove-btn" onclick="removeChoreFromChecklist('${chore.id}')" title="Remove from list">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        `;
      }).join('')}
    </div>
  `;

  appContent.innerHTML = html;
}

// Swipe Gestures
function initSwipeGestures() {
  const cards = document.querySelectorAll('.card-swipe-container');

  cards.forEach(container => {
    const content = container.querySelector('.card-content');
    const bg = container.querySelector('.card-swipe-bg');
    let startX = 0;
    let currentX = 0;
    let isDragging = false;

    content.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      isDragging = true;
      content.classList.add('swiping');
    }, { passive: true });

    content.addEventListener('touchmove', (e) => {
      if (!isDragging) return;

      currentX = e.touches[0].clientX - startX;

      // Only allow right swipe
      if (currentX < 0) currentX = 0;
      if (currentX > 150) currentX = 150;

      content.style.transform = `translateX(${currentX}px)`;
      bg.classList.toggle('visible', currentX > 30);
    }, { passive: true });

    content.addEventListener('touchend', () => {
      isDragging = false;
      content.classList.remove('swiping');

      if (currentX > 80) {
        // Complete the chore
        const choreId = container.dataset.choreId;
        completeChoreWithAnimation(container, choreId);
      } else {
        // Snap back
        content.style.transform = 'translateX(0)';
        bg.classList.remove('visible');
      }

      currentX = 0;
    });
  });
}

// Complete Chore (non-swipe, e.g., from checklists)
async function completeChore(choreId) {
  try {
    const result = await api(`/chores/${choreId}/complete`, { method: 'POST' });

    // Refresh view function
    const refreshView = () => {
      if (currentView === 'home') {
        loadHomeView();
      } else if (currentView === 'rooms' && currentRoomId) {
        loadRoomDetail(currentRoomId);
      } else if (currentView === 'lists' && currentChecklistId) {
        loadChecklistDetail(currentChecklistId);
      }
    };

    // Check if we need to show confirmations
    if (result.ask_about_interval) {
      showIntervalConfirmation(
        choreId,
        result.chore.name,
        result.chore.interval_days,
        result.suggested_interval,
        result.interval_context,
        () => {
          if (result.ask_about_duration) {
            showDurationConfirmation(choreId, result.chore.name, result.chore.estimated_minutes, refreshView);
          } else {
            refreshView();
          }
        }
      );
    } else if (result.ask_about_duration) {
      showDurationConfirmation(choreId, result.chore.name, result.chore.estimated_minutes, refreshView);
    } else {
      refreshView();
    }
  } catch (err) {
    console.error('Failed to complete chore:', err);
  }
}

async function completeChoreWithAnimation(container, choreId) {
  const content = container.querySelector('.card-content');

  // Trigger haptic feedback if available
  if (navigator.vibrate) {
    navigator.vibrate(10);
  }

  // Add completion animation class
  container.classList.add('card-completing');

  try {
    const result = await api(`/chores/${choreId}/complete`, { method: 'POST' });

    // Show streak badge if applicable
    if (result.chore.streak > 1) {
      const badge = document.createElement('div');
      badge.className = 'streak-badge';
      badge.textContent = `${result.chore.streak}×`;
      content.appendChild(badge);

      setTimeout(() => badge.classList.add('visible'), 50);
    }

    // Remove card after animation
    setTimeout(() => {
      container.remove();

      // Define what to do after any confirmation flow
      const afterConfirmation = () => {
        // Check if list is now empty
        const choreList = document.getElementById('chore-list');
        if (choreList && choreList.children.length === 0) {
          // Refresh the view
          if (currentView === 'home') {
            loadHomeView();
          }
        }
      };

      // Check if we need to show interval confirmation first (takes priority)
      if (result.ask_about_interval) {
        showIntervalConfirmation(
          choreId,
          result.chore.name,
          result.chore.interval_days,
          result.suggested_interval,
          result.interval_context,
          () => {
            // After interval confirmation, check for duration
            if (result.ask_about_duration) {
              showDurationConfirmation(
                choreId,
                result.chore.name,
                result.chore.estimated_minutes,
                afterConfirmation
              );
            } else {
              afterConfirmation();
            }
          }
        );
      } else if (result.ask_about_duration) {
        // Only duration confirmation needed
        showDurationConfirmation(
          choreId,
          result.chore.name,
          result.chore.estimated_minutes,
          afterConfirmation
        );
      } else {
        afterConfirmation();
      }
    }, 400);

  } catch (err) {
    console.error('Failed to complete chore:', err);
    container.classList.remove('card-completing');
    content.style.transform = 'translateX(0)';
  }
}

// Duration Confirmation Modal
let _durationOnDone = null;
let _intervalOnDone = null;

function showDurationConfirmation(choreId, choreName, estimatedMinutes, onDone) {
  _durationOnDone = onDone || null;
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'duration-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'duration-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Was that about right?</div>
    <div class="modal-subtitle">${choreName} is estimated at ${estimatedMinutes} min.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmDuration('${choreId}', true)">
        Yes, that's accurate
      </button>
      <button class="modal-btn modal-btn-secondary" onclick="showDurationAdjust('${choreId}', ${estimatedMinutes})">
        No, it takes different time
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissDurationModal()">
        Skip
      </button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);

  // Dismiss on overlay tap
  overlay.addEventListener('click', dismissDurationModal);

  // Animate in
  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

function showDurationAdjust(choreId, estimatedMinutes) {
  const sheet = document.getElementById('duration-modal-sheet');
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">How long does it take?</div>
    <div class="modal-subtitle">Enter the actual time in minutes.</div>
    <div class="duration-input-group">
      <button class="duration-btn" onclick="stepDuration(-5)">−</button>
      <input
        type="number"
        id="duration-input"
        class="duration-input"
        value="${estimatedMinutes}"
        min="1"
        inputmode="numeric"
      />
      <button class="duration-btn" onclick="stepDuration(5)">+</button>
    </div>
    <div class="modal-buttons" style="margin-top: var(--space-lg)">
      <button class="modal-btn modal-btn-primary" onclick="submitDurationAdjust('${choreId}')">
        Save
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissDurationModal()">
        Cancel
      </button>
    </div>
  `;

  // Focus input after render
  requestAnimationFrame(() => {
    const input = document.getElementById('duration-input');
    if (input) {
      input.focus();
      input.select();
    }
  });
}

function stepDuration(delta) {
  const input = document.getElementById('duration-input');
  if (!input) return;
  const current = parseInt(input.value, 10) || 0;
  input.value = Math.max(1, current + delta);
}

async function submitDurationAdjust(choreId) {
  const input = document.getElementById('duration-input');
  const actualMinutes = input ? parseInt(input.value, 10) : null;
  if (!actualMinutes || actualMinutes < 1) return;
  await confirmDuration(choreId, false, actualMinutes);
}

async function confirmDuration(choreId, accurate, actualMinutes = null) {
  dismissDurationModal();
  try {
    const body = { accurate };
    if (actualMinutes) body.actual_minutes = actualMinutes;
    await api(`/chores/${choreId}/duration-feedback`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  } catch (err) {
    console.error('Failed to record duration feedback:', err);
  }
}

function dismissDurationModal() {
  const overlay = document.getElementById('duration-modal-overlay');
  const sheet = document.getElementById('duration-modal-sheet');
  if (!overlay) return;

  overlay.classList.remove('visible');
  sheet.classList.remove('visible');

  setTimeout(() => {
    overlay.remove();
    sheet.remove();
    if (_durationOnDone) {
      const cb = _durationOnDone;
      _durationOnDone = null;
      cb();
    }
  }, 300);
}

// Interval Confirmation Modal
function formatInterval(days) {
  if (days === 1) return 'every day';
  if (days === 7) return 'every week';
  if (days === 14) return 'every 2 weeks';
  if (days === 30) return 'every month';
  if (days % 7 === 0) return `every ${days / 7} weeks`;
  return `every ${days} days`;
}

function showIntervalConfirmation(choreId, choreName, intervalDays, suggestedDays, context, onDone) {
  _intervalOnDone = onDone || null;
  const prefill = suggestedDays || intervalDays;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'interval-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'interval-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Right schedule?</div>
    <div class="modal-subtitle">${choreName} is set to ${formatInterval(intervalDays)}.${context ? ` Done ${context}.` : ''}</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmInterval('${choreId}', true)">
        Yes, that's right
      </button>
      <button class="modal-btn modal-btn-secondary" onclick="showIntervalAdjust('${choreId}', ${prefill})">
        No, change the schedule
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissIntervalModal()">
        Skip
      </button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);

  overlay.addEventListener('click', dismissIntervalModal);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

function showIntervalAdjust(choreId, intervalDays) {
  const sheet = document.getElementById('interval-modal-sheet');
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">How often?</div>
    <div class="modal-subtitle">Enter the number of days between completions.</div>
    <div class="duration-input-group">
      <button class="duration-btn" onclick="stepInterval(-1)">−</button>
      <input
        type="number"
        id="interval-input"
        class="duration-input"
        value="${intervalDays}"
        min="1"
        inputmode="numeric"
      />
      <button class="duration-btn" onclick="stepInterval(1)">+</button>
    </div>
    <div class="modal-subtitle" id="interval-preview" style="margin-top: var(--space-sm); margin-bottom: 0; text-align: center;">
      ${formatInterval(intervalDays)}
    </div>
    <div class="modal-buttons" style="margin-top: var(--space-lg)">
      <button class="modal-btn modal-btn-primary" onclick="submitIntervalAdjust('${choreId}')">
        Save
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissIntervalModal()">
        Cancel
      </button>
    </div>
  `;

  const input = document.getElementById('interval-input');
  input.addEventListener('input', () => {
    const days = parseInt(input.value, 10);
    const preview = document.getElementById('interval-preview');
    if (preview && days > 0) preview.textContent = formatInterval(days);
  });

  requestAnimationFrame(() => {
    if (input) { input.focus(); input.select(); }
  });
}

function stepInterval(delta) {
  const input = document.getElementById('interval-input');
  if (!input) return;
  const current = parseInt(input.value, 10) || 0;
  input.value = Math.max(1, current + delta);
  input.dispatchEvent(new Event('input'));
}

async function submitIntervalAdjust(choreId) {
  const input = document.getElementById('interval-input');
  const actualDays = input ? parseInt(input.value, 10) : null;
  if (!actualDays || actualDays < 1) return;
  await confirmInterval(choreId, false, actualDays);
}

async function confirmInterval(choreId, accurate, actualDays = null) {
  dismissIntervalModal();
  try {
    const body = { accurate };
    if (actualDays) body.actual_days = actualDays;
    await api(`/chores/${choreId}/interval-feedback`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  } catch (err) {
    console.error('Failed to record interval feedback:', err);
  }
}

function dismissIntervalModal() {
  const overlay = document.getElementById('interval-modal-overlay');
  const sheet = document.getElementById('interval-modal-sheet');
  if (!overlay) return;

  overlay.classList.remove('visible');
  sheet.classList.remove('visible');

  setTimeout(() => {
    overlay.remove();
    sheet.remove();
    if (_intervalOnDone) {
      const cb = _intervalOnDone;
      _intervalOnDone = null;
      cb();
    }
  }, 300);
}

// Vacation Mode

async function showStartVacationModal() {
  let eligibility = [];
  try {
    eligibility = await api('/vacation/eligibility');
  } catch (err) {
    console.error('Failed to load vacation eligibility:', err);
  }
  const willPause = eligibility.filter(c => c.vacation_eligible).length;
  const wontPause = eligibility.length - willPause;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'vacation-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'vacation-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Start vacation mode?</div>
    <div class="modal-subtitle">
      ${willPause} chore${willPause === 1 ? '' : 's'} will pause while you're away${wontPause > 0 ? `, ${wontPause} won't (maintenance)` : ''}.
    </div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmStartVacation()">Start vacation</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissVacationModal()">Cancel</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissVacationModal);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

async function confirmStartVacation() {
  dismissVacationModal();
  try {
    await api('/vacation/start', { method: 'POST' });
    refreshCurrentView();
  } catch (err) {
    console.error('Failed to start vacation mode:', err);
  }
}

function showEndVacationModal() {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'vacation-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'vacation-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Welcome back!</div>
    <div class="modal-subtitle">Ending vacation mode resumes paused chores right where they left off.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmEndVacation()">End vacation</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissVacationModal()">Not yet</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissVacationModal);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

async function confirmEndVacation() {
  try {
    const result = await api('/vacation/end', { method: 'POST' });
    const sheet = document.getElementById('vacation-modal-sheet');
    if (sheet) {
      sheet.innerHTML = `
        <div class="modal-handle"></div>
        <div class="modal-title">Welcome back!</div>
        <div class="modal-subtitle">${result.chores_affected} chore${result.chores_affected === 1 ? '' : 's'} shifted forward by ${formatVacationDays(result.days_elapsed)}.</div>
        <div class="modal-buttons">
          <button class="modal-btn modal-btn-primary" onclick="dismissVacationModal(); refreshCurrentView();">Done</button>
        </div>
      `;
    } else {
      refreshCurrentView();
    }
  } catch (err) {
    console.error('Failed to end vacation mode:', err);
    dismissVacationModal();
  }
}

function dismissVacationModal() {
  const overlay = document.getElementById('vacation-modal-overlay');
  const sheet = document.getElementById('vacation-modal-sheet');
  if (!overlay) return;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

// Settings

async function loadSettingsView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';
  try {
    const status = await api('/vacation');
    renderSettingsView(status);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load settings</div>';
  }
}

function renderSettingsView(status) {
  const html = `
    <div class="greeting">
      <div class="greeting-text">Settings</div>
    </div>

    <div class="section-header">
      <span class="section-title">Vacation mode</span>
    </div>
    <div class="settings-panel">
      <div class="settings-panel-status">
        ${status.is_active
          ? `${ICON_SVGS.vacation} Active &mdash; ${formatVacationDays(status.days_elapsed)} paused`
          : `${ICON_SVGS.vacation} Not active`}
      </div>
      <div class="modal-buttons" style="margin-top: var(--space-md);">
        ${status.is_active
          ? `<button class="modal-btn modal-btn-secondary" onclick="showEndVacationModal()">End vacation</button>`
          : `<button class="modal-btn modal-btn-secondary" onclick="showStartVacationModal()">Start vacation</button>`}
      </div>
    </div>
    <a href="#" class="settings-row" onclick="loadView('settings', 'vacation-history'); return false;">
      <span>Vacation history</span>
      ${ICON_SVGS.chevronRight}
    </a>

    <div class="section-header" style="margin-top: var(--space-lg);">
      <span class="section-title">Manage</span>
    </div>
    <a href="#" class="settings-row" onclick="loadView('settings', 'categories'); return false;">
      <span>Categories</span>
      ${ICON_SVGS.chevronRight}
    </a>
    <a href="#" class="settings-row" onclick="loadView('settings', 'chores'); return false;">
      <span>All chores</span>
      ${ICON_SVGS.chevronRight}
    </a>
  `;

  appContent.innerHTML = html;
}

async function loadSettingsVacationHistoryView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';
  try {
    const entries = await api('/vacation/history');
    renderSettingsVacationHistoryView(entries);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load vacation history</div>';
  }
}

function formatVacationDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function renderSettingsVacationHistoryView(entries) {
  const html = `
    <div class="view-header">
      <a href="#" class="back-btn" onclick="loadView('settings'); return false;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        Vacation history
      </a>
    </div>

    ${entries.length === 0 ? `
      <div class="empty-state">
        <div class="empty-state-icon">${ICON_SVGS.vacation}</div>
        <div class="empty-state-text">No vacations logged yet</div>
      </div>
    ` : entries.map(e => `
      <div class="settings-panel" style="margin-bottom: var(--space-sm);">
        <div class="settings-panel-status">
          ${formatVacationDate(e.started_at)} &ndash; ${formatVacationDate(e.ended_at)}
        </div>
        <div class="caption mt-sm">${formatVacationDays(e.days_elapsed)} &middot; ${e.chores_affected} chore${e.chores_affected === 1 ? '' : 's'} paused</div>
      </div>
    `).join('')}
  `;

  appContent.innerHTML = html;
}

// Category Management

let _selectedCategoryIcon = 'tag';
let _categoriesCache = [];
let _currentCategory = null;

async function loadSettingsCategoriesView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';
  try {
    const categories = await api('/categories');
    _categoriesCache = categories;
    renderSettingsCategoriesView(categories);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load categories</div>';
  }
}

function renderSettingsCategoriesView(categories) {
  const html = `
    <div class="view-header">
      <a href="#" class="back-btn" onclick="loadView('settings'); return false;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        Categories
      </a>
      <button class="icon-btn" onclick="showCategoryForm(null)" title="Add category">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>
    <div class="caption mb-lg">Whether a category pauses by default during vacation mode.</div>

    ${categories.map((cat, i) => `
      <div class="category-row">
        <span class="category-row-icon">${renderIcon(cat.icon)}</span>
        <span class="category-row-name">${cat.name}</span>
        <label class="switch" title="Pauses by default on vacation">
          <input type="checkbox" ${cat.is_vacation_pausable_default ? 'checked' : ''}
            onchange="toggleCategoryPausable('${cat.id}', this.checked)">
          <span class="switch-track"></span>
        </label>
        <div class="category-row-reorder">
          <button class="icon-btn" ${i === 0 ? 'disabled' : ''} onclick="moveCategory('${cat.id}', -1)">${ICON_SVGS.up}</button>
          <button class="icon-btn" ${i === categories.length - 1 ? 'disabled' : ''} onclick="moveCategory('${cat.id}', 1)">${ICON_SVGS.down}</button>
        </div>
        <button class="icon-btn" onclick='showCategoryForm(${JSON.stringify(cat)})' title="Edit category">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
          </svg>
        </button>
      </div>
    `).join('')}
  `;

  appContent.innerHTML = html;
}

async function toggleCategoryPausable(categoryId, checked) {
  try {
    await api(`/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify({ is_vacation_pausable_default: checked }),
    });
    const cat = _categoriesCache.find(c => c.id === categoryId);
    if (cat) cat.is_vacation_pausable_default = checked;
  } catch (err) {
    console.error('Failed to update category:', err);
    loadSettingsCategoriesView();
  }
}

async function moveCategory(categoryId, direction) {
  const index = _categoriesCache.findIndex(c => c.id === categoryId);
  const swapWith = index + direction;
  if (index < 0 || swapWith < 0 || swapWith >= _categoriesCache.length) return;

  const reordered = [..._categoriesCache];
  [reordered[index], reordered[swapWith]] = [reordered[swapWith], reordered[index]];
  _categoriesCache = reordered;
  renderSettingsCategoriesView(_categoriesCache);

  try {
    await api('/categories/reorder', {
      method: 'POST',
      body: JSON.stringify(reordered.map(c => c.id)),
    });
  } catch (err) {
    console.error('Failed to reorder categories:', err);
    loadSettingsCategoriesView();
  }
}

function showCategoryForm(category) {
  const isEdit = !!category;
  _currentCategory = category || null;
  _selectedCategoryIcon = category ? category.icon : 'tag';

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'category-form-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'category-form-sheet';

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">${isEdit ? 'Edit category' : 'New category'}</div>

    <div class="form-group">
      <label class="form-label">Icon</label>
      <div class="icon-picker">
        ${CATEGORY_ICON_KEYS.map(icon => `
          <button class="icon-picker-btn ${icon === _selectedCategoryIcon ? 'selected' : ''}"
            data-icon="${icon}" onclick="selectCategoryIcon('${icon}')">${renderIcon(icon)}</button>
        `).join('')}
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Name</label>
      <input type="text" id="category-form-name" class="form-input"
        value="${category ? category.name.replace(/"/g, '&quot;') : ''}"
        placeholder="e.g. Polish"
        autocomplete="off" />
    </div>

    <div class="form-group">
      <label class="form-label" style="display:flex;align-items:center;justify-content:space-between;">
        Pauses by default on vacation
        <label class="switch">
          <input type="checkbox" id="category-form-pausable" ${!category || category.is_vacation_pausable_default ? 'checked' : ''}>
          <span class="switch-track"></span>
        </label>
      </label>
    </div>

    <div class="modal-buttons" style="margin-top: var(--space-lg);">
      <button class="modal-btn modal-btn-primary" onclick="submitCategoryForm('${category ? category.id : ''}', ${isEdit})">
        ${isEdit ? 'Save changes' : 'Add category'}
      </button>
      ${isEdit ? `
        <button class="modal-btn modal-btn-secondary chore-delete-btn" onclick="confirmDeleteCategory()">
          Delete category
        </button>
      ` : ''}
      <button class="modal-btn modal-btn-tertiary" onclick="dismissCategoryForm()">
        Cancel
      </button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissCategoryForm);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
    if (!isEdit) {
      const nameInput = document.getElementById('category-form-name');
      if (nameInput) nameInput.focus();
    }
  });
}

function selectCategoryIcon(icon) {
  _selectedCategoryIcon = icon;
  const sheet = document.getElementById('category-form-sheet');
  if (!sheet) return;
  sheet.querySelectorAll('.icon-picker-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.icon === icon);
  });
}

async function submitCategoryForm(categoryId, isEdit) {
  const name = document.getElementById('category-form-name')?.value?.trim();
  const pausable = document.getElementById('category-form-pausable')?.checked ?? true;

  if (!name) {
    const nameInput = document.getElementById('category-form-name');
    if (nameInput) { nameInput.focus(); nameInput.style.borderColor = 'var(--overdue)'; }
    return;
  }

  const body = { name, icon: _selectedCategoryIcon, is_vacation_pausable_default: pausable };

  try {
    if (isEdit) {
      await api(`/categories/${categoryId}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await api('/categories', { method: 'POST', body: JSON.stringify(body) });
    }
    dismissCategoryForm();
    loadSettingsCategoriesView();
  } catch (err) {
    console.error('Failed to save category:', err);
  }
}

function confirmDeleteCategory() {
  if (!_currentCategory) return;
  const sheet = document.getElementById('category-form-sheet');
  if (!sheet) return;
  const name = _currentCategory.name.replace(/"/g, '&quot;');
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Delete category?</div>
    <div class="modal-subtitle">"${name}" will be removed permanently.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary chore-delete-btn" onclick="deleteCategoryConfirmed()">
        Yes, delete
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissCategoryForm()">
        Cancel
      </button>
    </div>
  `;
}

async function deleteCategoryConfirmed() {
  if (!_currentCategory) return;
  const categoryId = _currentCategory.id;
  try {
    await api(`/categories/${categoryId}`, { method: 'DELETE' });
    dismissCategoryForm();
    loadSettingsCategoriesView();
  } catch (err) {
    const sheet = document.getElementById('category-form-sheet');
    if (sheet) {
      sheet.innerHTML = `
        <div class="modal-handle"></div>
        <div class="modal-title">Couldn't delete category</div>
        <div class="modal-subtitle">${err.message}</div>
        <div class="modal-buttons">
          <button class="modal-btn modal-btn-tertiary" onclick="dismissCategoryForm()">Close</button>
        </div>
      `;
    }
  }
}

function dismissCategoryForm() {
  const overlay = document.getElementById('category-form-overlay');
  const sheet = document.getElementById('category-form-sheet');
  if (!overlay) return;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

// Chores Browser

let _settingsChoresFilters = { room_id: '', category_id: '' };

async function loadSettingsChoresView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';
  try {
    const params = new URLSearchParams({ active_only: 'true' });
    if (_settingsChoresFilters.room_id) params.set('room_id', _settingsChoresFilters.room_id);
    if (_settingsChoresFilters.category_id) params.set('category_id', _settingsChoresFilters.category_id);

    const [chores, rooms, categories] = await Promise.all([
      api(`/chores?${params}`),
      api('/rooms'),
      api('/categories'),
    ]);
    renderSettingsChoresView(chores, rooms, categories);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load chores</div>';
  }
}

function onSettingsChoresFilterChange() {
  _settingsChoresFilters.room_id = document.getElementById('chores-filter-room')?.value || '';
  _settingsChoresFilters.category_id = document.getElementById('chores-filter-category')?.value || '';
  loadSettingsChoresView();
}

function renderSettingsChoresView(chores, rooms, categories) {
  const groupByRoom = !_settingsChoresFilters.room_id;

  let listHtml;
  if (chores.length === 0) {
    listHtml = `
      <div class="empty-state">
        <div class="empty-state-icon">${ICON_SVGS.check}</div>
        <div class="empty-state-text">No chores match these filters</div>
      </div>
    `;
  } else if (groupByRoom) {
    const groups = {};
    chores.forEach(c => {
      const roomName = c.room ? c.room.name : 'House-wide';
      if (!groups[roomName]) groups[roomName] = [];
      groups[roomName].push(c);
    });
    listHtml = Object.entries(groups).map(([roomName, roomChores]) => `
      <div class="chore-picker-room">${roomName}</div>
      ${roomChores.map(c => renderSettingsChoreRow(c)).join('')}
    `).join('');
  } else {
    listHtml = chores.map(c => renderSettingsChoreRow(c)).join('');
  }

  const roomOptions = rooms.map(r => `<option value="${r.id}" ${_settingsChoresFilters.room_id === r.id ? 'selected' : ''}>${r.name}</option>`).join('');
  const categoryOptions = categories.map(c => `<option value="${c.id}" ${_settingsChoresFilters.category_id === c.id ? 'selected' : ''}>${c.name}</option>`).join('');

  const html = `
    <div class="view-header">
      <a href="#" class="back-btn" onclick="loadView('settings'); return false;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        All chores
      </a>
      <button class="icon-btn" onclick="openChoreCreator()" title="Add chore">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>

    <div class="chores-filter-bar">
      <select id="chores-filter-room" class="form-select" onchange="onSettingsChoresFilterChange()">
        <option value="">All rooms</option>
        <option value="" disabled>&mdash;</option>
        ${roomOptions}
      </select>
      <select id="chores-filter-category" class="form-select" onchange="onSettingsChoresFilterChange()">
        <option value="">All categories</option>
        ${categoryOptions}
      </select>
    </div>

    <div id="settings-chore-list">
      ${listHtml}
    </div>
  `;

  appContent.innerHTML = html;
}

function renderSettingsChoreRow(chore) {
  return `
    <button class="chore-picker-item" onclick="openChoreEditor('${chore.id}')">
      <span class="chore-picker-name">${chore.name}</span>
      <span class="chore-picker-meta">${chore.category_name || ''} &middot; ${chore.estimated_minutes} min &middot; every ${chore.interval_days}d</span>
    </button>
  `;
}

// Checklist Management

async function removeChoreFromChecklist(choreId) {
  try {
    await api(`/checklists/${currentChecklistId}/chores/${choreId}`, { method: 'DELETE' });
    loadChecklistDetail(currentChecklistId);
  } catch (err) {
    console.error('Failed to remove chore from checklist:', err);
  }
}

let _pendingChecklistAdds = new Set();

async function openChecklistChoreAdder() {
  _pendingChecklistAdds = new Set();
  try {
    const allChores = await api('/chores');
    // Filter to chores not already in the checklist
    const available = allChores.filter(c => !_currentChecklistChoreIds.has(c.id));
    showChecklistChoreAdder(available);
  } catch (err) {
    console.error('Failed to load chores:', err);
  }
}

function showChecklistChoreAdder(chores) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'checklist-adder-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'checklist-adder-sheet';

  // Group by room
  const groups = {};
  chores.forEach(c => {
    const roomName = c.room ? c.room.name : 'House-wide';
    if (!groups[roomName]) groups[roomName] = [];
    groups[roomName].push(c);
  });

  const groupsHtml = Object.entries(groups).map(([roomName, roomChores]) => `
    <div class="chore-picker-room">${roomName}</div>
    ${roomChores.map(c => `
      <label class="chore-picker-item chore-picker-item-selectable">
        <input type="checkbox" class="chore-picker-checkbox" onchange="toggleChecklistChoreSelection('${c.id}')">
        <span class="chore-picker-info">
          <span class="chore-picker-name">${c.name}</span>
          <span class="chore-picker-meta">${c.estimated_minutes} min · every ${c.interval_days}d</span>
        </span>
      </label>
    `).join('')}
  `).join('');

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Add chores</div>
    ${chores.length === 0 ? `
      <div class="modal-subtitle">All chores are already in this list.</div>
    ` : groupsHtml}
    <div class="modal-buttons" style="margin-top: var(--space-lg);">
      <button class="modal-btn modal-btn-primary" id="checklist-adder-confirm-btn" disabled onclick="confirmChecklistChoreAdd()">Add 0</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissChecklistAdder()">Cancel</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissChecklistAdder);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
  });
}

function toggleChecklistChoreSelection(choreId) {
  if (_pendingChecklistAdds.has(choreId)) {
    _pendingChecklistAdds.delete(choreId);
  } else {
    _pendingChecklistAdds.add(choreId);
  }
  const btn = document.getElementById('checklist-adder-confirm-btn');
  if (btn) {
    const count = _pendingChecklistAdds.size;
    btn.textContent = `Add ${count}`;
    btn.disabled = count === 0;
  }
}

async function confirmChecklistChoreAdd() {
  const choreIds = Array.from(_pendingChecklistAdds);
  if (choreIds.length === 0) return;
  dismissChecklistAdder();
  try {
    await api(`/checklists/${currentChecklistId}/chores/bulk`, {
      method: 'POST',
      body: JSON.stringify({ chore_ids: choreIds }),
    });
    loadChecklistDetail(currentChecklistId);
  } catch (err) {
    console.error('Failed to add chores to checklist:', err);
  }
}

function dismissChecklistAdder() {
  const overlay = document.getElementById('checklist-adder-overlay');
  const sheet = document.getElementById('checklist-adder-sheet');
  if (!overlay) return;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

// Create Checklist

let _selectedChecklistIcon = 'clipboard';

function showCreateChecklistForm() {
  _selectedChecklistIcon = 'clipboard';

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'checklist-form-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'checklist-form-sheet';

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">New checklist</div>

    <div class="form-group">
      <label class="form-label">Icon</label>
      <div class="icon-picker">
        ${CHECKLIST_ICON_KEYS.map(icon => `
          <button class="icon-picker-btn ${icon === _selectedChecklistIcon ? 'selected' : ''}"
            data-icon="${icon}" onclick="selectChecklistIcon('${icon}')">${renderIcon(icon)}</button>
        `).join('')}
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Name</label>
      <input type="text" id="checklist-form-name" class="form-input"
        placeholder="e.g. Parents visiting"
        autocomplete="off" />
    </div>

    <div class="form-group">
      <label class="form-label">Description <span style="color:var(--text-tertiary);font-size:var(--font-size-caption);">(optional)</span></label>
      <input type="text" id="checklist-form-desc" class="form-input"
        placeholder="e.g. Get the house ready for guests"
        autocomplete="off" />
    </div>

    <div class="modal-buttons" style="margin-top: var(--space-lg);">
      <button class="modal-btn modal-btn-primary" onclick="submitCreateChecklist()">Create</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissChecklistForm()">Cancel</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissChecklistForm);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
    const nameInput = document.getElementById('checklist-form-name');
    if (nameInput) nameInput.focus();
  });
}

function selectChecklistIcon(icon) {
  _selectedChecklistIcon = icon;
  document.querySelectorAll('.icon-picker-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.icon === icon);
  });
}

async function submitCreateChecklist() {
  const name = document.getElementById('checklist-form-name')?.value?.trim();
  const description = document.getElementById('checklist-form-desc')?.value?.trim() || '';

  if (!name) {
    const nameInput = document.getElementById('checklist-form-name');
    if (nameInput) { nameInput.focus(); nameInput.style.borderColor = 'var(--overdue)'; }
    return;
  }

  try {
    const newList = await api('/checklists', {
      method: 'POST',
      body: JSON.stringify({ name, description, icon: _selectedChecklistIcon, chore_ids: [] }),
    });
    dismissChecklistForm();
    // Navigate straight into the new checklist so user can add chores
    currentChecklistId = newList.id;
    loadChecklistDetail(newList.id);
  } catch (err) {
    console.error('Failed to create checklist:', err);
  }
}

function dismissChecklistForm() {
  const overlay = document.getElementById('checklist-form-overlay');
  const sheet = document.getElementById('checklist-form-sheet');
  if (!overlay) return;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

// Edit Checklist

function showEditChecklistForm(checklist) {
  _selectedChecklistIcon = checklist.icon || 'clipboard';

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'checklist-form-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'checklist-form-sheet';

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Edit checklist</div>

    <div class="form-group">
      <label class="form-label">Icon</label>
      <div class="icon-picker">
        ${CHECKLIST_ICON_KEYS.map(icon => `
          <button class="icon-picker-btn ${icon === _selectedChecklistIcon ? 'selected' : ''}"
            data-icon="${icon}" onclick="selectChecklistIcon('${icon}')">${renderIcon(icon)}</button>
        `).join('')}
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">Name</label>
      <input type="text" id="checklist-form-name" class="form-input"
        value="${checklist.name.replace(/"/g, '&quot;')}"
        autocomplete="off" />
    </div>

    <div class="form-group">
      <label class="form-label">Description <span style="color:var(--text-tertiary);font-size:var(--font-size-caption);">(optional)</span></label>
      <input type="text" id="checklist-form-desc" class="form-input"
        value="${(checklist.description || '').replace(/"/g, '&quot;')}"
        autocomplete="off" />
    </div>

    <div class="modal-buttons" style="margin-top: var(--space-lg);">
      <button class="modal-btn modal-btn-primary" onclick="submitEditChecklist('${checklist.id}')">Save</button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissChecklistForm()">Cancel</button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissChecklistForm);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
    const nameInput = document.getElementById('checklist-form-name');
    if (nameInput) nameInput.focus();
  });
}

async function submitEditChecklist(checklistId) {
  const name = document.getElementById('checklist-form-name')?.value?.trim();
  const description = document.getElementById('checklist-form-desc')?.value?.trim() || '';

  if (!name) {
    const nameInput = document.getElementById('checklist-form-name');
    if (nameInput) { nameInput.focus(); nameInput.style.borderColor = 'var(--overdue)'; }
    return;
  }

  try {
    await api(`/checklists/${checklistId}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description, icon: _selectedChecklistIcon }),
    });
    dismissChecklistForm();
    loadChecklistDetail(checklistId);
  } catch (err) {
    console.error('Failed to update checklist:', err);
  }
}

async function deleteChecklist(checklistId, checklistName) {
  if (!confirm(`Delete "${checklistName}"? This cannot be undone.`)) return;

  try {
    await api(`/checklists/${checklistId}`, { method: 'DELETE' });
    loadListsView();
  } catch (err) {
    console.error('Failed to delete checklist:', err);
  }
}

// Chore Management (Create / Edit / Delete)

async function openChoreEditor(choreId) {
  try {
    const [chore, rooms, categories] = await Promise.all([
      api(`/chores/${choreId}`),
      api('/rooms'),
      api('/categories'),
    ]);
    showChoreForm(chore, rooms, categories);
  } catch (err) {
    console.error('Failed to load chore for editing:', err);
  }
}

async function openChoreCreator(roomId = null) {
  try {
    const [rooms, categories] = await Promise.all([
      api('/rooms'),
      api('/categories'),
    ]);
    showChoreForm(null, rooms, categories, roomId);
  } catch (err) {
    console.error('Failed to load rooms:', err);
  }
}

function showChoreForm(chore, rooms, categories, defaultRoomId = null) {
  const isEdit = !!chore;
  _editingChore = chore || null;
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'chore-form-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'chore-form-sheet';

  const selectedRoom = chore ? chore.room_id : defaultRoomId;
  const roomOptions = rooms.map(r =>
    `<option value="${r.id}" ${selectedRoom === r.id ? 'selected' : ''}>${r.name}</option>`
  ).join('');

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">${isEdit ? 'Edit chore' : 'New chore'}</div>

    <div class="form-group">
      <label class="form-label">Name</label>
      <input type="text" id="chore-form-name" class="form-input"
        value="${chore ? chore.name.replace(/"/g, '&quot;') : ''}"
        placeholder="e.g. Vacuum living room"
        autocomplete="off" />
    </div>

    <div class="form-group">
      <label class="form-label">Room</label>
      <select id="chore-form-room" class="form-select">
        <option value="" ${!selectedRoom ? 'selected' : ''}>House-wide</option>
        ${roomOptions}
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Category</label>
      <select id="chore-form-category" class="form-select">
        ${categories.map(c =>
          `<option value="${c.id}" ${(chore ? chore.category_id : categories[0]?.id) === c.id ? 'selected' : ''}>${c.name}</option>`
        ).join('')}
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Vacation pausing</label>
      <select id="chore-form-vacation-override" class="form-select">
        <option value="" ${!chore || !chore.vacation_override ? 'selected' : ''}>Use category default</option>
        <option value="force_pause" ${chore && chore.vacation_override === 'force_pause' ? 'selected' : ''}>Always pause</option>
        <option value="force_exclude" ${chore && chore.vacation_override === 'force_exclude' ? 'selected' : ''}>Never pause</option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">Repeat every</label>
      <div class="duration-input-group">
        <button class="duration-btn" onclick="stepFormValue('chore-form-interval', -1)">−</button>
        <input type="number" id="chore-form-interval" class="duration-input"
          value="${chore ? chore.interval_days : 7}" min="1" inputmode="numeric" />
        <button class="duration-btn" onclick="stepFormValue('chore-form-interval', 1)">+</button>
      </div>
      <div class="form-hint">days</div>
    </div>

    <div class="form-group">
      <label class="form-label">Takes about</label>
      <div class="duration-input-group">
        <button class="duration-btn" onclick="stepFormValue('chore-form-duration', -5)">−</button>
        <input type="number" id="chore-form-duration" class="duration-input"
          value="${chore ? chore.estimated_minutes : 15}" min="1" inputmode="numeric" />
        <button class="duration-btn" onclick="stepFormValue('chore-form-duration', 5)">+</button>
      </div>
      <div class="form-hint">minutes</div>
    </div>

    <div class="modal-buttons" style="margin-top: var(--space-lg);">
      <button class="modal-btn modal-btn-primary" onclick="submitChoreForm('${chore ? chore.id : ''}', ${isEdit})">
        ${isEdit ? 'Save changes' : 'Add chore'}
      </button>
      ${isEdit ? `
        <button class="modal-btn modal-btn-secondary chore-delete-btn" onclick="confirmDeleteChore()">
          Delete chore
        </button>
      ` : ''}
      <button class="modal-btn modal-btn-tertiary" onclick="dismissChoreForm()">
        Cancel
      </button>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(sheet);
  overlay.addEventListener('click', dismissChoreForm);

  requestAnimationFrame(() => {
    overlay.classList.add('visible');
    sheet.classList.add('visible');
    if (!isEdit) {
      const nameInput = document.getElementById('chore-form-name');
      if (nameInput) nameInput.focus();
    }
  });
}

function stepFormValue(inputId, delta) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const current = parseInt(input.value, 10) || 0;
  input.value = Math.max(1, current + delta);
}

async function submitChoreForm(choreId, isEdit) {
  const name = document.getElementById('chore-form-name')?.value?.trim();
  const roomId = document.getElementById('chore-form-room')?.value || null;
  const categoryId = document.getElementById('chore-form-category')?.value;
  const intervalDays = parseInt(document.getElementById('chore-form-interval')?.value, 10);
  const estimatedMinutes = parseInt(document.getElementById('chore-form-duration')?.value, 10);
  const vacationOverride = document.getElementById('chore-form-vacation-override')?.value || null;

  if (!name) {
    const nameInput = document.getElementById('chore-form-name');
    if (nameInput) { nameInput.focus(); nameInput.style.borderColor = 'var(--overdue)'; }
    return;
  }

  const body = {
    name,
    room_id: roomId || null,
    category_id: categoryId,
    interval_days: intervalDays,
    estimated_minutes: estimatedMinutes,
    vacation_override: vacationOverride,
  };

  try {
    if (isEdit) {
      await api(`/chores/${choreId}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await api('/chores', { method: 'POST', body: JSON.stringify(body) });
    }
    dismissChoreForm();
    refreshCurrentView();
  } catch (err) {
    console.error('Failed to save chore:', err);
  }
}

function confirmDeleteChore() {
  if (!_editingChore) return;
  const sheet = document.getElementById('chore-form-sheet');
  if (!sheet) return;
  const name = _editingChore.name.replace(/"/g, '&quot;');
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Delete chore?</div>
    <div class="modal-subtitle">"${name}" and its completion history will be removed permanently.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary chore-delete-btn" onclick="deleteChore()">
        Yes, delete
      </button>
      <button class="modal-btn modal-btn-tertiary" onclick="dismissChoreForm()">
        Cancel
      </button>
    </div>
  `;
}

async function deleteChore() {
  if (!_editingChore) return;
  const choreId = _editingChore.id;
  try {
    await api(`/chores/${choreId}`, { method: 'DELETE' });
    dismissChoreForm();
    refreshCurrentView();
  } catch (err) {
    console.error('Failed to delete chore:', err);
    dismissChoreForm();
  }
}

function dismissChoreForm() {
  const overlay = document.getElementById('chore-form-overlay');
  const sheet = document.getElementById('chore-form-sheet');
  if (!overlay) return;
  _editingChore = null;
  overlay.classList.remove('visible');
  sheet.classList.remove('visible');
  setTimeout(() => { overlay.remove(); sheet.remove(); }, 300);
}

function refreshCurrentView() {
  if (currentView === 'home') {
    loadHomeView();
  } else if (currentView === 'rooms') {
    if (currentRoomId) {
      loadRoomDetail(currentRoomId);
    } else {
      loadRoomsView();
    }
  } else if (currentView === 'lists' && currentChecklistId) {
    loadChecklistDetail(currentChecklistId);
  } else if (currentView === 'settings') {
    loadSettingsChoresView();
  }
}

// Expose functions globally
window.loadHomeView = loadHomeView;
window.loadRoomsView = loadRoomsView;
window.loadListsView = loadListsView;
window.loadRoomDetail = loadRoomDetail;
window.loadChecklistDetail = loadChecklistDetail;
window.loadQuickClean = loadQuickClean;
window.completeChore = completeChore;
window.confirmDuration = confirmDuration;
window.dismissDurationModal = dismissDurationModal;
window.showDurationAdjust = showDurationAdjust;
window.stepDuration = stepDuration;
window.submitDurationAdjust = submitDurationAdjust;
window.showIntervalConfirmation = showIntervalConfirmation;
window.showIntervalAdjust = showIntervalAdjust;
window.stepInterval = stepInterval;
window.submitIntervalAdjust = submitIntervalAdjust;
window.confirmInterval = confirmInterval;
window.dismissIntervalModal = dismissIntervalModal;
window.openChoreEditor = openChoreEditor;
window.openChoreCreator = openChoreCreator;
window.stepFormValue = stepFormValue;
window.submitChoreForm = submitChoreForm;
window.confirmDeleteChore = confirmDeleteChore;
window.deleteChore = deleteChore;
window.dismissChoreForm = dismissChoreForm;
window.removeChoreFromChecklist = removeChoreFromChecklist;
window.openChecklistChoreAdder = openChecklistChoreAdder;
window.toggleChecklistChoreSelection = toggleChecklistChoreSelection;
window.confirmChecklistChoreAdd = confirmChecklistChoreAdd;
window.dismissChecklistAdder = dismissChecklistAdder;
window.showCreateChecklistForm = showCreateChecklistForm;
window.selectChecklistIcon = selectChecklistIcon;
window.submitCreateChecklist = submitCreateChecklist;
window.dismissChecklistForm = dismissChecklistForm;
window.showEditChecklistForm = showEditChecklistForm;
window.submitEditChecklist = submitEditChecklist;
window.deleteChecklist = deleteChecklist;
window.showStartVacationModal = showStartVacationModal;
window.confirmStartVacation = confirmStartVacation;
window.showEndVacationModal = showEndVacationModal;
window.confirmEndVacation = confirmEndVacation;
window.dismissVacationModal = dismissVacationModal;
window.toggleRoomsEditMode = toggleRoomsEditMode;
window.moveRoom = moveRoom;
window.showRoomForm = showRoomForm;
window.selectRoomIcon = selectRoomIcon;
window.submitRoomForm = submitRoomForm;
window.confirmDeleteRoom = confirmDeleteRoom;
window.deleteRoomConfirmed = deleteRoomConfirmed;
window.dismissRoomForm = dismissRoomForm;
window.showPauseRoomModal = showPauseRoomModal;
window.confirmPauseRoom = confirmPauseRoom;
window.showUnpauseRoomModal = showUnpauseRoomModal;
window.confirmUnpauseRoom = confirmUnpauseRoom;
window.dismissRoomPauseModal = dismissRoomPauseModal;
window.loadView = loadView;
window.toggleCategoryPausable = toggleCategoryPausable;
window.moveCategory = moveCategory;
window.showCategoryForm = showCategoryForm;
window.selectCategoryIcon = selectCategoryIcon;
window.submitCategoryForm = submitCategoryForm;
window.confirmDeleteCategory = confirmDeleteCategory;
window.deleteCategoryConfirmed = deleteCategoryConfirmed;
window.dismissCategoryForm = dismissCategoryForm;
window.onSettingsChoresFilterChange = onSettingsChoresFilterChange;
