<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Support\Facades\Auth;

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

        // Check blocking decision from Aikido
        $decision = \aikido\should_block_request();

        if ($decision !== null && $decision->block) {
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
            } else {
                return response('Blocked! '.serialize($decision), 429);
            }
        }

        // Continue to the next middleware or request handler
        return $next($request);
    }
}
