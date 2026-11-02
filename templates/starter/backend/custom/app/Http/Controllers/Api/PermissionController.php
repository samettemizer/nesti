<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\DB;

class PermissionController extends Controller
{
    /**
     * List the rows of the permissions table as they are.
     */
    public function index(): array
    {
        return ['data' => DB::table('permissions')->get()];
    }
}
