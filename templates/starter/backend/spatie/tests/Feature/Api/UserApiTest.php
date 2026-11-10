<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Spatie\Permission\Models\Permission;
use Spatie\Permission\Models\Role;
use Tests\TestCase;

class UserApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_guests_cannot_list_users(): void
    {
        $this->getJson('/api/users')->assertUnauthorized();
    }

    public function test_users_without_permission_are_forbidden(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $this->getJson('/api/users')->assertForbidden();
    }

    public function test_users_are_listed_paginated_with_roles(): void
    {
        Role::findOrCreate('viewer', 'web')->givePermissionTo(Permission::findOrCreate('users.view', 'web'));
        Sanctum::actingAs(User::factory()->create()->assignRole('viewer'));

        $this->getJson('/api/users')
            ->assertOk()
            ->assertJsonStructure(['data', 'links', 'meta' => ['total']])
            ->assertJsonPath('meta.total', 1)
            ->assertJsonPath('data.0.roles', ['viewer']);
    }

    public function test_per_page_is_capped_at_one_hundred(): void
    {
        Permission::findOrCreate('users.view', 'web');
        Sanctum::actingAs(User::factory()->create()->givePermissionTo('users.view'));

        $this->getJson('/api/users?per_page=101')
            ->assertUnprocessable()
            ->assertJsonValidationErrors('per_page');
    }
}
