<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class UserApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_guests_cannot_list_users(): void
    {
        $this->getJson('/api/users')->assertUnauthorized();
    }

    public function test_users_are_listed_paginated(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $this->getJson('/api/users')
            ->assertOk()
            ->assertJsonStructure(['data', 'links', 'meta' => ['total']])
            ->assertJsonPath('meta.total', 1);
    }

    public function test_per_page_is_capped_at_one_hundred(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $this->getJson('/api/users?per_page=101')
            ->assertUnprocessable()
            ->assertJsonValidationErrors('per_page');
    }
}
