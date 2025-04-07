<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class AikidoMiddleware
{
    /**
     * Handle an incoming request.
     */
    public function handle($request, Closure $next)
    {
        // Check if Aikido extension is loaded
        if (!extension_loaded('aikido')) {
            return $next($request);
        }

        // Get the authenticated user's ID from Laravel's Auth system
        $userId = Auth::id();

        // If a user is authenticated, set the user in Aikido's firewall context
        if ($userId) {
            // If username is available, you can set it as the second parameter in the \aikido\set_user function call
            \aikido\set_user($userId);
        }

        // Check blocking decision from Aikido
        $decision = \aikido\should_block_request();

        if ($decision->block) {
            if ($decision->type == "blocked") {
                if ($decision->trigger == "user") {
                    return response('Your user is blocked!', 403);
                }
                else if ($decision->trigger == "ip") {
                    return response("Your IP ({$decision->ip}) is blocked due to: {$decision->description}!", 403);
                }
            }
            else if ($decision->type == "ratelimited") {
                if ($decision->trigger == "user") {
                    return response('Your user exceeded the rate limit for this endpoint!', 429);
                }
                else if ($decision->trigger == "ip") {
                    return response("Your IP ({$decision->ip}) exceeded the rate limit for this endpoint!", 429);
                }
            }
        }

        // Continue to the next middleware or request handler
        return $next($request);
    }
}
