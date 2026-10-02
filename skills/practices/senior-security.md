---
title: Application Security Engineering
slug: senior-security
source: nesti://skills/practices/senior-security.md
adapted_from: https://github.com/alirezarezvani/claude-skills/tree/main/engineering-team/senior-security
license: MIT (practices/licenses/senior-security.txt)
triggers: security review, threat model, vulnerability, owasp, sql injection, xss, secure coding, attack surface, mass assignment, sensitive data
---

# Application Security Engineering

*Security reference for planning and coding a Nesti change: the controls every Laravel 13 + Vue 3 + PrimeVue 5 change carries, the pattern to write, and the test that proves it. Adapted for Nesti from alirezarezvani/claude-skills `senior-security` (MIT, Copyright (c) 2025 Alireza Rezvani; see practices/licenses/senior-security.txt).*

## Non-negotiables in every Nesti change

1. **Authenticate and authorize every route that reads or changes user-owned data**: `auth` (web) or `auth:sanctum` (/api) plus a policy `app/Policies/<Model>Policy.php` (auto-discovered), enforced by `Gate::authorize('update', $task)`, `->can('update', 'task')` on the route, or a FormRequest `authorize()`. No users in the app and none requested: do not invent auth; note "endpoints are public" under Risks or ambiguities.
2. **Validate every input** in FormRequest `rules()` or `$request->validate([...])`; persist only `$request->validated()` or `$request->safe()->only([...])`, never `$request->all()`.
3. **Mass assignment**: list writable columns in `$fillable`; never `$guarded = []` or `#[Unguarded]`. Owner, role and status columns (`user_id`, `is_admin`) are set server-side.
4. **Whitelist output**: API responses go through a JsonResource whose `toArray()` names every field (never `parent::toArray($request)`); `password`, `remember_token` and tokens stay in `$hidden`.
5. **SQL**: Eloquent / query builder bindings only. Never interpolate input into `whereRaw`, `selectRaw`, `orderByRaw` or `DB::select`; sort columns come from a `Rule::in([...])` whitelist (PDO cannot bind column names).
6. **XSS**: Blade `{{ }}` and Vue text interpolation only; no `{!! !!}` or `v-html` with user data; never echo user data into the Vue-mounted `#app` markup.
7. **Secrets** live in `.env`, are read in `config/*.php` with `env()`, and everywhere else with `config('services.x.key')`.
8. **Passwords**: `Hash::make` / `Hash::check` or the `hashed` cast. **Sensitive columns**: the `encrypted` cast on a TEXT column.
9. **Throttle** login, registration, password reset and write endpoints (`throttle:<limiter>`).
10. **Errors**: no exception text, SQL or stack traces in responses; `APP_DEBUG=false` outside local.
11. **Prove it in PHPUnit**: 403 for another user's record, 401 for a guest on /api (`getJson`), 422 for invalid input.

## OWASP Top 10 → Laravel / Vue controls

| OWASP 2021 | Typical defect in this stack | Control | Test |
|---|---|---|---|
| A01 Broken access control | `/api/tasks/{task}` serves any id; index lists all users' rows; client `user_id` trusted | Policy + `Gate::authorize`/`can`; `$request->user()->tasks()`; `scopeBindings()` | `assertForbidden()` as a second user |
| A02 Cryptographic failures | plain-text tokens or PII; md5/sha1 "hashing"; base64 "encryption" | `encrypted` cast, `Crypt::encryptString`, `Hash::make` / `hashed` cast; `APP_KEY` only in `.env` | `assertDatabaseMissing` plain value |
| A03 Injection | interpolated raw SQL; user-chosen `orderBy` column; `{!! !!}` / `v-html` | bindings; `Rule::in` sort columns; escaped output | 422 on `?sort=password`; Vitest shows markup as text |
| A04 Insecure design | rule enforced only in the Vue form | STRIDE pass; the server enforces every UI rule | assert the rule over HTTP |
| A05 Security misconfiguration | `APP_DEBUG=true`; `env()` in app code; exception text in JSON | `config()` access; the exception handler renders errors; header middleware | `assertHeader(...)` |
| A06 Vulnerable components | unmaintained packages; CDN scripts | add a dependency only when truly needed; keep pinned versions; no runtime CDN assets | none |
| A07 Authentication failures | brute force, session fixation, weak passwords | `Auth::attempt` + `$request->session()->regenerate()`; `throttle:login`; `Password::min(8)` | `assertTooManyRequests()` |
| A08 Integrity failures | trusted hidden fields or client totals; forgeable links | recompute server-side; `URL::temporarySignedRoute` + `signed` middleware | tampered value ignored |
| A09 Logging failures | no trace of deletes; secrets in logs | `Log::info('...', ['user_id' => ..., 'task_id' => ...])`, ids only | none |
| A10 SSRF | server fetches a user-supplied URL | `url:http,https` + host allowlist from config; `Http::timeout(3)` | `Http::fake()` + `Http::preventStrayRequests()` |

