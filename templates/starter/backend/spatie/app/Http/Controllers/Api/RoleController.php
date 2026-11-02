<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Spatie\Permission\Models\Role;

class RoleController extends Controller
{
    /**
     * List the roles with their permission names, ordered by name.
     */
    public function index(): array
    {
        $roles = Role::query()->with('permissions:id,name')->orderBy('name')->get();

        return [
            'data' => $roles->map(fn (Role $role) => [
                'id' => $role->id,
                'name' => $role->name,
                'guard_name' => $role->guard_name,
                'permissions' => $role->permissions->pluck('name'),
            ]),
        ];
    }
}
