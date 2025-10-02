# Book Creator Design Principles

## Experience North Star
- **Professional calm**: the interface should feel like a confident creative studio—clean typography, generous spacing, and crisp alignment keep focus on manuscript work rather than UI chrome.
- **Intuitive flow**: every surface favours clarity over decoration. Primary actions sit where the eye naturally travels, defaults are safe, and every interactive element gives immediate feedback.
- **Responsive empathy**: light and dark palettes adapt to ambient lighting, while motion is purposeful and respectful of reduced-motion preferences.

## Core System Tokens
All visual decisions must be expressed through the CSS variables defined in `apps/frontend/src/styles/globals.css`.

| Token Category | Key Variables | Usage Notes |
| --- | --- | --- |
| Color – surfaces | `--color-bg-canvas`, `--color-bg-surface`, `--color-bg-translucent` | Canvas gradients live on `<body>`; surfaces are always cards, modals, or navigation blocks. |
| Color – text | `--color-text-primary`, `--color-text-secondary`, `--color-text-muted` | Primary for headings, secondary for body copy, muted for metadata and helper text. |
| Color – accents | `--color-accent`, `--color-accent-strong`, `--color-secondary` | Accent drives primary calls-to-action; secondary handles success/positive states. |
| Status | `--color-success`, `--color-warning`, `--color-danger` | Pair with translucent backgrounds (e.g., `rgba(var, 0.16)`) for badges and banners. |
| Shape & shadow | `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-xl`, `--shadow-soft`, `--shadow-elevated` | Consistent radii keep cards and pills aligned across views; shadows differentiate elevation. |
| Timing | `--transition-short`, `--transition-medium`, `--transition-long` | Use short for hover/focus, medium for layout shifts, long for large overlays. |

Never hard-code hex values in modules—if a new visual needs colour, extend the token set first.

## Light & Dark Themes
The `ThemeProvider` stores the current theme (`light` or `dark`) and persists it in `localStorage`. Theme application happens by setting `data-theme` on `<html>`, which drives all `[data-theme="dark"]` overrides in `globals.css`.

*How to use in components*
```tsx
import { useTheme } from "../context/ThemeContext";

const { theme, toggleTheme } = useTheme();
// Use `theme` to choose illustration variants, or call
// `toggleTheme()` for custom toggles.
```
For most cases, drop the shared `<ThemeToggle />` component into toolbars or settings menus instead of rolling custom controls.

### Server-Safe Defaults
Initial render assumes light mode to avoid hydration flashes, then immediately syncs with the stored or system preference. Avoid accessing `window` or `document` during render; use the provider’s value inside effects.

## Layout & Composition
- **Two-column app frame**: `AppLayout` provides a glassmorphic sidebar with sticky workflow status. Content is centred inside `contentInner` (max-width 1120px) for predictable reading length.
- **Mobile behaviour**: below 960px the sidebar collapses to the top, and the theme toggle reappears via `.themeToggleMobile`.
- **Cards over tables**: whenever possible, summarise data in cards (`var(--radius-xl)` + `var(--shadow-soft)`) with subtle hover elevation. Tables remain for dense provider settings, but keep headers pinned and use `min-width` to control overflow.

## Interaction & Motion
- Buttons, pills, and cards all include hover translations (`translateY(-2px)`) to reinforce agency.
- Progress bars and key fills animate using `var(--transition-long)` for smooth stage progression feedback.
- `@media (prefers-reduced-motion: reduce)` in `globals.css` neutralises transitions for motion-sensitive users; do not add bespoke animations without the same guard.

## Accessibility Commitments
- Contrast meets WCAG AA in both modes; verify with the `docs/accessibility-checklist.md` flow when introducing new colours.
- Focus states rely on the global `:focus-visible` ring (`box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.3)`). Never remove it—use additional styling if a component needs refinement.
- `ThemeToggle` exposes `aria-pressed` and falls back to system preferences; replicate this pattern for any binary controls.

## Component Guidelines
- **Hero sections**: pair gradient overlays with a supporting paragraph capped at ~52ch for readability.
- **Status banners**: use translucent backgrounds with matching border hues. Examples live in `index.module.css` (`.status`, `.error`).
- **Data edits**: budgeting and provider forms employ grid layouts, `var(--radius-sm)` inputs, and inline helper text—follow that structure to keep validation messaging predictable.
- **Tables**: apply `tableWrapper` for scrollable containers, `th` uppercase labels, and `td` with generous padding. Keep destructive actions as `dangerButton` variants.
- **Overlays & modals**: use the shared `<Modal />` component for confirmations and editors. It renders via portal, locks body scroll, and wires `Escape`/outside-click dismissal. Pass `size="lg"` plus a custom container class (e.g., `promptModalContainer`) when you need the gradient prompt editor style; smaller confirmations can rely on the default surface. Provide `footer` content instead of hard-coding buttons in bodies so alignment stays consistent.

## Dark/Light Toggle Placement
- Desktop: top-right of the sidebar (`.themeToggleDesktop`).
- Mobile / unauthenticated pages: `.themeToggleMobile` inside the main area and a floating version on the login screen.
- Developers may surface the toggle in feature sandboxes, but avoid duplicating it within a single viewport.

## Implementation Notes
1. Wrap new Next.js pages in `AppLayout` to inherit theming, spacing, and skip links. For standalone pages (e.g., auth), manually include `<ThemeToggle />` where appropriate.
2. When styling, prefer utility wrappers already present: `status`, `error`, `badge`, `card` patterns are showcased on the dashboard and agent settings pages.
3. Animations must degrade gracefully—test them by enabling “Reduce Motion” in your OS before shipping.
4. Test both colour modes via the toggle and by clearing `localStorage` to ensure system-preference fallbacks operate correctly.

## Extending the Design System
- **Adding a token**: edit `globals.css`, define light + dark values, and document the new token here with usage guidance.
- **Creating new patterns**: sketch in Figma or describe intent in `docs/design/design-principles.md`’s appendix before coding; align on naming to avoid one-off classes.
- **Contributing components**: colocate module CSS with the component, use existing tokens, and add concise inline comments only for complex logic (never for declarative styling).

By keeping every visual decision rooted in this system we ensure the Book Creator app feels coherent, trustworthy, and flexible enough to evolve through future phases.
