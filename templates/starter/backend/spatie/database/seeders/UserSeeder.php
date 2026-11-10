<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class UserSeeder extends Seeder
{
    /**
     * Seed the demo accounts with their roles; running it again changes nothing.
     */
    public function run(): void
    {
        $admin = User::firstOrNew(['email' => 'admin@example.com']);
        $admin->forceFill(['name' => 'Admin', 'password' => Hash::make('password')])->save();
        $admin->syncRoles(['admin']);

        foreach (range(1, 24) as $number) {
            $user = User::firstOrNew(['email' => sprintf('user%02d@example.com', $number)]);

            if (! $user->exists) {
                $user->forceFill(['name' => fake()->name(), 'password' => Hash::make('password')])->save();
            }

            $user->syncRoles([$number <= 4 ? 'manager' : 'viewer']);
        }
    }
}