## Threat modeling in the plan (STRIDE)

For every new route, model, upload or form, the planner asks the six questions below without tools or diagrams. Each real finding becomes one line under **8. Risks or ambiguities** in the form `threat → control → test`, and its test is named under **7. Test cases**.

| STRIDE | Question | Laravel / Vue control |
|---|---|---|
| Spoofing | Can an unauthenticated request reach this code? | `auth` / `auth:sanctum`; session regenerate on login; throttled login |
| Tampering | Which request fields could change data the user must not change (owner, price, role, status)? | FormRequest rules, `$fillable`, server-set values, CSRF, signed URLs |
| Repudiation | Does a destructive or disputed action leave a trace? | `Log::info` with actor and record ids; an audit column via a new migration only if the issue asks |
| Information disclosure | Which fields leave the server in JSON, Blade, logs or errors? | JsonResource field list, `$hidden`, generic errors, `encrypted` cast |
| Denial of service | What can one client repeat or enlarge without bound? | `throttle`, `max:` rules, `File::types(...)->max(...)`, `paginate()` not `get()` |
| Elevation of privilege | Can a normal user reach an admin action or another user's record? | a policy method per action; roles never read from the request |

A security issue is fixed test-first: first a failing Feature test that demonstrates the vulnerability, then the fix that turns it green.

## Pattern: SQL injection

```php
// Insecure: input becomes SQL text.
$tasks = DB::select("select * from tasks where title like '%{$request->q}%'");
$tasks = Task::query()->orderByRaw($request->input('sort'))->get();

// Secure: values are bound, the column is whitelisted.
$validated = $request->validate([
    'q' => ['nullable', 'string', 'max:100'],
    'sort' => ['nullable', Rule::in(['title', 'due_date', 'created_at'])],
    'direction' => ['nullable', Rule::in(['asc', 'desc'])],
]);

$tasks = $request->user()->tasks()
    ->when($validated['q'] ?? null, function ($query, string $q) {
        $query->where('title', 'like', '%'.$q.'%');
    })
    ->orderBy($validated['sort'] ?? 'created_at', $validated['direction'] ?? 'desc')
    ->paginate(20);
```

- Raw expressions are allowed only with placeholders: `->whereRaw('price > ?', [$min])`, `DB::select('select * from tasks where id = ?', [$id])`.
- `DB::unprepared` never sees a user value. Raw DDL is forbidden anyway (the suite runs on SQLite).
- Cast values to their real type before querying; MySQL compares a string with an integer by casting the string to a number.

## Pattern: mass assignment

```php
// Insecure: a client posting user_id or is_admin rewrites them.
class Task extends Model
{
    protected $guarded = [];
}
Task::create($request->all());
```

```php
namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Task extends Model
{
    use HasFactory;

    protected $fillable = ['title', 'description', 'due_date'];

    protected function casts(): array
    {
        return ['due_date' => 'date'];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}

// Controller: user_id comes from the relationship, the rest from validated input.
$task = $request->user()->tasks()->create($request->validated());
```

- Laravel 13 also offers the `#[Fillable([...])]` / `#[Hidden([...])]` attribute form; follow the style the repository's models already use.
- Never put a column in `$fillable` only because a form sends it. `role`, `is_admin`, `user_id`, `status` and price fields are assigned explicitly after an authorization check.

