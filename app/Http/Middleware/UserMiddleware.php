<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class UserMiddleware
{
    /**
     * Handle an incoming request.
     */
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->header('user');
        if ($user) {
            $id = (int)$user;
            $this->setUser($id, $this->getName($id));
        } else {
            // Check for X-User-ID and X-User-Name headers
            $userId = $request->header('X-User-ID');
            $userName = $request->header('X-User-Name');
            if ($userId && $userName) {
                $id = (int)$userId;
                $this->setUser($id, $userName);
            }
        }

        return $next($request);
    }

    private function setUser($id, $name)
    {
        if (extension_loaded('aikido')) {
            \aikido\set_user($id, $name);
        }
    }

    private function getName($number)
    {
        $names = [
            "Hans",
            "Pablo",
            "Samuel",
            "Timo",
            "Tudor",
            "Willem",
            "Wout",
            "Yannis",
        ];

        // Use absolute value to handle negative numbers
        // Use modulo to wrap around the list
        $index = abs($number) % count($names);
        return $names[$index];
    }
}
