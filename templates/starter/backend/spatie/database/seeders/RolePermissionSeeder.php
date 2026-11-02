<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Spatie\Permission\Models\Permission;
use Spatie\Permission\Models\Role;
use Spatie\Permission\PermissionRegistrar;

class RolePermissionSeeder extends Seeder
{
    /**
     * Seed the demo roles and their permissions; running it again changes nothing.
     */
    public function run(): void
    {
        app(PermissionRegistrar::class)->forgetCachedPermissions();

        $permissions = collect([
            'users.view', 'users.create', 'users.update', 'users.delete',
            'roles.view', 'roles.create', 'roles.update', 'roles.delete',
        ])->mapWithKeys(fn (string $name) => [$name => Permission::findOrCreate($name, 'web')]);

        $roles = [
            'admin' => $permissions->keys()->all(),
            'manager' => ['users.view', 'users.create', 'users.update', 'roles.view'],
            'viewer' => ['users.view'],
        ];

        foreach ($roles as $role => $names) {
            // Models, not names: a name lookup reads the permission cache, which is stale here.
            Role::findOrCreate($role, 'web')->syncPermissions($permissions->only($names)->values());
        }

        // WithoutModelEvents suppresses spatie's own cache flush on save.
        app(PermissionRegistrar::class)->forgetCachedPermissions();
    }
}
