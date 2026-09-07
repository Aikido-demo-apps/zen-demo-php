<?php

use Illuminate\Contracts\Http\Kernel;
use Illuminate\Foundation\Application;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Facade;
use Illuminate\Support\Str;

define('LARAVEL_START', microtime(true));

if (file_exists($maintenance = __DIR__ . '/../storage/framework/maintenance.php')) {
    require $maintenance;
}

require __DIR__ . '/../vendor/autoload.php';

/** @var Application $app */
$app = require __DIR__ . '/../bootstrap/app.php';

$kernel = $app->make(Kernel::class);

$nbRequests = 0;

while (frankenphp_handle_request(function () use ($app, $kernel, &$nbRequests) {
    \aikido\worker_rinit();

    Facade::clearResolvedInstances();

    try {
        $request = Request::capture();
        $request->enableHttpMethodParameterOverride();
        $app->instance('request', $request);

        $response = $kernel->handle($request);
        $response->send();
        $kernel->terminate($request, $response);

        if ($route = $request->route()) {
            if (method_exists($route, 'flushController')) {
                $route->flushController();
            }
        }
    } finally {
        if (method_exists($app, 'forgetScopedInstances')) {
            $app->forgetScopedInstances();
        }

        flushState($app);

        $app->forgetInstance('request');

        unset($request, $response, $route);

        if ((++$nbRequests % 100) === 0) {
            gc_collect_cycles();
            $nbRequests = 0;
        }
    }

    \aikido\worker_rshutdown();
})) {
    // keep looping
}

function flushState(Application $app): void
{
    if ($app->resolved('cookie')) {
        $app->make('cookie')->flushQueuedCookies();
    }

    if ($app->resolved('auth')) {
        $app->make('auth')->forgetGuards();
    }

    if ($app->resolved('db')) {
        foreach ($app->make('db')->getConnections() as $connection) {
            $connection->flushQueryLog();
        }
    }

    if ($app->resolved('log')) {
        $logger = $app->make('log');
        if (method_exists($logger, 'flushSharedContext')) {
            $logger->flushSharedContext();
        }
    }

    if ($app->resolved('session')) {
        $driver = $app->make('session');
        if (method_exists($driver, 'flush')) {
            $driver->flush();
        }
    }

    Str::flushCache();

    if ($app->resolved('view.engine.resolver')) {
        $resolver = $app->make('view.engine.resolver');
        $resolver->forget('blade');
        $resolver->forget('php');
    }
}
