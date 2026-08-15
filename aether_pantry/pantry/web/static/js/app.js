/**
 * Aether Pantry
 * Main application JavaScript
 *
 * Independent from the sibling Aether (chores) app.js - same interaction
 * conventions (hash routing, ingress base derivation, api() wrapper, modal
 * pattern) per docs/DESIGN_SYSTEM.md, but hand-authored separately with no
 * shared import.
 */

// When served via HA ingress, window.AETHER_PANTRY_BASE is injected server-side.
// Fallback: derive the base from the current page URL (works when
// X-Ingress-Path is not forwarded - the browser URL already contains the
// ingress prefix, e.g. /api/hassio_ingress/TOKEN/).
const API_BASE = (window.AETHER_PANTRY_BASE != null && window.AETHER_PANTRY_BASE !== '')
    ? window.AETHER_PANTRY_BASE + '/api'
    : window.location.pathname.replace(/\/+$/, '') + '/api';

// Icon system - inline SVG only, no icon fonts/network fetches. Keys are
// stored as plain strings in the DB (e.g. category.icon = "produce").
// renderIcon() falls back to printing the raw string for any unknown value.
const ICON_SVGS = {
  // UI icons
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
  warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
  pencil: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"></path></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
  chevronRight: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>',
  cart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8l-9-5-9 5 9 5 9-5z"></path><path d="M3 8v8l9 5 9-5V8"></path><line x1="12" y1="13" x2="12" y2="21"></line></svg>',
  clipboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="3" width="12" height="18" rx="2"></rect><rect x="9" y="1.5" width="6" height="3" rx="1"></rect><line x1="9" y1="11" x2="15" y2="11"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>',
  pause: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>',
  play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41L11 3.83A2 2 0 0 0 9.59 3.24L4 3a1 1 0 0 0-1 1l.24 5.59a2 2 0 0 0 .59 1.41l9.58 9.58a2 2 0 0 0 2.83 0l4.35-4.35a2 2 0 0 0 0-2.82z"></path><circle cx="7.5" cy="7.5" r="1"></circle></svg>',
  // Category icons
  produce: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21a7 7 0 0 0 7-7c0-4-3-6-3-6s-1 2-4 2-4-2-4-2-3 2-3 6a7 7 0 0 0 7 7z"></path><path d="M12 8V4"></path><path d="M12 4c1-1 2-1.5 3-1"></path></svg>',
  dairy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6v4l2 3v11a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V9l2-3z"></path><line x1="7" y1="13" x2="17" y2="13"></line></svg>',
  meat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 13a5 5 0 1 0-5-5c0 2 1 3 0 5s-4 3-4 6a4 4 0 0 0 7 2.6"></path><line x1="19" y1="19" x2="21.5" y2="21.5"></line></svg>',
  jar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="8" width="12" height="13" rx="2"></rect><path d="M8 8V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v3"></path><line x1="6" y1="13" x2="18" y2="13"></line></svg>',
  spice: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 8h8l-1 13a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2z"></path><path d="M9 8V5a3 3 0 0 1 6 0v3"></path><line x1="10" y1="12" x2="10.01" y2="12"></line><line x1="14" y1="12" x2="14.01" y2="12"></line><line x1="12" y1="15" x2="12.01" y2="15"></line></svg>',
  spray: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 22V10a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v12z"></path><path d="M11 8V5h4l2-2"></path><line x1="4" y1="10" x2="6" y2="10"></line><line x1="4" y1="14" x2="6" y2="14"></line></svg>',
  household: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>',
  snowflake: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="22"></line><line x1="4.9" y1="4.9" x2="19.1" y2="19.1"></line><line x1="4.9" y1="19.1" x2="19.1" y2="4.9"></line><line x1="2" y1="12" x2="22" y2="12"></line></svg>',
};

const CATEGORY_ICON_KEYS = ['produce', 'dairy', 'meat', 'jar', 'spice', 'spray', 'household', 'snowflake', 'tag', 'box'];
const CHECKLIST_ICON_KEYS = ['clipboard', 'cart', 'box', 'jar', 'tag', 'household'];

