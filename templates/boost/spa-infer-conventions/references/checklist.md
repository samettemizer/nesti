# Detection Checklist (Vue SPA)

Every dimension here is a genuine fork: Vue, Vite and PrimeVue offer two or more valid approaches, the app's choice changes what the next agent writes, and no active project tool can pick for you. Each item gives the fork, then a hint (a grep or dir to spot which side the app takes). Hints are only a start. Read the matched files, never record on a raw count. Rows tagged (architecture) are the highest-signal, so record presence and deliberate absence.

---

## K. Entry & app shell

1. Plugin registration site: everything in `src/main.*` vs split into `src/plugins/*`.
   - Hint: read `src/main.*`; `ls src/plugins`.
2. PrimeVue configuration: styled preset via `@primeuix/themes` / `definePreset` vs unstyled + pass-through; dark-mode selector; locale.
   - Hint: grep `definePreset`, `unstyled`, `pt:`, `darkModeSelector`, `locale` near `app.use(PrimeVue`.
3. PrimeVue import style: per-file `primevue/<name>` imports vs global `app.component` vs an `unplugin-vue-components` resolver.
   - Hint: grep `from 'primevue/` in `src/`; grep `app.component(` in `src/main.*`; check `vite.config.*` for `PrimeVueResolver`.
4. Global services/directives: `ToastService` / `ConfirmationService` / `Tooltip` registered and used through `useToast` / `useConfirm`.
   - Hint: grep `ToastService`, `ConfirmationService`, `useToast(`, `useConfirm(`, `v-tooltip`.

## L. Components & composition

5. SFC style: `<script setup lang="ts">` vs `<script setup>` in JS vs the Options API.
   - Hint: grep `<script setup`, `defineComponent(`, `export default {` in `src/**/*.vue`.
6. Props/emits/model typing: type-based `defineProps<…>()` vs runtime declarations; `withDefaults`; `defineModel` vs `modelValue` + `update:modelValue`.
   - Hint: grep `defineProps<`, `defineProps({`, `withDefaults(`, `defineModel(`, `update:modelValue`.
7. Composables: location, `useX` naming and return shape (refs object vs reactive vs functions).
   - Hint: `ls src/composables`; grep `export function use`, `export const use`.
8. Folder & file naming (architecture): naming language and casing (English vs other-language names such as `sayfalar` / `depolar`; PascalCase vs kebab-case files); feature folders vs type folders.
   - Hint: `ls src` and its subfolders; compare file name casing in `src/components`.
9. Page vs component split (architecture): route-level pages in `src/views` / `src/pages` vs components used directly as routes.
   - Hint: `ls src/views src/pages`; read which components the router imports.

## M. Routing & state

10. Router module shape: one routes array vs per-feature route modules; lazy `() => import()` vs static imports.
    - Hint: `ls src/router`; grep `() => import(` in the router files.
11. Navigation guards & auth: `router.beforeEach` with a store check vs route `meta` flags vs per-page checks.
    - Hint: grep `beforeEach`, `meta:`, `requiresAuth` in `src/router`.
12. Pinia store style: setup stores vs options stores; naming (`useXStore` vs localized names); folder.
    - Hint: `ls src/stores`; grep `defineStore(` and whether its second argument is a function or an object.
13. State ownership (architecture): API data held in stores vs fetched and kept in pages or composables.
    - Hint: compare where HTTP calls are made: stores, composables or page components.

## N. API layer & types

14. HTTP client: one configured axios instance vs `fetch` vs ad-hoc axios calls.
    - Hint: grep `axios.create(`, `import axios`, `fetch(` in `src/`.
15. Endpoint organisation (architecture): per-resource service modules vs one services file vs inline calls in components.
    - Hint: `ls src/services src/api`; grep `.get('/`, `.post('/` in `src/views` and `src/components`.
16. Auth token & error handling: request/response interceptors, 401 → logout/redirect, errors → toast.
    - Hint: grep `interceptors.request`, `interceptors.response`, `401`, `Authorization` in `src/`.
17. Types location & API response typing: shared `src/types` vs co-located types; typed Laravel `data` / `meta` envelopes vs `any`.
    - Hint: `ls src/types`; grep `interface .*Response`, `data:`, `meta:`, `: any` in the API layer.

## O. Styling, forms & UX

18. Styling approach: global CSS vs scoped `<style scoped>` vs a utility framework (Tailwind, PrimeFlex).
    - Hint: grep `<style scoped`, `@tailwind`, `primeflex` in `src/` and `package.json`.
19. Forms & validation: PrimeVue Forms vs vee-validate / zod vs manual refs with 422 error mapping.
    - Hint: grep `@primevue/forms`, `useForm(`, `zod`, `errors.value`, `422` in `src/`.
20. User feedback: Toast vs Message vs inline text; `ConfirmDialog` for destructive actions.
    - Hint: grep `toast.add(`, `<Message`, `confirm.require(` in `src/`.
21. UI language / i18n: hard-coded strings in one language vs `vue-i18n` keys.
    - Hint: grep `vue-i18n`, `$t(`, `useI18n(`; read a few templates for the UI language.

## P. Testing & checks

22. Component tests: Vitest presence, spec location (`__tests__` vs co-located) and mount helpers.
    - Hint: `package.json` scripts and devDependencies; find `*.spec.*` / `*.test.*` under `src/`; grep `mount(`, `render(`.
23. E2E: Playwright presence; API stubbed with `page.route` vs a real backend.
    - Hint: `ls e2e`; grep `page.route(` in `e2e/`.
24. Type-check gate: `vue-tsc --noEmit` in the build script; `strict` in `tsconfig`.
    - Hint: read the `build` / `type-check` scripts in `package.json` and `compilerOptions.strict` in `tsconfig*.json`.

---

Genuine forks only. Give each dimension exactly one verdict: pattern, conflict, default, no-signal, tooling-owned, or already-recorded. The rows tagged (architecture) are where the highest-value rules come from.
