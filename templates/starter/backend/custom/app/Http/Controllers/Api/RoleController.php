<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\DB;

class RoleController extends Controller
{
    /**
     * List the rows of the roles table as they are.
     */
    public function index(): array
    {
        return ['data' => DB::table('roles')->get()];
    }
}
