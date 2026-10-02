---
title: Minimalist UI Direction
slug: minimalist-ui
source: nesti://skills/practices/minimalist-ui.md
adapted_from: "local skill library: minimalist-ui (origin unrecorded)"
triggers: minimalist, minimal ui, clean interface, editorial design, monochrome, flat design
---

# Minimalist UI Direction

_Adapted for Nesti from the local skill library's minimalist-ui (origin unrecorded). Apply only when the issue asks for a minimal/editorial look; otherwise frontend-design governs._

## Mapping the direction onto PrimeVue 5

Warm monochrome canvas, near-black text, 1px `#EAEAEA` lines, flat surfaces, scarce pastels, serif headings over a sans body, wide whitespace. Use PrimeVue 5 components; never hand-roll a table, form, dialog or accordion.

Restyle PrimeVue through tokens or `pt`:
- Feature-wide: `class="minimal"` on each restyled page component's root element; `.minimal` in `resources/css/app.css` sets CSS variables from the components' Design Tokens tables, inherited by every component inside with hover states intact.
- One instance: `pt` keyed by a Pass Through section (a string is a class, `{ style: { ... } }` an inline style), or scoped `dt` shaped like a preset's component layer: `<Card :dt="{ root: { shadow: 'none' } }">`.
- Dialog and Toast render outside `.minimal`: on the instance, Dialog `pt.root` / Toast `pt.message` = `{ style: { boxShadow: 'none', border: '1px solid var(--min-border)' } }`.

| Element | PrimeVue 5 | Treatment |
|---|---|---|
| Card, bento tile | `Card`; `Panel` if it needs a header | flat, 10px radius, `pt.root` style `border: 1px solid var(--min-border)` |
| Primary action | `Button severity="contrast"` | `#111111`, hover `#333333`, 6px radius |
| Secondary action | `Button severity="secondary" variant="outlined"` or `variant="text"` | never `raised` |
| Status | `Tag` with `severity`, `rounded` | severities remapped to pastels |
| FAQ | `Accordion` > `AccordionPanel` > `AccordionHeader` + `AccordionContent` | transparent, 1px dividers, `#toggleicon="{ active }"` with `pi pi-minus` / `pi pi-plus` |
| Table | `DataTable` + `Column` | no `showGridlines` or `stripedRows`; `size="small"` if dense |
| Shortcut | plain `<kbd>` | styled in app.css |
| Icon | `<i class="pi pi-check" />`, Button `icon="pi pi-check"` | already loaded |

## Palette

Colour marks meaning; pastels only on tags, inline code, small icon backgrounds. Append to `resources/css/app.css`, keeping every existing line (Tailwind import first). No preset, no `app.js` change.

```css
:root {
    --min-canvas: #F7F6F3;  /* or #FFFFFF, #FBFBFA */
    --min-surface: #FFFFFF; /* cards; or #F9F9F8 */
    --min-border: #EAEAEA;  /* or rgba(0, 0, 0, 0.06) */
    --min-ink: #111111;     /* or #2F3437; never #000000 */
    --min-muted: #787774;
    --min-red-bg: #FDEBEC; --min-red-text: #9F2F2D;
    --min-blue-bg: #E1F3FE; --min-blue-text: #1F6C9F;
    --min-green-bg: #EDF3EC; --min-green-text: #346538;
    --min-yellow-bg: #FBF3DB; --min-yellow-text: #956400;
}
.minimal {
    --p-card-background: var(--min-surface); --p-card-shadow: none;
    --p-card-border-radius: 10px; --p-card-body-padding: 2rem;
    --p-panel-border-color: var(--min-border); --p-panel-border-radius: 10px;
    --p-button-border-radius: 6px;
    --p-button-contrast-background: var(--min-ink); --p-button-contrast-border-color: var(--min-ink);
    --p-button-contrast-hover-background: #333333; --p-button-contrast-hover-border-color: #333333;
    --p-tag-danger-background: var(--min-red-bg); --p-tag-danger-color: var(--min-red-text);
    --p-tag-info-background: var(--min-blue-bg); --p-tag-info-color: var(--min-blue-text);
    --p-tag-success-background: var(--min-green-bg); --p-tag-success-color: var(--min-green-text);
    --p-tag-warn-background: var(--min-yellow-bg); --p-tag-warn-color: var(--min-yellow-text);
    --p-accordion-panel-border-color: var(--min-border);
    --p-accordion-header-background: transparent; --p-accordion-header-hover-background: transparent;
    --p-accordion-header-active-background: transparent; --p-accordion-content-background: transparent;
    --p-datatable-header-cell-background: transparent;
    --p-datatable-header-cell-border-color: var(--min-border); --p-datatable-body-cell-border-color: var(--min-border);
}
```

## Typography

Serif display over plain sans carries the hierarchy; local faces only, no CDN fonts or font package.

```css
:root {
    --min-sans: 'SF Pro Display', 'Geist Sans', 'Helvetica Neue', 'Switzer', sans-serif;
    --min-serif: 'Lyon Text', 'Newsreader', 'Playfair Display', 'Instrument Serif', serif;
    --min-mono: 'Geist Mono', 'SF Mono', 'JetBrains Mono', monospace;
}
.minimal { background: var(--min-canvas); color: var(--min-ink); font-family: var(--min-sans); line-height: 1.6; }
.minimal h1, .minimal h2, .minimal blockquote {
    font-family: var(--min-serif); letter-spacing: -0.03em; line-height: 1.1;
}
.minimal code { font-family: var(--min-mono); }
.minimal kbd { font-family: var(--min-mono); border: 1px solid var(--min-border); border-radius: 4px; background: var(--min-canvas); }
.min-muted { color: var(--min-muted); }
.min-tag { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
```

