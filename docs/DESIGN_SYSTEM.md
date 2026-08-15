# Aether Design System

Shared visual and interaction conventions for the Aether umbrella — currently
the chore manager (`aether/`) and Aether Pantry (`aether_pantry/`). Both are
separate add-ons with separate codebases, separate data, and no runtime
coupling. This document is the only thing that ties them together: each
app's CSS/JS is hand-authored to follow it independently. There is no shared
package, no `@import`, no build-time dependency between the two — if this
doc changes, each app's stylesheet is updated by hand to match.

## Purpose & Scope

Keep the two apps feeling like one family (dark mode, same type system, same
component language) without solving the same design decision twice, while
keeping them fully independent to build, deploy, and evolve separately.

## Color Tokens

Dark-mode base palette:

| Token | Value | Use |
|---|---|---|
| `--bg-primary` | `#0D0D0D` | Page background |
| `--bg-surface` | `#1A1A1A` | Cards, nav bar |
| `--bg-elevated` | `#242424` | Inputs, pills, modal chrome |
| `--border` | `#2A2A2A` | Hairline borders |
| `--text-primary` | `#FAFAFA` | Primary text |
| `--text-secondary` | `#8A8A8A` | Secondary text, captions |
| `--text-tertiary` | `#5A5A5A` | Placeholders, disabled state |
| `--accent` | `#FAFAFA` | Primary buttons, active nav |
| `--accent-muted` | `#3A3A3A` | Focus rings, subtle emphasis |

Status/semantic colors — same hue logic, different label set per app:

| Hue | Chores (`fresh`/`aging`/`due-soon`/`overdue`) | Pantry (`in_stock`/`low`/`out`) |
|---|---|---|
| Green `#3DD68C` | fresh | in_stock |
| Amber `#F0B429` | due-soon | low |
| Orange-red `#EF6B4A` | overdue | out |
| Muted green `#8FB596` | aging (chores-only fourth tier) | — |

Pantry has three tiers where chores has four (no "aging" equivalent) —
that's a legitimate per-domain difference, not a gap to fill.

## Spacing Scale

`--space-xs: 4px`, `--space-sm: 8px`, `--space-md: 16px`, `--space-lg: 24px`,
`--space-xl: 32px`, `--space-2xl: 48px`.

## Typography

Three-tier, system-font-only stack (no bundled webfont — both are
local-first HA add-ons and shouldn't gain a network dependency to render
text):

- `--font-family-display` (Georgia/serif stack) — page-level moments only:
  hero greetings, view headers, modal titles (`.hero` class).
- `--font-family-card` (Century Gothic/Avenir stack) — card and sub-titles
  (`.title` class).
- `--font-family` (system sans stack) — body copy, captions, buttons,
  everything else.

Sizes: `--font-size-hero: 26px`, `--font-size-title: 20px`,
`--font-size-body: 16px`, `--font-size-caption: 14px`,
`--font-size-small: 12px`.

## Radii, Borders, Elevation

`--radius-sm: 8px`, `--radius-md: 12px`, `--radius-lg: 16px`. Elevation is
communicated by background tier (`bg-primary` → `bg-surface` → `bg-elevated`)
plus a 1px `--border`, never box-shadow.

## Motion

`--transition-fast: 150ms ease-out` (taps, toggles),
`--transition-normal: 200ms ease-out` (modals, view transitions).

## Icon System

- Inline SVG only, stroke-based (`stroke="currentColor" stroke-width="2"`,
  round caps/joins) — no icon fonts, no network fetches.
- Icons are a `key -> SVG string` registry (`ICON_SVGS` in each app's
  `app.js`), stored as plain string keys in the DB (e.g. `category.icon =
  "produce"`). A `renderIcon(key)` helper falls back to printing the raw
  string for any unrecognized value, so old data never breaks rendering.
- Each app keeps its own icon set (chores: rooms/categories/checklists;
  pantry: pantry categories/checklists) — no shared icon module, but both
  follow the same registry pattern and the same UI-icon subset (check,
  warning, plus, pencil, trash, x, chevronRight, pause, play, tag) where
  their meaning overlaps.

## Layout Shell

- `.app` flex column, `.app-content` scrollable body, fixed `.bottom-nav`
  with `env(safe-area-inset-*)` padding for notches/home indicators.
- Bottom nav: 3–4 tabs, active tab distinguished by `--text-primary` vs
  `--text-tertiary` (icon + 11px label), never a background highlight.

## Component Patterns

- **Status pill**: small rounded-rect badge, uppercase, semantic color at
  15% opacity background + full-opacity text.
- **Status-flip control** (pantry-specific, no chores equivalent): a
  3-segment inline control for one-tap status changes, replacing chores'
  complete-checkbox pattern where the domain has 3 discrete states instead
  of a binary done/not-done.
- **Card**: `bg-surface` + 1px border + `radius-md`, stacked with
  `space-sm` gaps.
- **Edit-mode toggle**: a header-level pill button that flips a view's rows
  between their "fast interaction" affordance (status tap, complete tap)
  and their "editing" affordance (pencil icon opening a modal editor) —
  same row markup, different trailing control, driven by one boolean.
- **Modal**: bottom-sheet pattern (`modal-overlay` + `modal-sheet`,
  slide-up transform, drag handle), not a centered dialog. One shared
  `showModal(html)` / `hideModal()` pair per app.
- **Empty state**: centered `.title` + `.caption`, no illustration.
- **Form inputs**: `bg-elevated` fill, 1px border, `radius-sm`, focus ring
  via `border-color: var(--accent-muted)`.

## Interaction Conventions

- Hash-based view routing (`#view` or `#view/id`) with manual
  `history.pushState`/`popstate` — no router library, no build step.
- Tap targets sized for mobile (24px+ circular checkboxes/flip buttons).
- Reload-after-mutation, not optimistic UI: every write (`api()` POST/PUT/
  PATCH/DELETE) is followed by re-fetching and re-rendering the current
  view rather than hand-patching the DOM. Simpler, and correct by
  construction since the server is always the source of truth.

## Ingress & API Conventions

- Each app is a separate HA add-on; each injects its own
  `window.AETHER_*_BASE` server-side in `serve_root()` (chores:
  `AETHER_BASE`; pantry: `AETHER_PANTRY_BASE`), read by the frontend to
  build `API_BASE`, with a `location.pathname`-derived fallback for when
  `X-Ingress-Path` isn't forwarded.
- `IngressMiddleware` (Starlette `BaseHTTPMiddleware`) propagates
  `X-Ingress-Path` into ASGI `root_path` — copied verbatim between apps,
  since getting this wrong breaks the add-on specifically when accessed
  through HA (not when curled directly), which makes it easy to miss.
- `api()` fetch wrapper contract: JSON in/out, throws on non-2xx using the
  response body's `detail` field when present, returns `null` for 204.

## PWA / Manifest Conventions

Each app serves its own `static/manifest.json`, dynamically patched at
request time so `start_url`/icon paths respect the current ingress prefix
(the manifest route is registered before the static file mount so it wins).
Standalone display, portrait-primary, dark `background_color`/`theme_color`
matching `--bg-primary`.
