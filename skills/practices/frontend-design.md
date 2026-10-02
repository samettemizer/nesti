---
title: Frontend Visual Design
slug: frontend-design
source: nesti://skills/practices/frontend-design.md
adapted_from: "local skill library: frontend-design (Apache-2.0)"
license: Apache-2.0 (practices/licenses/frontend-design.txt)
triggers: visual design, ui design, typography, color palette, design system, look and feel, redesign, visual hierarchy
---

# Frontend Visual Design

*Visual direction for a Nesti screen: where design decisions go, how to plan them, what to avoid. Adapted for Nesti from the `frontend-design` skill (Apache License 2.0, see practices/licenses/frontend-design.txt). Modified: retargeted to issue-driven Laravel 13 + Vue 3 + PrimeVue 5 screens; interactive and screenshot steps removed; PrimeVue theming placement added.*

## Where design decisions live in a Nesti app

- Build with PrimeVue 5 components, not hand-written markup: DataTable + Column, InputText / Select / DatePicker / Checkbox / InputNumber, Button, Dialog / ConfirmDialog, Toast / Message, Menubar / Breadcrumb / Tabs. Import per file (`import Button from 'primevue/button'`).
- The Aura preset stays exactly as registered in resources/js/app.js. Do not call `definePreset` and do not rewrite app.js for an ordinary issue. If the issue explicitly demands an app-wide theme change, the planner flags it as a risk in the plan instead of silently rewriting the setup.
- App-wide typography, colour CSS variables and keyframes go in resources/css/app.css (loaded by `@vite` in resources/views/app.blade.php; Tailwind 4 is imported there).
- Per-instance visuals: the `pt` (pass-through) prop for classes/attributes on a component's DOM sections, the `dt` prop for design tokens scoped to one instance (PrimeVue recommends it over `:deep()`), or a scoped `<style>` in the SFC.
- Layout (grid, flex, spacing, breakpoints) with Tailwind 4 utility classes. `tailwindcss-primeui` is not installed.
- Icons: PrimeIcons classes are already loaded (`icon="pi pi-check"` on Button, `<i class="pi pi-inbox" />`). No other icon library.
- Use Button `severity` (secondary, success, info, warn, help, danger, contrast) for emphasis rather than custom colours.
- A web font only when the issue's direction needs it: add an npm font package and `@import` it in resources/css/app.css. Adding an npm dependency is allowed; rewriting vite.config.js, vitest.config.js or playwright.config.js is not. Never load fonts or images from external network hosts at runtime.

```vue
<script setup>
import Button from 'primevue/button';
</script>

<template>
  <Button
    label="Publish"
    icon="pi pi-send"
    :dt="{ primary: { background: 'var(--app-accent)' } }"
    :pt="{ label: { class: 'tracking-tight' } }"
  />
</template>
```

## Ground the design in the subject matter

The GitLab issue is the brief. Infer from the issue text and the existing app the subject, the audience and the screen's primary job; never ask anyone. The subject's industry, materials and vernacular are where distinctive choices come from: a booking screen for a climbing gym looks different from a ledger for accountants. Use the issue's real nouns and data throughout, not lorem ipsum.

Distinguish two kinds of screen:
- App screens (most issues): the primary task area leads. A list screen opens with its DataTable and its primary action Button, a form with its fields. No marketing hero, no stats banner, no decorative intro.
- Public pages (landing, about, pricing): the hero is what viewers see first. Open with the most characteristic thing in the subject's world. A big number with a small label, supporting stats and a gradient accent is the default treatment; use it only when it is truly the best option.

## Planning the design

The planner writes no code; it puts a compact token plan into the implementation plan, and the coder follows it:
- Colour: 4–6 named hex values, each mapped to where it lives (a CSS variable in resources/css/app.css, a `dt` token, or a Button `severity`).
- Type: typefaces and their roles (display, body, data), with the scale.
- Layout: one-sentence concept plus a small ASCII sketch; state alignment and the mobile behaviour.
- Principles: two or three lines on what makes this screen specific to its subject.

There are no screenshots: self-critique happens in the plan. Before finalising, check every part against the issue's own words and against the calibration list; if a part is what you would produce for any similar screen, revise it and note why.

When coding, watch selector specificity: a scoped class and an element selector can cancel each other's padding or margin. Prefer `pt` and Tailwind utilities over overriding PrimeVue's internal classes.

## Calibration: generated-looking defaults