Secondary text: `.min-muted`. Tags: `:pt="{ root: 'min-tag' }"`.

## Banned defaults

- Inter, Roboto, Open Sans.
- Another icon library (Lucide, Feather, Heroicons, Phosphor, Radix): PrimeIcons `pi pi-*` only.
- Heavy shadows: no `shadow-md` / `shadow-lg` / `shadow-xl`, no PrimeVue elevation (`--p-card-shadow: none`, no Button `raised`, Dialog/Toast shadow off via `pt`).
- Primary-coloured backgrounds on large elements or sections.
- Gradients, neon, glassmorphism (a faint navbar blur excepted).
- `rounded-full` or the `rounded` prop on cards, containers, primary buttons; pills are for Tags.
- Emojis anywhere, including alt text: use a `pi` icon or an inline SVG.
- "John Doe", "Acme Corp", "Lorem Ipsum": write contextual copy; demo rows come from seeders with Faker.
- "Elevate", "Seamless", "Unleash", "Next-Gen", "Game-changer", "Delve": write plainly.
- Runtime network assets: placeholder images, CDN fonts, remote icons.

## Execution in a Nesti change

- Plan (no code): per `.vue` file, its PrimeVue components, where `class="minimal"` sits, any per-instance `pt`/`dt`; the `app.css` additions; Vitest and Playwright cases by behaviour. A pure restyle is frontend-only: no PHP.
- Code: `resources/css/app.css` whole with existing lines intact; `<script setup>` SFCs importing per file (`import Card from 'primevue/card'`). In `app.js` only the usual `app.component(...)` registration of a new page component; never touch the PrimeVue/Aura setup, never `definePreset`, no npm package for fonts, icons or animation.
- Vitest: mount with PrimeVue + Aura; assert text, props, emitted events, never classes, styles or colours. With `v-animateonscroll`, `vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} })` before `mount` (jsdom lacks it).
- Playwright: `getByRole`, `getByTestId`, `getByText(..., { exact: true })` on seeded or spec-created data; no style assertions or animation waits (`opacity: 0` counts as visible).

## Layout with Tailwind 4

Tailwind does layout only; colours, borders, radii and shadows of PrimeVue internals go through the token block or `pt`, never utilities forced onto inner elements.
- Whitespace first: `py-24` between sections, `py-32` for a hero.
- Width: `max-w-4xl mx-auto px-6` for reading columns, `max-w-5xl` for grids.
- Bento grid: asymmetric, e.g. `grid grid-cols-1 md:grid-cols-3 gap-4`, one tile `md:col-span-2`, one `md:row-span-2`; placement classes may sit on a component root (`<Card class="md:col-span-2">`).
- Card padding is the `--p-card-body-padding` token (24 to 40px); do not pad again inside.
- Whitespace and type supply depth: no background textures, radial light spots or line patterns.

## Motion

Quiet, and only when the issue asks for it. Scroll entry uses PrimeVue's `v-animateonscroll` with the change's own keyframes: `tailwindcss-primeui` is not installed, so the doc's `animate-enter` / `fade-in-*` classes do not exist. Register the directive locally, never in `app.js`:

```vue
<script setup>
import AnimateOnScroll from 'primevue/animateonscroll';
const vAnimateonscroll = AnimateOnScroll;
defineProps({ items: { type: Array, required: true } });
</script>
<template>
    <div v-for="(item, index) in items" :key="item.id"
        v-animateonscroll="{ enterClass: 'min-reveal' }" :style="{ '--min-index': Math.min(index, 6) }">
        {{ item.title }}
    </div>
</template>
```

```css
@keyframes min-rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
.min-reveal { animation: min-rise 600ms cubic-bezier(0.16, 1, 0.3, 1) both; animation-delay: calc(var(--min-index, 0) * 80ms); }
.min-press:active { transform: scale(0.98); }
@media (prefers-reduced-motion: reduce) {
    .min-reveal { animation-duration: 1ms; animation-delay: 0ms; }
    .min-press:active { transform: none; }
}
```

- No `leaveClass`: content must not vanish when scrolled past.
- Animate `transform` and `opacity` only; `will-change` only while animating. Buttons may take `:pt="{ root: 'min-press' }"`.
- No ambient background blobs, parallax or `window` scroll listeners on app screens.

## Imagery

- No external placeholder services (picsum.photos, unsplash) or remote images: the app and the Playwright run must not depend on the network.
- Use an image already in `public/` by root-relative path, or none. Illustrations are inline SVG: a monochrome line drawing (`stroke="#111111"`) plus one offset shape filled with a pastel; decorative SVGs get `aria-hidden="true"`.
- Photos supplied by the issue: desaturated, warm, no overlays over content.
- Faux-OS window chrome only when the issue asks for a software mockup: 1px `var(--min-border)` frame, 10px radius, white top bar with three 10px `#EAEAEA` circles, no shadow.