function renderIcon(key, extraClass = '') {
  if (key && ICON_SVGS[key]) {
    return `<span class="icon ${extraClass}">${ICON_SVGS[key]}</span>`;
  }
  return `<span class="icon icon-emoji ${extraClass}">${key || ''}</span>`;
}

// State
let currentView = 'grocery';
let currentChecklistId = null;
let _editingProduct = null;
let _allCategories = [];
let _allChecklistProductIds = new Set();
let _productsEditMode = false;

const appContent = document.getElementById('app-content');
const navItems = document.querySelectorAll('.nav-item');

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initModal();
  loadView('grocery');
});

// ---------------------------------------------------------------------------
// Navigation / routing
// ---------------------------------------------------------------------------

function initNavigation() {
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const view = item.dataset.view;
      setActiveNav(view);
      loadView(view);
    });
  });

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
  setActiveNav(view);

  if (pushState) {
    history.pushState({ view, id }, '', `#${view}${id ? '/' + id : ''}`);
  }

  switch (view) {
    case 'grocery':
      loadGroceryView();
      break;
    case 'products':
      loadProductsView();
      break;
    case 'checklists':
      if (id) {
        loadChecklistDetail(id);
      } else {
        loadChecklistsView();
      }
      break;
  }
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

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

function showToast(message) {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('visible');
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove('visible'), 2200);
}

// ---------------------------------------------------------------------------
// Modal management
// ---------------------------------------------------------------------------

function initModal() {
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

  modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) hideModal();
  });
}

function showModal(content) {
  document.getElementById('modal-content').innerHTML = content;
  document.getElementById('modal-overlay').classList.add('visible');
}

function hideModal() {
  document.getElementById('modal-overlay').classList.remove('visible');
}

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

const STATUS_LABELS = { in_stock: 'In Stock', low: 'Low', out: 'Out' };

function statusPillHTML(status) {
  return `<span class="status-pill ${status}">${STATUS_LABELS[status]}</span>`;
}

function statusFlipHTML(effectiveStatus) {
  return `
    <div class="status-flip">
      ${['in_stock', 'low', 'out'].map(s => `
        <button type="button" class="status-flip-btn ${s} ${effectiveStatus === s ? 'active ' + s : ''}" data-status="${s}">
          ${s === 'in_stock' ? 'IN' : s.toUpperCase()}
        </button>
      `).join('')}
    </div>
  `;
}

