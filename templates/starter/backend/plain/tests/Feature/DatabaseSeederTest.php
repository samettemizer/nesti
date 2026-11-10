<?php

namespace Tests\Feature;

use App\Models\User;
use Database\Seeders\UserSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class DatabaseSeederTest extends TestCase
{
    use RefreshDatabase;

    public function test_database_seeder_creates_the_admin_account(): void
    {
        $this->seed();

        $this->assertDatabaseHas('users', ['email' => 'admin@example.com']);
    }

    public function test_user_seeder_can_run_twice(): void
    {
        $this->seed(UserSeeder::class);
        $count = User::count();

        $this->seed(UserSeeder::class);

        $this->assertSame($count, User::count());
    }
}
