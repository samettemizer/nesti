<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class AuthApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_login_returns_a_token_and_the_user(): void
    {
        $user = User::factory()->create(['password' => Hash::make('password')]);

        $this->postJson('/api/login', ['email' => $user->email, 'password' => 'password'])
            ->assertOk()
            ->assertJsonStructure(['token', 'user' => ['id', 'name', 'email', 'created_at']])
            ->assertJsonPath('user.email', $user->email);
    }

    public function test_login_rejects_a_wrong_password(): void
    {
        $user = User::factory()->create(['password' => Hash::make('password')]);

        $this->postJson('/api/login', ['email' => $user->email, 'password' => 'wrong-password'])
            ->assertUnprocessable()
            ->assertJsonValidationErrors('email');
    }

    public function test_login_requires_email_and_password(): void
    {
        $this->postJson('/api/login')
            ->assertUnprocessable()
            ->assertJsonValidationErrors(['email', 'password']);
    }

    public function test_logout_revokes_the_token(): void
    {
        $user = User::factory()->create(['password' => Hash::make('password')]);
        $token = $this->postJson('/api/login', ['email' => $user->email, 'password' => 'password'])
            ->json('token');

        $this->withToken($token)->postJson('/api/logout')->assertNoContent();

        $this->assertDatabaseCount('personal_access_tokens', 0);
    }
}