function wireStatusFlip(container, productId, onDone) {
  container.querySelectorAll('.status-flip-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await api(`/products/${productId}/status`, {
          method: 'PATCH',
          body: JSON.stringify({ status: btn.dataset.status }),
        });
        if (onDone) onDone();
      } catch (err) {
        showToast(err.message);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Grocery view (hero / default view)
// ---------------------------------------------------------------------------

async function loadGroceryView() {
  appContent.innerHTML = `<div class="loading">Loading...</div>`;

  try {
    const [items, attention] = await Promise.all([
      api('/grocery-list'),
      api('/products/needing-attention'),
    ]);

    const linkedProductIds = new Set(items.filter(i => i.product_id).map(i => i.product_id));
    const surfaced = attention.filter(p => !linkedProductIds.has(p.id));

    let html = `
      <div class="view-header"><span class="hero">Grocery</span></div>
      <form class="grocery-form" id="grocery-form">
        <input class="grocery-input" id="grocery-input" type="text" placeholder="Add anything..." autocomplete="off">
        <button type="submit" class="grocery-add-btn">Add</button>
      </form>
    `;

    if (surfaced.length > 0) {
      html += `<div class="section-label">Needs attention</div>`;
      surfaced.forEach(p => {
        html += `
          <div class="attention-row" data-product-id="${p.id}">
            ${statusPillHTML(p.effective_status)}
            <span class="body">${escapeHTML(p.name)}</span>
            <button type="button" class="attention-add-btn">Add to list</button>
          </div>
        `;
      });
    }

    html += `<div class="section-label">On the list</div>`;
    if (items.length === 0) {
      html += `<div class="empty-state"><div class="title">All clear</div><div class="caption">Add anything above - dinner ingredients, one-offs, whatever.</div></div>`;
    } else {
      items.forEach(item => {
        html += `
          <div class="grocery-item" data-item-id="${item.id}">
            <button type="button" class="grocery-checkbox" data-action="check-off">${renderIcon('check')}</button>
            <div class="grocery-item-text">
              <div class="grocery-item-raw body">${escapeHTML(item.raw_text)}</div>
              ${item.product_id ? `
                <div class="linked-chip">
                  ${renderIcon('tag')}
                  <span>Linked${item.linked_product_effective_status ? ' &middot; ' + STATUS_LABELS[item.linked_product_effective_status] : ''}</span>
                </div>
              ` : ''}
            </div>
            <button type="button" class="grocery-remove-btn" data-action="remove">${renderIcon('x')}</button>
          </div>
        `;
      });
    }

    appContent.innerHTML = html;

    document.getElementById('grocery-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('grocery-input');
      const text = input.value.trim();
      if (!text) return;
      try {
        await api('/grocery-list', { method: 'POST', body: JSON.stringify({ raw_text: text }) });
        input.value = '';
        loadGroceryView();
      } catch (err) {
        showToast(err.message);
      }
    });

    appContent.querySelectorAll('.attention-row .attention-add-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const row = e.target.closest('.attention-row');
        const productId = row.dataset.productId;
        try {
          await api(`/grocery-list/from-product/${productId}`, { method: 'POST' });
          loadGroceryView();
        } catch (err) {
          showToast(err.message);
        }
      });
    });

    appContent.querySelectorAll('.grocery-item').forEach(row => {
      const itemId = row.dataset.itemId;
      row.querySelector('[data-action="check-off"]').addEventListener('click', async () => {
        try {
          await api(`/grocery-list/${itemId}/check-off`, { method: 'POST' });
          loadGroceryView();
        } catch (err) {
          showToast(err.message);
        }
      });
      row.querySelector('[data-action="remove"]').addEventListener('click', async () => {
        try {
          await api(`/grocery-list/${itemId}`, { method: 'DELETE' });
          loadGroceryView();
        } catch (err) {
          showToast(err.message);
        }
      });
    });
  } catch (err) {
    appContent.innerHTML = `<div class="empty-state"><div class="title">Couldn't load</div><div class="caption">${escapeHTML(err.message)}</div></div>`;
  }
}

// ---------------------------------------------------------------------------
// Products view (All Products)
// ---------------------------------------------------------------------------