## Pattern: IDOR with route model binding and a policy

```php
namespace App\Policies;

use App\Models\Task;
use App\Models\User;

class TaskPolicy
{
    public function view(User $user, Task $task): bool
    {
        return $user->id === $task->user_id;
    }

    public function update(User $user, Task $task): bool
    {
        return $user->id === $task->user_id;
    }

    public function delete(User $user, Task $task): bool
    {
        return $user->id === $task->user_id;
    }
}
```

```php
// routes/api.php (served under /api)
Route::middleware('auth:sanctum')->group(function () {
    Route::get('/tasks', [TaskController::class, 'index']);
    Route::post('/tasks', [TaskController::class, 'store']);
    Route::get('/tasks/{task}', [TaskController::class, 'show'])->can('view', 'task');
    Route::put('/tasks/{task}', [TaskController::class, 'update'])->can('update', 'task');
    Route::delete('/tasks/{task}', [TaskController::class, 'destroy'])->can('delete', 'task');
});
```

- `index` returns only the caller's rows: `TaskResource::collection($request->user()->tasks()->latest()->paginate(20))`.
- Foreign keys sent by the client must belong to the caller: `Rule::exists('projects', 'id')->where(fn (Builder $query) => $query->where('user_id', $this->user()->id))` with `Illuminate\Database\Query\Builder`.
- Nested routes (`/projects/{project}/tasks/{task}`) use `->scopeBindings()` so a task of another project returns 404.
- Inside a controller use `Gate::authorize('update', $task)` when the route has no `can`; one enforcement point per action is enough, zero is a defect.
- To hide existence, the policy may return `Response::denyAsNotFound()`; the test then expects `assertNotFound()`.

## Pattern: XSS in Blade and Vue

- Blade `{{ $comment->body }}` runs through `htmlspecialchars`; `{!! $comment->body !!}` does not and is never used with user data. Pass PHP data to inline JavaScript with `{{ Js::from($data) }}`, not hand-built JSON.
- Vue text interpolation and attribute bindings escape; `v-html` does not. If the issue needs user-formatted text, render it as text with Tailwind `whitespace-pre-line`; do not add an HTML sanitizer the issue does not name.
- Nesti-specific: Vue compiles the markup inside `<div id="app">` of `resources/views/app.blade.php` at runtime (the full `vue.esm-bundler.js` build). Anything Blade echoes there becomes a Vue template, so a stored value containing `{{ ... }}` survives `htmlspecialchars` and runs as a Vue expression. Keep `#app` to static component tags; components load user data from JSON endpoints.
- User-supplied links: validate with `url:http,https` server-side before rendering them in `:href`, which blocks `javascript:` URLs.

```vue
<script setup>
defineProps({
    comment: { type: Object, required: true },
});
</script>

<template>
    <!-- Escaped. Never: <p v-html="comment.body"></p> -->
    <p data-testid="comment-body" class="whitespace-pre-line">{{ comment.body }}</p>
</template>
```

## Pattern: file uploads

```php
// FormRequest rules(): content-based type check plus size limit.
return [
    'attachment' => ['required', File::types(['pdf', 'png', 'jpg'])->max('5mb')],
    'avatar' => ['nullable', File::image()->max('2mb')], // SVG is rejected by default (XSS)
];

// Controller: random name on the private local disk; the client name is display text only.
$file = $request->file('attachment');
$document = $request->user()->documents()->create([
    'path' => $file->store('attachments', 'local'),
    'original_name' => $file->getClientOriginalName(),
]);
```

