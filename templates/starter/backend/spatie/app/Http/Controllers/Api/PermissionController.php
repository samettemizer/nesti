<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Spatie\Permission\Models\Permission;

class PermissionController extends Controller
{
    /**
     * List the permissions, ordered by name.
     */
    public function index(): array
    {
        return [
            'data' => Permission::query()->orderBy('name')->get(['id', 'name', 'guard_name']),
        ];
    }
}
