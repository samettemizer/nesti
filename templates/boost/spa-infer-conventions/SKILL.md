---
name: spa-infer-conventions
description: "Analyze how a Vue 3 + PrimeVue single-page application is actually written and record its conventions as path-scoped rules."
license: MIT
provenance: "Adapted from laravel/boost v2.10.3 .ai/boost/skill/infer-conventions (MIT)"
---

# SPA Infer Conventions

Learn how this Vue single-page application writes its code, then record what you learn as durable, path-scoped rules other agents will read. You are documenting reality, not improving it.

## Ground Rules (read before you start)

- Consistency first. The codebase's majority style is the convention. Never judge it, never propose a "better" pattern, never record what the code should do. If the pages call axios directly everywhere, that is the rule, even if a service layer would be nicer.
- Skip what an active tool owns. Inspect the ESLint, Prettier and `vue-tsc` configuration first (`eslint.config.*`, `.eslintrc*`, `.prettierrc*`, `tsconfig*.json`, the `lint` / `type-check` / `build` scripts in `package.json`). Formatting and anything an enabled lint rule or the type-check enforces are tooling-owned: record nothing.
- Record decisions, not defaults. A consistent pattern earns a rule only when the app took one valid option where Vue, Vite or PrimeVue offered others, or when it would surprise a competent agent. create-vue, Vite and PrimeVue documented defaults steer nothing, so skip them: `<script setup lang="ts">` in a TypeScript create-vue app, the `@` → `src` alias, `createApp(App).use(router).mount('#app')`.
- Architecture choices are the gold. Record presence and deliberate absence: folder organisation (feature vs type folders, folder naming language), the page/component split, the API layer, the store style and who owns API data. Also record a consistent non-pattern, such as "pages call the HTTP client directly, no service layer", so the next agent matches the app's altitude instead of over-engineering.
- Evidence or silence. A convention needs at least 3 consistent examples and a rival under 20 % of sites to become a pattern. Both styles in meaningful numbers is a conflict: report the split, never record a winner.
- The recorded rule states the convention, nothing else. One or two imperative lines: this project does X, so do X here. No counts, ratios, current usage, file lists or example paths.

## Glob mapping

Globs are relative to the SPA root (the folder that holds `package.json`). Attach each rule to the most specific subtree that covers its evidence: `src/<dir>/**`, for example `src/stores/**`, `src/views/**`, `src/services/**`, `src/router/**`, `src/components/**`. Use `src/**` only for a truly app-wide convention and `e2e/**` for Playwright specs.
