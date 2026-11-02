<?php

namespace Tests\Feature\Api;

use App\Models\User;
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
        Sanctum::actingAs(User::factory()->create());

        $this->assertIsArray($this->getJson('/api/roles')->assertOk()->json('data'));
        $this->assertIsArray($this->getJson('/api/permissions')->assertOk()->json('data'));
    }
}