async function loadProductsView() {
  appContent.innerHTML = `<div class="loading">Loading...</div>`;

  try {
    const [products, categories, vacation] = await Promise.all([
      api('/products'),
      api('/categories'),
      api('/vacation'),
    ]);
    _allCategories = categories;

    const byCategory = new Map();
    products.forEach(p => {
      const key = p.category_id || '__none__';
      if (!byCategory.has(key)) byCategory.set(key, []);
      byCategory.get(key).push(p);
    });

    let html = `
      <div class="view-header">
        <span class="hero">Products</span>
        <div class="view-header-actions">
          <button type="button" class="pill-btn ${vacation.is_active ? 'active' : ''}" id="vacation-toggle">
            ${renderIcon(vacation.is_active ? 'play' : 'pause')}
            <span>${vacation.is_active ? 'Resume' : 'Vacation'}</span>
          </button>
          <button type="button" class="pill-btn ${_productsEditMode ? 'active' : ''}" id="edit-toggle">
            ${renderIcon('pencil')}
            <span>${_productsEditMode ? 'Done' : 'Edit'}</span>
          </button>
        </div>
      </div>
    `;

    if (_productsEditMode) {
      html += `
        <div class="card-row" style="margin-bottom: var(--space-lg);">
          <button type="button" class="pill-btn" id="add-product-btn">${renderIcon('plus')}<span>Add product</span></button>
          <button type="button" class="pill-btn" id="add-category-btn">${renderIcon('plus')}<span>Add category</span></button>
        </div>
      `;
    }

    const groupOrder = [];
    if (byCategory.has('__none__')) groupOrder.push({ id: null, name: 'Uncategorized', icon: 'tag' });
    // In edit mode, show every category (even ones with no products yet) so
    // a freshly-added or now-empty category is still reachable to edit/delete.
    categories.forEach(c => { if (byCategory.has(c.id) || _productsEditMode) groupOrder.push(c); });

    if (products.length === 0) {
      html += `<div class="empty-state"><div class="title">Nothing tracked yet</div><div class="caption">Products show up here once you add them - or link a grocery line to one.</div></div>`;
    }

    groupOrder.forEach(cat => {
      const key = cat.id || '__none__';
      const items = byCategory.get(key) || [];
      html += `
        <div class="category-group">
          <div class="category-group-header">
            ${renderIcon(cat.icon, '')}
            <span class="title">${escapeHTML(cat.name)}</span>
            ${_productsEditMode && cat.id ? `<button type="button" class="edit-btn" data-action="edit-category" data-category-id="${cat.id}">${renderIcon('pencil')}</button>` : ''}
          </div>
          ${items.map(p => `
            <div class="product-row" data-product-id="${p.id}">
              <div class="product-info">
                <div class="product-name">${escapeHTML(p.name)}</div>
                ${p.interval_days ? `<div class="product-meta"><span>every ~${p.interval_days}d</span></div>` : ''}
              </div>
              ${_productsEditMode
                ? `<button type="button" class="edit-btn" data-action="edit-product">${renderIcon('pencil')}</button>`
                : statusFlipHTML(p.effective_status)
              }
            </div>
          `).join('')}
        </div>
      `;
    });

    appContent.innerHTML = html;

    document.getElementById('edit-toggle').addEventListener('click', () => {
      _productsEditMode = !_productsEditMode;
      loadProductsView();
    });

    document.getElementById('vacation-toggle').addEventListener('click', async () => {
      try {
        if (vacation.is_active) {
          const result = await api('/vacation/end', { method: 'POST' });
          showToast(`Welcome back! ${result.products_affected} product(s) shifted forward.`);
        } else {
          await api('/vacation/start', { method: 'POST' });
          showToast('Vacation mode started - interval clocks paused.');
        }
        loadProductsView();
      } catch (err) {
        showToast(err.message);
      }
    });

    if (_productsEditMode) {
      document.getElementById('add-product-btn').addEventListener('click', () => openProductEditor(null));
      document.getElementById('add-category-btn').addEventListener('click', () => openCategoryEditor());

      appContent.querySelectorAll('[data-action="edit-product"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const productId = e.target.closest('.product-row').dataset.productId;
          const product = products.find(p => p.id === productId);
          openProductEditor(product);
        });
      });

      appContent.querySelectorAll('[data-action="edit-category"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const categoryId = btn.dataset.categoryId;
          const category = categories.find(c => c.id === categoryId);
          openCategoryEditor(category);
        });
      });
    } else {
      appContent.querySelectorAll('.product-row').forEach(row => {
        wireStatusFlip(row, row.dataset.productId, loadProductsView);
      });
    }
  } catch (err) {
    appContent.innerHTML = `<div class="empty-state"><div class="title">Couldn't load</div><div class="caption">${escapeHTML(err.message)}</div></div>`;
  }
}

function categoryOptionsHTML(selectedId) {
  let html = `<option value="" ${!selectedId ? 'selected' : ''}>Uncategorized</option>`;
  _allCategories.forEach(c => {
    html += `<option value="${c.id}" ${c.id === selectedId ? 'selected' : ''}>${escapeHTML(c.name)}</option>`;
  });
  return html;
}

