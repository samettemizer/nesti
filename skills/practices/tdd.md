---
title: Test-Driven Development
slug: tdd
source: nesti://skills/practices/tdd.md
adapted_from: "local skill library: tdd (origin unrecorded)"
triggers: tdd, test driven, red green refactor, test first, regression test, failing test, test coverage
---

# Test-Driven Development

*How to pair every Nesti change with tests that prove the issue's behaviour across PHPUnit, Vitest and Playwright. Adapted for Nesti from a local skill library (tdd, origin unrecorded).*

## The loop in a Nesti change

Nesti writes implementation and tests in one response; the sandbox gates (PHPUnit → OpenAPI → Vitest → Playwright) run afterwards. Red → green therefore becomes:

1. Derive the acceptance criteria from the issue text. Each criterion is one observable behaviour.
2. For each criterion, write the test that would fail against the current repository.
3. Write the minimal implementation that makes that test pass. No speculative features, no behaviour the issue does not name.
4. On a gate failure (its output is fed back), fix the code, not the test, unless the test asserts something the issue never asked for. Never weaken, skip or delete an assertion to get green.

Work in vertical slices inside the single response: one criterion → its test → its code, then the next criterion. Do not write a block of generic tests for imagined behaviour.

A bug issue starts with a regression test named after the broken behaviour (`test_completed_tasks_are_excluded_from_overdue_list`), asserting the correct outcome, then the fix.

Expected values come from the issue or a worked example, never from the implementation. Refactoring beyond what the criterion needs is out of scope.

## Seams per layer

A seam is the public boundary where behaviour is observed without reaching inside. The plan's per-layer test cases are the agreed seams: the planner names them, the coder implements exactly those.

- **PHPUnit Feature** (`tests/Feature`): the HTTP seam. `use RefreshDatabase;`, data from model factories, `actingAs($user)` where the route needs auth, `getJson` / `postJson` / `putJson` / `deleteJson`, then `assertStatus`, `assertOk`, `assertCreated`, `assertNotFound`, `assertUnprocessable`, `assertJsonPath`, `assertJsonValidationErrors`.
- **PHPUnit Unit** (`tests/Unit`): a service or model method called directly with plain inputs.
- **Vitest** (`resources/js/components/__tests__/<Name>.test.js`): component props in, rendered text and emitted events out.
- **Playwright** (`e2e/<feature>.spec.js`): one user-visible flow in the real app, against DatabaseSeeder data or data created inside the spec.

Which layers a change needs:

- Backend-only: PHPUnit (Feature for routes, Unit for services). No `.vue`, no Vitest, no Playwright.
- Frontend-only: Vitest + Playwright. No new PHP code, no PHPUnit test.
- Both: every layer the change touches gets its test.

The OpenAPI layer is a gate, not a test you write: make `/api` routes inferable (typed FormRequest rules, JsonResource, a one-line PHPDoc per controller method). Never write a PHPUnit test that inspects the OpenAPI document.

## Good and bad tests: PHPUnit

Good: behaviour through the public interface, response contract first.

```php
<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TaskStoreTest extends TestCase
{
    use RefreshDatabase;

    public function test_user_can_create_a_task(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)
            ->postJson('/api/tasks', ['title' => 'Write report'])
            ->assertCreated()
            ->assertJsonPath('data.title', 'Write report');

        $this->assertDatabaseHas('tasks', ['title' => 'Write report']);
    }

    public function test_title_is_required(): void
    {
        $this->actingAs(User::factory()->create())
            ->postJson('/api/tasks', [])
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['title']);
    }
}
```

`assertDatabaseHas` is fine as a supplementary persistence check. The anti-pattern is asserting only the database while ignoring the response, or querying tables by hand instead of using the route.

Bad: tautological expected value, recomputed the way the code computes it.

```php
// BAD: passes by construction
$items = [10, 5];
$this->assertSame(array_sum($items), $service->total($items));

// GOOD: independent literal from the issue or a worked example
$this->assertSame(15, $service->total([10, 5]));
```

Red flags: mocking your own classes, testing private methods, asserting call counts or order, names that describe how instead of what, a test that breaks on a refactor with unchanged behaviour.

## Good and bad tests: Vitest

Mount with the PrimeVue plugin and assert on text, props and emitted events.

