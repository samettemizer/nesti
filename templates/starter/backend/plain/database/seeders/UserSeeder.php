<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class UserSeeder extends Seeder
{
    /**
     * Seed the demo accounts; running it again changes nothing.
     */
    public function run(): void
    {
        User::firstOrNew(['email' => 'admin@example.com'])
            ->forceFill(['name' => 'Admin', 'password' => Hash::make('password')])
            ->save();

        foreach (range(1, 24) as $number) {
            $user = User::firstOrNew(['email' => sprintf('user%02d@example.com', $number)]);

            if (! $user->exists) {
                $user->forceFill(['name' => fake()->name(), 'password' => Hash::make('password')])->save();
            }
        }
    }
}
