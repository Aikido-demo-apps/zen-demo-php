<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use App\Http\Middleware\UserMiddleware;
use App\Http\Middleware\AikidoMiddleware;
use Illuminate\Contracts\Http\Kernel;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        $kernel = $this->app->make(Kernel::class);
        $kernel->pushMiddleware(UserMiddleware::class);
        $kernel->pushMiddleware(AikidoMiddleware::class);
    }
}
