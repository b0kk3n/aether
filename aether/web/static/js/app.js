/**
 * Aether - Home Concierge
 * Main application JavaScript
 */

const API_BASE = '/api';

// State
let currentView = 'home';
let currentRoomId = null;
let currentChecklistId = null;

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
            </div>
          </div>
          <div class="chore-status ${statusClass}"></div>
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
        ${result.chores.map(chore => renderChoreCard(chore)).join('')}
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
    <a href="#" class="back-btn" onclick="loadRoomsView(); return false;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
      ${room.name}
    </a>

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
    <div class="greeting">
      <div class="greeting-text">Checklists</div>
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
  const html = `
    <a href="#" class="back-btn" onclick="loadListsView(); return false;">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="15 18 9 12 15 6"></polyline>
      </svg>
      Checklists
    </a>

    <div class="checklist-header">
      <div class="title">${checklist.icon} ${checklist.name}</div>
      <div class="caption">${checklist.description}</div>
      <div class="checklist-meta">
        <span>~${checklist.total_minutes} min</span>
        <span>${checklist.overdue_count} need attention</span>
      </div>
    </div>

    <div id="checklist-items">
      ${checklist.chores.map(chore => {
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
            ${chore.is_overdue ? '<div class="chore-status overdue"></div>' : ''}
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
    await api(`/chores/${choreId}/complete`, { method: 'POST' });

    // Refresh current view
    if (currentView === 'home') {
      loadHomeView();
    } else if (currentView === 'rooms' && currentRoomId) {
      loadRoomDetail(currentRoomId);
    } else if (currentView === 'lists' && currentChecklistId) {
      loadChecklistDetail(currentChecklistId);
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
    }, 400);

  } catch (err) {
    console.error('Failed to complete chore:', err);
    container.classList.remove('card-completing');
    content.style.transform = 'translateX(0)';
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
