# Strawberry Greenhouse Dashboard Design System

## 1. Atmosphere & Identity

A quiet greenhouse control room for growers comparing practical work decisions, not a decorative analytics site. The signature is evidence-led comparison: dense controls, restrained surfaces, and visible rule explanations that keep the simulated crop state traceable.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | --surface-primary | #F6F7F2 | #11130F | Main app background |
| Surface/secondary | --surface-secondary | #FFFFFF | #191C16 | Sidebar and chart surfaces |
| Surface/elevated | --surface-elevated | #EEF1E8 | #20251D | Metric bands, comparison panels |
| Text/primary | --text-primary | #1C2118 | #F4F6EF | Headlines, body |
| Text/secondary | --text-secondary | #5D6657 | #B8C2AF | Captions, hints |
| Text/tertiary | --text-tertiary | #8A9383 | #7F8978 | Disabled, muted metadata |
| Border/default | --border-default | #D8DECf | #333B2D | Dividers, outlines |
| Border/subtle | --border-subtle | #E8ECE0 | #262C22 | Soft separations |
| Accent/primary | --accent-primary | #2F6F5E | #67BFA7 | Primary commands, selected state |
| Accent/hover | --accent-hover | #24584A | #8BD4C0 | Hover state |
| Status/success | --status-success | #338B5B | #5FD28D | Improved crop state |
| Status/warning | --status-warning | #B87820 | #F1B454 | Cautions |
| Status/error | --status-error | #B64A3A | #F17C6C | Risk increase |
| Status/info | --status-info | #3A6E9F | #78AEE0 | Evidence and neutral notes |

### Rules

- Accent is used for selection and commands only, not decoration.
- Risk colors are reserved for warnings and chart traces with risk semantics.
- Never introduce a color not in this table. Extend this table first.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| Display | 40px / 2.5rem | 700 | 1.15 | 0 | App title |
| H1 | 32px / 2rem | 700 | 1.2 | 0 | Page headers |
| H2 | 24px / 1.5rem | 650 | 1.3 | 0 | Chart groups |
| H3 | 18px / 1.125rem | 650 | 1.4 | 0 | Panel titles |
| Body/lg | 17px / 1.0625rem | 400 | 1.6 | 0 | Lead explanation |
| Body | 15px / 0.9375rem | 400 | 1.55 | 0 | Default text |
| Body/sm | 13px / 0.8125rem | 400 | 1.5 | 0 | Secondary info |
| Caption | 12px / 0.75rem | 550 | 1.4 | 0 | Labels, metadata |
| Overline | 11px / 0.6875rem | 650 | 1.3 | 0.04em | Section labels |

### Font Stack

- Primary: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
- Mono: "SFMono-Regular", Consolas, "Liberation Mono", monospace
- Serif: not used

### Rules

- Body text never below 13px in dense panels.
- Letter spacing stays at 0 except overline labels.
- Keep headings compact inside dashboards; no landing-page scale type.

## 4. Spacing & Layout

### Base Unit

All spacing derives from a base of **4px**.

| Token | Value | Usage |
|-------|-------|-------|
| --space-1 | 4px | Tight icon-to-label gaps |
| --space-2 | 8px | Compact inline groups |
| --space-3 | 12px | Form field padding |
| --space-4 | 16px | Standard panel padding |
| --space-5 | 20px | Metric row spacing |
| --space-6 | 24px | Chart group spacing |
| --space-8 | 32px | Major dashboard bands |
| --space-10 | 40px | Page sections |
| --space-12 | 48px | Large vertical breaks |
| --space-16 | 64px | Maximum page rhythm |
| --space-20 | 80px | Reserved for non-dashboard pages |
| --space-24 | 96px | Reserved for non-dashboard pages |

### Grid

- Max content width: 1440px
- Column system: responsive two-column dashboard, controls left and comparison output right
- Breakpoints: sm 640px, md 768px, lg 1024px, xl 1280px, 2xl 1536px

### Rules

- Prefer full-width bands and compact panels over nested cards.
- Use stable chart heights so filters do not cause layout jump.

## 5. Components

### Scenario Controls
- **Structure**: grouped sidebar inputs for initial state, environment, work intensity, and duration.
- **Variants**: baseline, active scenario, risk scenario.
- **Spacing**: --space-3 inside fields, --space-6 between groups.
- **States**: default, focus, disabled, validation error.
- **Accessibility**: every input has a visible label and bounded range.
- **Motion**: none beyond native focus.

### Metric Strip
- **Structure**: compact row of end-state metrics.
- **Variants**: neutral, improvement, warning.
- **Spacing**: --space-4 padding, --space-2 label/value gap.
- **States**: default only.
- **Accessibility**: values include units in labels or captions.
- **Motion**: none.

### Evidence Log
- **Structure**: date, scenario, note, warning, evidence tag list.
- **Variants**: note, warning, metric.
- **Spacing**: --space-3 row padding.
- **States**: default, expanded by Streamlit table affordances.
- **Accessibility**: text labels, no icon-only status.
- **Motion**: none.

## 6. Motion & Interaction

### Timing

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 100-150ms | ease-out | Native control feedback |
| Standard | 200-300ms | ease-in-out | Optional panel transitions |
| Emphasis | 400-600ms | cubic-bezier(0.16, 1, 0.3, 1) | Not used in this dashboard |
| Scroll-driven | tied to scroll | linear | Not used |

### Rules

- Do not animate chart layout.
- Every interactive element relies on Streamlit native hover/focus behavior.
- Respect reduced-motion by avoiding decorative motion.

## 7. Depth & Surface

### Strategy

Choose ONE and commit: tonal-shift.

Surfaces use progressively lighter/darker shades. Borders are only for data separation. No decorative shadows.
