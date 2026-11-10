# Admin Panel

A Vue 3 + PrimeVue 5 single-page app built on the Sakai layout. It signs in
against the Laravel API (Sanctum tokens) and lists users.

## Requirements

Node 22.

## Commands

```sh
npm ci              # install the locked dependencies
npm run dev         # dev server; proxies /api to `php artisan serve` on :8000
npm run build       # production build into dist/
npm test            # Vitest component tests
npx playwright test # end-to-end tests against `vite preview`
```

## Signing in

Run `php artisan migrate` and `php artisan db:seed` in the Laravel app, then
sign in as `admin@example.com` / `password`.

## API origin

The app calls `/api/...` on its own origin. To reach an API on another origin,
set `VITE_API_BASE_URL` in `.env` (see `.env.example`), e.g.
`VITE_API_BASE_URL=https://api.example.com`.

## Licence

MIT, see `LICENSE.md`. The layout is vendored from `primefaces/sakai-vue@ec6b6ef53ad4fa7f2861277f50f2d9e236c40372` and `primefaces/sakai-assets@eaa70ece4cfa9aeb8f60b36dce5a422b6bae8003` (the assets repository is covered by the same Sakai MIT licence).
