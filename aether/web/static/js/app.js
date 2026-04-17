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

// State
let currentView = 'home';
let currentRoomId = null;
let currentChecklistId = null;
let _editingChore = null; // Chore currently open in the edit form
let _currentChecklistChoreIds = new Set(); // IDs of chores in the open checklist

// DOM Elements
const appContent = document.getElementById('app-content');
const navItems = document.querySelectorAll('.nav-item');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  loadView('home');
});

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
    throw new Error(`API error: ${response.status}`);
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
    const briefing = await api('/dashboard/briefing');
    renderHomeView(briefing);
  } catch (err) {
    appContent.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">!</div>
      <div class="empty-state-text">Could not load data</div>
    </div>`;
  }
}

function renderHomeView(briefing) {
  const html = `
    <div class="greeting">
      <div class="greeting-text">${briefing.greeting}.</div>
      <div class="greeting-sub">
        ${briefing.suggested_chores.length > 0
          ? `${briefing.suggested_chores.length} things worth ~${briefing.total_minutes} minutes`
          : 'All caught up'}
      </div>
    </div>

    ${briefing.suggested_chores.length > 0 ? `
      <div class="section-header">
        <span class="section-title">Suggested</span>
      </div>

      <div id="chore-list">
        ${briefing.suggested_chores.map(chore => renderChoreCard(chore)).join('')}
      </div>
    ` : `
      <div class="empty-state">
        <div class="empty-state-icon">&#10003;</div>
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

    ${briefing.rooms_needing_attention.length > 0 ? `
      <div class="section-header">
        <span class="section-title">Rooms needing attention</span>
      </div>
      <div class="caption">
        ${briefing.rooms_needing_attention.join(', ')}
      </div>
    ` : ''}
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
        <div class="empty-state-icon">&#10003;</div>
        <div class="empty-state-text">Nothing urgent right now</div>
      </div>
    `}
  `;

  appContent.innerHTML = html;
  initSwipeGestures();
}

// Rooms View
async function loadRoomsView() {
  appContent.innerHTML = '<div class="loading">Loading...</div>';

  try {
    const rooms = await api('/rooms');
    renderRoomsView(rooms);
  } catch (err) {
    appContent.innerHTML = '<div class="empty-state">Could not load rooms</div>';
  }
}

function renderRoomsView(rooms) {
  const html = `
    <div class="greeting">
      <div class="greeting-text">Rooms</div>
    </div>

    <div class="room-grid">
      ${rooms.map(room => `
        <a href="#" class="room-card" onclick="loadRoomDetail('${room.id}'); return false;">
          <div class="room-icon">${room.icon}</div>
          <div class="room-name">${room.name}</div>
          <div class="room-progress">
            <div class="room-progress-bar ${getProgressClass(room.freshness_percent)}"
                 style="width: ${room.freshness_percent}%"></div>
          </div>
          <div class="room-percent">${room.freshness_percent}% fresh</div>
        </a>
      `).join('')}
    </div>
  `;

  appContent.innerHTML = html;
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
      <button class="icon-btn" onclick="openChoreCreator('${room.id}')" title="Add chore">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>

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
        <div class="empty-state-icon">&#10003;</div>
        <div class="empty-state-text">No chores for this room</div>
      </div>
    ` : ''}
  `;

  appContent.innerHTML = html;
  initSwipeGestures();
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

    ${lists.length > 0 ? lists.map(list => `
      <a href="#" class="card" style="display: block; margin-bottom: var(--space-md); text-decoration: none; color: inherit;"
         onclick="loadChecklistDetail('${list.id}'); return false;">
        <div class="title">${list.icon} ${list.name}</div>
        <div class="caption mt-sm">${list.description}</div>
      </a>
    `).join('') : `
      <div class="empty-state">
        <div class="empty-state-icon">&#128203;</div>
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
      <button class="icon-btn" onclick="openChecklistChoreAdder()" title="Add chore">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
    </div>

    <div class="checklist-header">
      <div class="title">${checklist.icon} ${checklist.name}</div>
      <div class="caption">${checklist.description}</div>
      <div class="checklist-meta">
        <span>~${checklist.total_minutes} min</span>
        <span>${checklist.overdue_count} need attention</span>
      </div>
    </div>

    <div id="checklist-items">
      ${checklist.chores.length === 0 ? `
        <div class="empty-state" style="padding: var(--space-xl) 0;">
          <div class="empty-state-icon">+</div>
          <div class="empty-state-text">Tap + to add chores</div>
        </div>
      ` : [...checklist.chores].sort((a, b) => {
        const aDone = !a.is_overdue && a.days_until_due > 0;
        const bDone = !b.is_overdue && b.days_until_due > 0;
        return aDone === bDone ? 0 : aDone ? 1 : -1;
      }).map(chore => {
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

// Complete Chore
async function completeChore(choreId) {
  try {
    const result = await api(`/chores/${choreId}/complete`, { method: 'POST' });

    // Refresh current view
    if (currentView === 'home') {
      loadHomeView();
    } else if (currentView === 'rooms' && currentRoomId) {
      loadRoomDetail(currentRoomId);
    } else if (currentView === 'lists' && currentChecklistId) {
      loadChecklistDetail(currentChecklistId);
    }

    // Show at most one confirmation modal per completion (duration takes priority)
    if (result && result.ask_about_duration) {
      setTimeout(() => {
        showDurationConfirmation(choreId, result.chore.name, result.chore.estimated_minutes);
      }, 400);
    } else if (result && result.ask_about_interval) {
      setTimeout(() => {
        showIntervalConfirmation(choreId, result.chore.name, result.chore.interval_days);
      }, 400);
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

      // Check if list is now empty
      const choreList = document.getElementById('chore-list');
      if (choreList && choreList.children.length === 0) {
        // Refresh the view
        if (currentView === 'home') {
          loadHomeView();
        }
      }

      // Show at most one confirmation modal per completion (duration takes priority)
      if (result.ask_about_duration) {
        showDurationConfirmation(choreId, result.chore.name, result.chore.estimated_minutes);
      } else if (result.ask_about_interval) {
        showIntervalConfirmation(choreId, result.chore.name, result.chore.interval_days);
      }
    }, 400);

  } catch (err) {
    console.error('Failed to complete chore:', err);
    container.classList.remove('card-completing');
    content.style.transform = 'translateX(0)';
  }
}

// Duration Confirmation Modal
function showDurationConfirmation(choreId, choreName, estimatedMinutes) {
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

function showIntervalConfirmation(choreId, choreName, intervalDays) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'interval-modal-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet';
  sheet.id = 'interval-modal-sheet';
  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Right schedule?</div>
    <div class="modal-subtitle">${choreName} is set to ${formatInterval(intervalDays)}.</div>
    <div class="modal-buttons">
      <button class="modal-btn modal-btn-primary" onclick="confirmInterval('${choreId}', true)">
        Yes, that's right
      </button>
      <button class="modal-btn modal-btn-secondary" onclick="showIntervalAdjust('${choreId}', ${intervalDays})">
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
  }, 300);
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

async function openChecklistChoreAdder() {
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
      <button class="chore-picker-item" onclick="addChoreToChecklist('${c.id}')">
        <span class="chore-picker-name">${c.name}</span>
        <span class="chore-picker-meta">${c.estimated_minutes} min · every ${c.interval_days}d</span>
      </button>
    `).join('')}
  `).join('');

  sheet.innerHTML = `
    <div class="modal-handle"></div>
    <div class="modal-title">Add chore</div>
    ${chores.length === 0 ? `
      <div class="modal-subtitle">All chores are already in this list.</div>
    ` : groupsHtml}
    <div class="modal-buttons" style="margin-top: var(--space-lg);">
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

async function addChoreToChecklist(choreId) {
  dismissChecklistAdder();
  try {
    await api(`/checklists/${currentChecklistId}/chores/${choreId}`, { method: 'POST' });
    loadChecklistDetail(currentChecklistId);
  } catch (err) {
    console.error('Failed to add chore to checklist:', err);
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

const CHECKLIST_ICONS = ['📋', '🏠', '🧹', '🛁', '🛋️', '🌿', '🎉', '✈️', '🌙', '☀️', '🎄', '🌸'];
let _selectedChecklistIcon = '📋';

function showCreateChecklistForm() {
  _selectedChecklistIcon = '📋';

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
        ${CHECKLIST_ICONS.map(icon => `
          <button class="icon-picker-btn ${icon === _selectedChecklistIcon ? 'selected' : ''}"
            onclick="selectChecklistIcon('${icon}')">${icon}</button>
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
    btn.classList.toggle('selected', btn.textContent === icon);
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

// Chore Management (Create / Edit / Delete)

async function openChoreEditor(choreId) {
  try {
    const [chore, rooms] = await Promise.all([
      api(`/chores/${choreId}`),
      api('/rooms'),
    ]);
    showChoreForm(chore, rooms);
  } catch (err) {
    console.error('Failed to load chore for editing:', err);
  }
}

async function openChoreCreator(roomId = null) {
  try {
    const rooms = await api('/rooms');
    showChoreForm(null, rooms, roomId);
  } catch (err) {
    console.error('Failed to load rooms:', err);
  }
}

function showChoreForm(chore, rooms, defaultRoomId = null) {
  const isEdit = !!chore;
  _editingChore = chore || null;
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'chore-form-overlay';

  const sheet = document.createElement('div');
  sheet.className = 'modal-sheet chore-form-sheet';
  sheet.id = 'chore-form-sheet';

  const categories = ['vacuum', 'mop', 'dust', 'declutter', 'clean', 'wash', 'wipe', 'maintain'];
  const selectedRoom = chore ? chore.room_id : defaultRoomId;
  const roomOptions = rooms.map(r =>
    `<option value="${r.id}" ${selectedRoom === r.id ? 'selected' : ''}>${r.icon} ${r.name}</option>`
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
          `<option value="${c}" ${(chore ? chore.category : 'clean') === c ? 'selected' : ''}>${c.charAt(0).toUpperCase() + c.slice(1)}</option>`
        ).join('')}
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
  const category = document.getElementById('chore-form-category')?.value;
  const intervalDays = parseInt(document.getElementById('chore-form-interval')?.value, 10);
  const estimatedMinutes = parseInt(document.getElementById('chore-form-duration')?.value, 10);

  if (!name) {
    const nameInput = document.getElementById('chore-form-name');
    if (nameInput) { nameInput.focus(); nameInput.style.borderColor = 'var(--overdue)'; }
    return;
  }

  const body = {
    name,
    room_id: roomId || null,
    category,
    interval_days: intervalDays,
    estimated_minutes: estimatedMinutes,
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
window.addChoreToChecklist = addChoreToChecklist;
window.dismissChecklistAdder = dismissChecklistAdder;
window.showCreateChecklistForm = showCreateChecklistForm;
window.selectChecklistIcon = selectChecklistIcon;
window.submitCreateChecklist = submitCreateChecklist;
window.dismissChecklistForm = dismissChecklistForm;