function openProductEditor(product) {
  _editingProduct = product;
  const isNew = !product;

  showModal(`
    <div class="modal-title">${isNew ? 'Add product' : 'Edit product'}</div>
    <div class="form-group">
      <label class="form-label">Name</label>
      <input class="form-input" id="pf-name" type="text" value="${product ? escapeHTML(product.name) : ''}">
    </div>
    <div class="form-group">
      <label class="form-label">Category</label>
      <select class="form-select" id="pf-category">${categoryOptionsHTML(product ? product.category_id : null)}</select>
    </div>
    <div class="form-group">
      <label class="form-label">Interval (days, optional)</label>
      <input class="form-input" id="pf-interval" type="number" min="1" value="${product && product.interval_days ? product.interval_days : ''}">
    </div>
    <div class="modal-buttons">
      <button type="button" class="modal-btn modal-btn-primary" id="pf-save">Save</button>
      ${!isNew ? '<button type="button" class="modal-btn modal-btn-danger" id="pf-delete">Delete product</button>' : ''}
      <button type="button" class="modal-btn modal-btn-secondary" id="pf-cancel">Cancel</button>
    </div>
  `);

  document.getElementById('pf-cancel').addEventListener('click', hideModal);
  document.getElementById('pf-save').addEventListener('click', async () => {
    const name = document.getElementById('pf-name').value.trim();
    if (!name) { showToast('Name is required'); return; }
    const categoryId = document.getElementById('pf-category').value || null;
    const intervalRaw = document.getElementById('pf-interval').value;
    const intervalDays = intervalRaw ? parseInt(intervalRaw, 10) : null;

    try {
      if (isNew) {
        await api('/products', {
          method: 'POST',
          body: JSON.stringify({ name, category_id: categoryId, interval_days: intervalDays }),
        });
      } else {
        await api(`/products/${product.id}`, {
          method: 'PUT',
          body: JSON.stringify({ name, category_id: categoryId, interval_days: intervalDays }),
        });
      }
      hideModal();
      loadProductsView();
    } catch (err) {
      showToast(err.message);
    }
  });

  const deleteBtn = document.getElementById('pf-delete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      try {
        await api(`/products/${product.id}`, { method: 'DELETE' });
        hideModal();
        loadProductsView();
      } catch (err) {
        showToast(err.message);
      }
    });
  }
}

function openCategoryEditor(category) {
  const isNew = !category;

  showModal(`
    <div class="modal-title">${isNew ? 'Add category' : 'Edit category'}</div>
    <div class="form-group">
      <label class="form-label">Name</label>
      <input class="form-input" id="cf-name" type="text" value="${category ? escapeHTML(category.name) : ''}">
    </div>
    <div class="form-group">
      <label class="form-label">Icon</label>
      <select class="form-select" id="cf-icon">
        ${CATEGORY_ICON_KEYS.map(k => `<option value="${k}" ${category && category.icon === k ? 'selected' : ''}>${k}</option>`).join('')}
      </select>
    </div>
    <div class="modal-buttons">
      <button type="button" class="modal-btn modal-btn-primary" id="cf-save">Save</button>
      ${!isNew ? '<button type="button" class="modal-btn modal-btn-danger" id="cf-delete">Delete category</button>' : ''}
      <button type="button" class="modal-btn modal-btn-secondary" id="cf-cancel">Cancel</button>
    </div>
  `);

  document.getElementById('cf-cancel').addEventListener('click', hideModal);
  document.getElementById('cf-save').addEventListener('click', async () => {
    const name = document.getElementById('cf-name').value.trim();
    if (!name) { showToast('Name is required'); return; }
    const icon = document.getElementById('cf-icon').value;

    try {
      if (isNew) {
        await api('/categories', { method: 'POST', body: JSON.stringify({ name, icon }) });
      } else {
        await api(`/categories/${category.id}`, { method: 'PUT', body: JSON.stringify({ name, icon }) });
      }
      hideModal();
      loadProductsView();
    } catch (err) {
      showToast(err.message);
    }
  });

  const deleteBtn = document.getElementById('cf-delete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      try {
        await api(`/categories/${category.id}`, { method: 'DELETE' });
        hideModal();
        loadProductsView();
      } catch (err) {
        // Backend blocks delete while products still reference this
        // category (409, "N product(s) use this category; reassign or
        // delete them first.") - surfaced verbatim via the toast.
        showToast(err.message);
      }
    });
  }
}

// ---------------------------------------------------------------------------
// Checklists view
// ---------------------------------------------------------------------------