```js
import { mount } from '@vue/test-utils';
import Aura from '@primeuix/themes/aura';
import PrimeVue from 'primevue/config';
import { describe, expect, it } from 'vitest';
import TaskTable from '../TaskTable.vue';

const global = { plugins: [[PrimeVue, { theme: { preset: Aura } }]] };

describe('TaskTable', () => {
    it('lists the given tasks', () => {
        const wrapper = mount(TaskTable, { props: { tasks: [{ id: 1, title: 'Alpha task' }] }, global });
        expect(wrapper.text()).toContain('Alpha task');
    });

    it('emits remove with the task id', async () => {
        const wrapper = mount(TaskTable, { props: { tasks: [{ id: 1, title: 'Alpha task' }] }, global });
        await wrapper.find('[data-testid="remove-1"]').trigger('click');
        expect(wrapper.emitted('remove')).toEqual([[1]]);
    });
});
```

Bad: asserting PrimeVue's internal DOM shape (`.p-datatable-tbody tr` counts, `p-*` classes). A DataTable with zero rows still renders an empty-message row, so row counts lie. Add your own `data-testid` on elements you render and assert on text instead. Keep specs to behaviour the issue names.

## Mock only at system boundaries

The real SQLite test database via `RefreshDatabase` is the default, not a mock. Never mock Eloquent models or your own services. Fake only what leaves the process:

- Outgoing HTTP: `Http::fake(['api.example.com/*' => Http::response(['ok' => true], 200)])`, then `Http::assertSent(fn ($request) => ...)` or `Http::assertNothingSent()`.
- Mail: `Mail::fake()` → `Mail::assertSent(OrderShipped::class)`, `Mail::assertNotSent(...)`.
- Notifications: `Notification::fake()` → `Notification::assertSentTo($user, OrderShipped::class)`.
- Jobs: `Queue::fake()` → `Queue::assertPushed(ShipOrder::class)`.
- Events: `Event::fake()` → `Event::assertDispatched(OrderShipped::class)`.
- Files: `Storage::fake('avatars')` → `Storage::disk('avatars')->assertExists($path)`.
- Time: `$this->travel(5)->days()`, `$this->travelTo(...)`, `$this->travelBack()`, `$this->freezeTime()`.

Assert the HTTP response first, then the faked side effect.

In Vitest, a component that calls `fetch` gets a stub, never a live request:

```js
import { vi } from 'vitest';

vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ data: [{ id: 1, title: 'Alpha task' }] }),
}));
```

Await the component's update (`await flushPromises()` from `@vue/test-utils`) before asserting rendered text.

## Designing for testability

Pass external dependencies in; let Laravel's container resolve them through constructor injection.

```php
// Testable: the client is injected and configured from config/
class InvoiceSender
{
    public function __construct(private readonly BillingClient $billing)
    {
    }

    public function send(Invoice $invoice): bool
    {
        return $this->billing->createCharge($invoice->total);
    }
}

// Hard to test: builds its own client inside the method
public function send(Invoice $invoice): bool
{
    return (new BillingClient(config('services.billing.key')))->createCharge($invoice->total);
}
```

- Give the boundary class one method per external operation (`createCharge`, `refundCharge`) rather than one generic `request($method, $url)`; each test then fakes one shape with no conditional setup.
- Build boundary clients on Laravel's `Http` facade so `Http::fake()` covers them without a hand-written mock.
- Read credentials via `config()`, never `env()` outside config files.
- Keep controllers thin: validation in a FormRequest, logic in `app/Services` or model methods, so Unit tests reach the logic without HTTP.

## Playwright specifics

```js
import { expect, test } from '@playwright/test';

test('user adds a task', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Title').fill('Buy milk');
    await page.getByRole('button', { name: 'Add task' }).click();
    await expect(page.getByText('Buy milk', { exact: true })).toBeVisible();
});
```

- The sandbox runs `php artisan migrate --force --seed`, builds assets and serves `http://127.0.0.1:8000`. The database holds exactly what `DatabaseSeeder` creates: never assume rows exist. Seed in `DatabaseSeeder::run()` with factories, or create the data through the UI or API inside the spec.
- Use precise locators: `getByRole` with a name, `getByTestId`, `getByText(..., { exact: true })`. Avoid CSS selectors on PrimeVue internals.
- Rely on `expect(...).toBeVisible()` auto-waiting; never fixed sleeps.
- One flow per test, named after the user-visible outcome.