Generated design currently clusters around these traits:
1. a warm cream background (near #F4F1EA) with a high-contrast serif display and a terracotta accent (near #D97757);
2. a near-black background with a single acid-green or vermilion accent;
3. a broadsheet layout with hairline rules, zero border-radius and dense newspaper columns;
4. the SaaS-card kit: content chopped into identical rounded cards, one radius on everything, the same soft grey shadow (rgba(0,0,0,.1)) under each, gradient washes as decoration;
5. template chrome regardless of subject: tracked-out all-caps eyebrows above every heading; meta strings joined with middle dots ('A · B · C'); 'WORD — fragment' labels; tinted near-black (#0B0B0B, #111) instead of black; a monospace face for small data labels; '→' appended to link and button text.

Each is legitimate for some briefs, but they are defaults, not choices. Where the issue pins down a visual direction, follow it exactly; the issue's own words win, including when it asks for one of these looks. Where it leaves an axis free, do not spend that freedom on a default.

## Typography and structure

Typography carries the personality. One family or two; if two, make them clearly distinct. Choose deliberately rather than by habit, and set a clear type scale with intentional weights and spacing (define it once as CSS variables in resources/css/app.css). A headline's type treatment is part of the design, not a neutral vehicle.

Keep line length under 80 characters (Tailwind `max-w-prose` or a `ch`-based max width). Serif body text may run slightly longer and needs slightly more line-height than sans-serif.

Avoid the commonest tells of a generated page:
- accenting a single word in a headline (one word italic, bold or coloured);
- all-caps labels;
- unnecessary labels above content.

Visual structure is information. Borders, numbering, dividers and labels must encode something about the content, not decorate it. Numbered markers (01 / 02 / 03) only when the content really is a sequence, such as a stepped process or a timeline. In app screens, prefer PrimeVue's own structure (DataTable columns, Tabs, Panel headers) over invented chrome.

## Motion

Use motion nobody triggered sparingly, only to draw attention. One orchestrated moment beats scattered effects; fade-and-slide-up on every section and hover transitions on every card read as generated. Motion that answers a person's action (opening a Dialog, expanding a row, confirming with a Toast) is welcome when it shows what changed; PrimeVue components already animate these.

For a scroll reveal use the `v-animateonscroll` directive with the change's own keyframe classes, defined in resources/css/app.css or the SFC's `<style>`; the classes in PrimeVue's example come from tailwindcss-primeui, which is not installed. Always respect reduced motion:

```css
@keyframes reveal-up { from { opacity: 0; transform: translateY(1rem); } to { opacity: 1; transform: none; } }
.reveal-enter { animation: reveal-up 400ms ease-out both; }
@media (prefers-reduced-motion: reduce) {
  .reveal-enter { animation: none; }
}
```

```vue
<script setup>
import AnimateOnScroll from 'primevue/animateonscroll';

const vAnimateonscroll = AnimateOnScroll; // local registration; app.js registers nothing globally
</script>

<template>
  <section v-animateonscroll="{ enterClass: 'reveal-enter' }">...</section>
</template>
```

## Restraint

Spend boldness in one place. Let one element be memorable, keep everything around it quiet, and cut decoration that does not serve the issue. Build to a quality floor without announcing it: responsive down to mobile, visible keyboard focus, reduced motion respected, sufficient contrast, a harmonious palette. Before finishing, remove one accessory.

## Writing in the interface

Words exist to make the screen easier to understand and use. Bring the same minimalism to copy as to spacing and colour.

Write from the user's perspective: name things by what users understand, not by how the system is built. A user manages notifications, not webhook config. Describe plainly what something does; specific beats clever.

Use active voice. A button says exactly what happens: "Save changes", not "Submit". An action keeps its name through the flow: a Button labelled "Publish" leads to a Toast whose summary says "Published" (`toast.add({ severity: 'success', summary: 'Published', life: 3000 })`).

Failure and emptiness are moments for direction. Errors (Message, Toast with `severity: 'error'`, validation text under a field) say what went wrong and how to fix it, without apology or vagueness. An empty DataTable's empty message invites the next action.

Keep the tone plain: sentence case, plain verbs, no filler. Each written element does one job.

## Testing a design change

- Vitest asserts copy, props and emitted events (`wrapper.text()`, `wrapper.emitted()`), never CSS classes, colours or PrimeVue's internal DOM shape. Mount with the PrimeVue plugin and Aura preset in `global.plugins`.
- Playwright asserts what a user sees: `getByRole('button', { name: 'Publish' })`, `getByText('Published', { exact: true })`, `getByTestId(...)`. Seed data through DatabaseSeeder or create it in the spec.
- Styling itself is not unit-tested. A purely visual change still ships a spec for the behaviour or copy the issue names.