async function loadChecklistsView() {
  appContent.innerHTML = `<div class="loading">Loading...</div>`;

  try {
    const checklists = await api('/checklists');

    let html = `
      <div class="view-header">
        <span class="hero">Checklists</span>
        <button type="button" class="pill-btn" id="new-checklist-btn">${renderIcon('plus')}<span>New</span></button>
      </div>
    `;

    if (checklists.length === 0) {
      html += `<div class="empty-state"><div class="title">No checklists yet</div><div class="caption">Market, Sale, Breakfast, Cupboard - whatever cuts across your products.</div></div>`;
    } else {
      checklists.forEach(cl => {
        html += `
          <div class="card checklist-card" data-checklist-id="${cl.id}">
            ${renderIcon(cl.icon)}
            <div class="checklist-card-info">
              <div class="title">${escapeHTML(cl.name)}</div>
              ${cl.description ? `<div class="caption">${escapeHTML(cl.description)}</div>` : ''}
            </div>
            <div class="checklist-counts">
              ${cl.out_count ? `<span class="checklist-count out">${cl.out_count}</span>` : ''}
              ${cl.low_count ? `<span class="checklist-count low">${cl.low_count}</span>` : ''}
              ${cl.in_stock_count ? `<span class="checklist-count in_stock">${cl.in_stock_count}</span>` : ''}
            </div>
            ${renderIcon('chevronRight')}
          </div>
        `;
      });
    }

    appContent.innerHTML = html;

    document.getElementById('new-checklist-btn').addEventListener('click', () => openChecklistEditor());

    appContent.querySelectorAll('.checklist-card').forEach(card => {
      card.addEventListener('click', () => {
        loadView('checklists', card.dataset.checklistId);
      });
    });
  } catch (err) {
    appContent.innerHTML = `<div class="empty-state"><div class="title">Couldn't load</div><div class="caption">${escapeHTML(err.message)}</div></div>`;
  }
}

async function loadChecklistDetail(checklistId) {
  currentChecklistId = checklistId;
  appContent.innerHTML = `<div class="loading">Loading...</div>`;

  try {
    const checklist = await api(`/checklists/${checklistId}`);
    _allChecklistProductIds = new Set(checklist.products.map(p => p.id));

    let html = `
      <div class="view-header">
        <span class="hero">${escapeHTML(checklist.name)}</span>
        <div class="view-header-actions">
          <button type="button" class="pill-btn" id="checklist-add-products-btn">${renderIcon('plus')}<span>Add</span></button>
          <button type="button" class="pill-btn" id="checklist-edit-btn">${renderIcon('pencil')}</button>
        </div>
      </div>
      ${checklist.description ? `<div class="caption" style="margin-bottom: var(--space-lg);">${escapeHTML(checklist.description)}</div>` : ''}
    `;

    if (checklist.products.length === 0) {
      html += `<div class="empty-state"><div class="title">No products yet</div><div class="caption">Add products to walk this checklist.</div></div>`;
    } else {
      checklist.products.forEach(p => {
        html += `
          <div class="product-row" data-product-id="${p.id}">
            <div class="product-info">
              <div class="product-name">${escapeHTML(p.name)}</div>
              <div class="product-meta">${p.category_name ? escapeHTML(p.category_name) : ''}</div>
            </div>
            ${statusFlipHTML(p.effective_status)}
            <button type="button" class="grocery-remove-btn" data-action="remove-from-checklist">${renderIcon('x')}</button>
          </div>
        `;
      });
    }

    appContent.innerHTML = html;

    document.getElementById('checklist-edit-btn').addEventListener('click', () => openChecklistEditor(checklist));
    document.getElementById('checklist-add-products-btn').addEventListener('click', () => openAddProductsToChecklist(checklistId));

    appContent.querySelectorAll('.product-row').forEach(row => {
      const productId = row.dataset.productId;
      wireStatusFlip(row, productId, () => loadChecklistDetail(checklistId));
      row.querySelector('[data-action="remove-from-checklist"]').addEventListener('click', async () => {
        try {
          await api(`/checklists/${checklistId}/products/${productId}`, { method: 'DELETE' });
          loadChecklistDetail(checklistId);
        } catch (err) {
          showToast(err.message);
        }
      });
    });
  } catch (err) {
    appContent.innerHTML = `<div class="empty-state"><div class="title">Couldn't load</div><div class="caption">${escapeHTML(err.message)}</div></div>`;
  }
}