- Never `storeAs(..., $file->getClientOriginalName())` and never trust `getClientOriginalExtension()`; both are client-controlled. Use `hashName()` / `extension()` when a name is needed.
- `extensions:jpg,png` alone is not validation; combine it with `mimes` / `mimetypes` or use `File::types()`.
- The `local` disk stores under `storage/app/private`. Serve files through an authorized route that returns `Storage::download($document->path, $document->original_name)`, or a `URL::temporarySignedRoute` link. Use the `public` disk only for files every visitor may see.
- PrimeVue `FileUpload` `accept`, `:maxFileSize` and `:fileLimit` are UX hints, not controls; the FormRequest is the gate.
- Tests: `Storage::fake('local')`, `$file = UploadedFile::fake()->create('report.pdf', 100, 'application/pdf')`, then `Storage::disk('local')->assertExists('attachments/'.$file->hashName())`; an `.exe` or oversized file gets `assertUnprocessable()`.

## Pattern: passwords and login

```php
public function store(Request $request): RedirectResponse
{
    $credentials = $request->validate([
        'email' => ['required', 'email'],
        'password' => ['required', 'string'],
    ]);

    if (! Auth::attempt($credentials)) {
        return back()->withErrors([
            'email' => 'The provided credentials do not match our records.',
        ])->onlyInput('email');
    }

    $request->session()->regenerate();

    return redirect()->intended('/');
}
```

- Store passwords with `Hash::make($validated['password'])` or assign the plain validated value to a `password` attribute cast `hashed`; verify with `Hash::check` or `Auth::attempt`. Never compare hashes yourself.
- Registration and reset rules: `['required', 'confirmed', Password::min(8)]`. Do not use `uncompromised()`; it calls an external service the sandbox cannot reach.
- One generic message for an unknown email and a wrong password (no user enumeration).
- Logout: `Auth::logout()`, `$request->session()->invalidate()`, `$request->session()->regenerateToken()`.
- Throttle: in `AppServiceProvider::boot()`, `RateLimiter::for('login', fn (Request $request) => Limit::perMinute(5)->by($request->input('email').'|'.$request->ip()));`, and on the route `->middleware('throttle:login')`. Exceeding it returns 429.
- API tokens: Sanctum `createToken('name', ['tasks:read'])->plainTextToken`, shown once; check abilities with `tokenCan`. The User model needs `Laravel\Sanctum\HasApiTokens`. Do not build JWT, TOTP or 2FA by hand.

## Pattern: leaking attributes through resources, logs and errors

```php
// Insecure: every column, including ones added later.
return $user;
return response()->json($user->toArray());

// Secure: explicit fields; owner-only data behind a condition.
class UserResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'email' => $this->when($request->user()?->is($this->resource), $this->email),
            'created_at' => $this->created_at,
        ];
    }
}
```

- `$hidden` covers `password`, `remember_token` and any token or secret column; resources are still the whitelist.
- Load relations explicitly and expose them with `whenLoaded('posts')`, so a nested model never leaks its own columns unfiltered.
- Logs: ids and outcomes only, e.g. `Log::info('Task deleted', ['task_id' => $task->id, 'user_id' => $request->user()->id])`. Never log `$request->all()`, passwords, tokens, or full card or ID numbers.
- Errors: do not catch an exception to return `$e->getMessage()`; let the handler render it (generic when `APP_DEBUG=false`). For expected refusals use `abort(403)` / `abort(404)`.
- Test with `assertJsonMissingPath('data.password')` and `assertJsonMissingPath('data.email')` as a different user.

## Pattern: CSRF in the Vue frontend

- `PreventRequestForgery` protects the `web` group. It accepts a same-origin `Sec-Fetch-Site` header, which the Laravel docs say is only sent over HTTPS; otherwise it validates the CSRF token from `_token`, `X-CSRF-TOKEN` or `X-XSRF-TOKEN`. Playwright drives plain-HTTP `http://127.0.0.1:8000`, so always send the token.
- `resources/views/app.blade.php` already renders `<meta name="csrf-token" content="{{ csrf_token() }}">`. Send it on every state-changing web request:

```js
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ?? '';

async function saveTask(form) {
    const response = await fetch('/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            'X-CSRF-TOKEN': csrfToken,
        },
        body: JSON.stringify(form),
    });

    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }

    return response.json();
}
```

