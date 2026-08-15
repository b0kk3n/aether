# Changelog

## 0.1.2

- Fix status changes appearing not to work in the All Products view: `effective_status` (and the other derived fields) was defined as a plain Python `@property` on the API model, which Pydantic v2 silently drops from JSON responses unless marked `@computed_field`. The status buttons were always functioning server-side, but the frontend never received the value telling it which one to highlight, so taps looked like they did nothing.
- Fix the same root cause producing literal "undefined" text in the grocery view's "Needs attention" section.
- Fix checklist product status appearing disconnected from the main Products view - checklists were using a different, correctly-populated field, so they worked while the main list silently didn't; same underlying bug, now consistent everywhere.
- Fix the page jumping to the top on every status change, edit, or other in-place update - the window (not the inner content div, which never actually scrolls) now has its scroll position preserved across refreshes; only switching to a different tab/view resets it, as expected.
- Added an API-level regression test (`tests/test_api_serialization.py`) so a future property-vs-computed-field mistake like this fails CI instead of only failing silently in the browser.

## 0.1.1

- Fix bottom nav icons rendering oversized (missing size constraint on the raw SVGs).
- Fix categories being impossible to edit or delete: empty categories were hidden from the All Products view entirely, and there was no edit entry point on category headers even when visible. Edit mode now shows every category and lets you rename, re-icon, or delete each one (delete is still blocked while products reference it).

## 0.1.0

- Initial release: grocery list, products, categories, checklists, intervals, vacation mode, All Products view.