function openChecklistEditor(checklist) {
  const isNew = !checklist;

  showModal(`
    <div class="modal-title">${isNew ? 'New checklist' : 'Edit checklist'}</div>
    <div class="form-group">
      <label class="form-label">Name</label>
      <input class="form-input" id="clf-name" type="text" value="${checklist ? escapeHTML(checklist.name) : ''}">
    </div>
    <div class="form-group">
      <label class="form-label">Description (optional)</label>
      <input class="form-input" id="clf-description" type="text" value="${checklist ? escapeHTML(checklist.description) : ''}">
    </div>
    <div class="form-group">
      <label class="form-label">Icon</label>
      <select class="form-select" id="clf-icon">
        ${CHECKLIST_ICON_KEYS.map(k => `<option value="${k}" ${checklist && checklist.icon === k ? 'selected' : ''}>${k}</option>`).join('')}
      </select>
    </div>
    <div class="modal-buttons">
      <button type="button" class="modal-btn modal-btn-primary" id="clf-save">Save</button>
      ${!isNew ? '<button type="button" class="modal-btn modal-btn-danger" id="clf-delete">Delete checklist</button>' : ''}
      <button type="button" class="modal-btn modal-btn-secondary" id="clf-cancel">Cancel</button>
    </div>
  `);

  document.getElementById('clf-cancel').addEventListener('click', hideModal);
  document.getElementById('clf-save').addEventListener('click', async () => {
    const name = document.getElementById('clf-name').value.trim();
    if (!name) { showToast('Name is required'); return; }
    const description = document.getElementById('clf-description').value.trim();
    const icon = document.getElementById('clf-icon').value;

    try {
      if (isNew) {
        const created = await api('/checklists', {
          method: 'POST',
          body: JSON.stringify({ name, description, icon, product_ids: [] }),
        });
        hideModal();
        loadView('checklists', created.id);
      } else {
        await api(`/checklists/${checklist.id}`, {
          method: 'PUT',
          body: JSON.stringify({ name, description, icon }),
        });
        hideModal();
        loadChecklistDetail(checklist.id);
      }
    } catch (err) {
      showToast(err.message);
    }
  });

  const deleteBtn = document.getElementById('clf-delete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      try {
        await api(`/checklists/${checklist.id}`, { method: 'DELETE' });
        hideModal();
        loadView('checklists');
      } catch (err) {
        showToast(err.message);
      }
    });
  }
}

async function openAddProductsToChecklist(checklistId) {
  try {
    const allProducts = await api('/products');
    const available = allProducts.filter(p => !_allChecklistProductIds.has(p.id));

    if (available.length === 0) {
      showModal(`<div class="modal-title">Add products</div><div class="caption">Every product is already on this checklist.</div><div class="modal-buttons"><button type="button" class="modal-btn modal-btn-secondary" id="ap-cancel">Close</button></div>`);
      document.getElementById('ap-cancel').addEventListener('click', hideModal);
      return;
    }

    showModal(`
      <div class="modal-title">Add products</div>
      ${available.map(p => `
        <label class="card-row" style="padding: var(--space-xs) 0;">
          <input type="checkbox" value="${p.id}" class="ap-checkbox">
          <span class="body">${escapeHTML(p.name)}</span>
        </label>
      `).join('')}
      <div class="modal-buttons">
        <button type="button" class="modal-btn modal-btn-primary" id="ap-save">Add selected</button>
        <button type="button" class="modal-btn modal-btn-secondary" id="ap-cancel">Cancel</button>
      </div>
    `);

    document.getElementById('ap-cancel').addEventListener('click', hideModal);
    document.getElementById('ap-save').addEventListener('click', async () => {
      const ids = Array.from(document.querySelectorAll('.ap-checkbox:checked')).map(cb => cb.value);
      if (ids.length === 0) { hideModal(); return; }
      try {
        await api(`/checklists/${checklistId}/products/bulk`, {
          method: 'POST',
          body: JSON.stringify({ product_ids: ids }),
        });
        hideModal();
        loadChecklistDetail(checklistId);
      } catch (err) {
        showToast(err.message);
      }
    });
  } catch (err) {
    showToast(err.message);
  }
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function escapeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}