- `/api` routes are stateless. Cookie-based Sanctum SPA auth on `/api` requires `$middleware->statefulApi()` in `bootstrap/app.php`, which a Nesti change must not edit. Unless that call already exists, session-authenticated UI calls go to `web` routes; when it exists, request `/sanctum/csrf-cookie` once and send the `X-XSRF-TOKEN` header.
- Never add a route to the `preventRequestForgery(except: [...])` list to make a test pass.
- Vitest: stub the request with `vi.stubGlobal('fetch', vi.fn(...))`; the test document has no meta tag, hence the `?.` fallback.

## Testing security behaviour

```php
namespace Tests\Feature;

use App\Models\Task;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TaskSecurityTest extends TestCase
{
    use RefreshDatabase;

    public function test_guest_receives_401(): void
    {
        $task = Task::factory()->create();

        $this->getJson("/api/tasks/{$task->id}")->assertUnauthorized();
    }

    public function test_user_cannot_update_another_users_task(): void
    {
        $task = Task::factory()->create();

        $this->actingAs(User::factory()->create())
            ->putJson("/api/tasks/{$task->id}", ['title' => 'Hijacked'])
            ->assertForbidden();

        $this->assertDatabaseMissing('tasks', ['id' => $task->id, 'title' => 'Hijacked']);
    }

    public function test_owner_cannot_be_mass_assigned(): void
    {
        $user = User::factory()->create();
        $other = User::factory()->create();

        $this->actingAs($user)
            ->postJson('/api/tasks', ['title' => 'Mine', 'user_id' => $other->id])
            ->assertCreated();

        $this->assertDatabaseHas('tasks', ['title' => 'Mine', 'user_id' => $user->id]);
    }

    public function test_unknown_sort_column_is_rejected(): void
    {
        $this->actingAs(User::factory()->create())
            ->getJson('/api/tasks?sort=password')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['sort']);
    }
}
```

## Security assertions per layer

Each new endpoint gets 401, 403 and 422 Feature tests (429 when throttled) in `tests/Feature` with `RefreshDatabase`.

- The factory owns the relation: `'user_id' => User::factory()` in `TaskFactory::definition()`.
- Guests on `/api`: use `getJson` / `postJson`; a plain `get` expects a redirect to a `login` route that may not exist.
- Web forms: `assertInvalid(['email'])` covers both JSON and session errors; `assertSessionHasErrors` for redirects.
- Throttling: loop the allowed number of requests, then assert `assertTooManyRequests()` on the next one.
- Response hygiene: `assertJsonMissingPath('data.password')`; headers: `assertHeader('X-Content-Type-Options', 'nosniff')`.
- Token abilities: `Sanctum::actingAs($user, ['tasks:read'])` (requires `HasApiTokens` on User).
- Outbound HTTP: `Http::preventStrayRequests()` plus `Http::fake([...])`; the sandbox has no business calling the internet.
- Vitest proves escaping without touching PrimeVue internals: mount with a body of `'<img src=x onerror=alert(1)>'`, then `expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>')` and `expect(wrapper.find('img').exists()).toBe(false)`.
- Playwright needs data from `DatabaseSeeder` or created through the UI inside the spec; do not plan an E2E login unless the seeder creates that user.

## Secure code review checklist (Laravel + Vue)

- **Routes**: every user-data route has `auth` / `auth:sanctum` and a policy check; nested bindings scoped; no debug or test-only routes.
- **Requests**: a FormRequest or `validate()` per write; strings have `max:`; enums and sort columns use `Rule::in`; foreign keys use a caller-scoped `Rule::exists`; `authorize()` does not return `true` while no other check exists.
- **Models**: `$fillable` lists only user-editable columns; secrets in `$hidden`; `encrypted` / `hashed` casts where needed; schema changes in a new migration with `up()` and `down()`.
- **Queries**: no interpolated SQL; raw methods use `?` bindings; lists use `paginate()`; queries are scoped to the caller.
- **Responses**: JsonResource with an explicit field list; no `toArray()` dump of models; no exception text.
- **Files**: `File::types()` / `mimes` with a size limit; random names; private disk; downloads authorized.
- **Auth**: `Auth::attempt` + session regenerate; generic failure message; throttled; logout invalidates the session.
- **Config**: `env()` only in `config/*.php`; no keys or passwords in code, seeders or tests; seeders use factories with Faker.
- **Vue**: no `v-html` with user data; no user data echoed inside `#app`; CSRF token sent; validation and permission checks repeated server-side; PrimeVue components from `primevue/<name>`, no deprecated components.
- **Tests**: 401, 403, 422 (and 429 when throttled) cases exist for each new endpoint.

