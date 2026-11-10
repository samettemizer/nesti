<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Database\Seeders\RolePermissionSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class RoleApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_guests_cannot_list_roles_or_permissions(): void
    {
        $this->getJson('/api/roles')->assertUnauthorized();
        $this->getJson('/api/permissions')->assertUnauthorized();
    }

    public function test_roles_and_permissions_are_listed(): void
    {
        $this->seed(RolePermissionSeeder::class);
        Sanctum::actingAs(User::factory()->create()->givePermissionTo('roles.view'));

        $roles = $this->getJson('/api/roles')
            ->assertOk()
            ->assertJsonCount(3, 'data')
            ->assertJsonPath('data.0.name', 'admin')
            ->assertJsonCount(8, 'data.0.permissions')
            ->json('data');

        $this->assertEqualsCanonicalizing(
            ['users.view'],
            collect($roles)->firstWhere('name', 'viewer')['permissions']
        );

        $this->getJson('/api/permissions')
            ->assertOk()
            ->assertJsonCount(8, 'data')
            ->assertJsonStructure(['data' => [['id', 'name', 'guard_name']]]);
    }
}
