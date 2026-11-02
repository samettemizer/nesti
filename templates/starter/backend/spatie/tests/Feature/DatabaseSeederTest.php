<?php

namespace Tests\Feature;

use App\Models\User;
use Database\Seeders\RolePermissionSeeder;
use Database\Seeders\UserSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Spatie\Permission\Models\Permission;
use Spatie\Permission\Models\Role;
use Tests\TestCase;

class DatabaseSeederTest extends TestCase
{
    use RefreshDatabase;

    public function test_database_seeder_creates_the_admin_account_roles_and_permissions(): void
    {
        $this->seed();

        $admin = User::query()->where('email', 'admin@example.com')->firstOrFail();
        $this->assertTrue($admin->hasRole('admin'));
        $this->assertSame(3, Role::query()->whereIn('name', ['admin', 'manager', 'viewer'])->count());
        $this->assertSame(8, Permission::query()->whereIn('name', [
            'users.view', 'users.create', 'users.update', 'users.delete',
            'roles.view', 'roles.create', 'roles.update', 'roles.delete',
        ])->count());
    }

    public function test_user_seeder_can_run_twice(): void
    {
        $this->seed(RolePermissionSeeder::class);
        $this->seed(UserSeeder::class);
        $count = User::count();

        $this->seed(UserSeeder::class);

        $this->assertSame($count, User::count());
    }
}