## Severity triage

| Severity | Examples in this stack | Action in the plan |
|---|---|---|
| Critical | auth bypass; SQL injection; mass-assignable `is_admin` / `user_id`; uploads stored executable under `public/`; secret committed to code | fix in this change, test-first |
| High | IDOR on read; stored XSS via `v-html` or `{!! !!}`; plaintext token or PII column; unthrottled login | fix in this change, test-first |
| Medium | resource exposes another user's email; verbose errors; unbounded list endpoint; missing security headers | fix when the change touches the code; else list under Risks or ambiguities |
| Low | missing log line for a destructive action; defence-in-depth gaps without a direct exploit | list under Risks or ambiguities |

Rate by impact (what an attacker gains) and reach (anonymous > any user > admin only). Do not refactor unrelated code to fix a finding outside the issue's scope; name it in the risks instead.

## Security headers

```php
namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class SecurityHeaders
{
    public function handle(Request $request, Closure $next): Response
    {
        $response = $next($request);

        $response->headers->set('X-Content-Type-Options', 'nosniff');
        $response->headers->set('X-Frame-Options', 'DENY');
        $response->headers->set('Referrer-Policy', 'strict-origin-when-cross-origin');
        $response->headers->set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

        return $response;
    }
}
```

- Add headers only when the issue asks for hardening. `$response->headers->set` also works on file downloads and streamed responses.
- Global registration lives in `bootstrap/app.php`, which a Nesti change does not edit; attach the middleware to route groups instead: `Route::middleware([SecurityHeaders::class])->group(function () { ... });` in `routes/web.php` and `routes/api.php`.
- `Strict-Transport-Security` only when the issue states the app is served over HTTPS; the sandbox serves plain HTTP.
- Content-Security-Policy: do not add one unless the issue asks. The scaffold compiles the in-DOM `#app` template at runtime, which needs `'unsafe-eval'`, and PrimeVue injects `<style>` elements whose nonce is configured only at PrimeVue setup in `app.js`. A strict policy blanks the page and fails Playwright. When required, generate the script nonce with `Vite::useCspNonce()` in the middleware and build the header from `Vite::cspNonce()`.
- Test: `$this->get('/')->assertHeader('X-Frame-Options', 'DENY');`.

## Cryptography

- Never implement a cipher, hash or token scheme. No md5/sha1 for passwords, no base64 as "encryption", no `rand()` / `mt_rand()` for secrets; use `Str::random(40)` or `random_bytes()`.
- Passwords: `Hash::make`, `Hash::check`, `Hash::needsRehash` (bcrypt by default). API tokens: Sanctum (stored as SHA-256 hashes).
- Reversible secrets (third-party API keys, personal identifiers): the `encrypted` cast (also `encrypted:array`, `encrypted:collection`, `encrypted:object`) on a TEXT column, or `Crypt::encryptString` / `Crypt::decryptString`, catching `Illuminate\Contracts\Encryption\DecryptException`. Laravel encrypts with OpenSSL AES and signs every value with a MAC, so tampered values fail to decrypt.
- Encrypted columns cannot be searched or used in `where`; if the issue needs filtering, filter on a non-secret column.
- Everything depends on `APP_KEY` (generated by `php artisan key:generate`, kept in `.env`). Rotation: the new key goes into `APP_KEY`, the old ones into the comma-separated `APP_PREVIOUS_KEYS`, so old values still decrypt. This is deployment configuration, never code.
- Compare secrets with `hash_equals()`, not `===`, to avoid timing leaks.
- Tamper-proof links: `URL::signedRoute` / `URL::temporarySignedRoute` with the `signed` middleware instead of home-made HMAC parameters.
