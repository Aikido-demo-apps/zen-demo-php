<?php

use App\Http\Controllers\HomeController;
use App\Http\Controllers\ApiController;
use Illuminate\Support\Facades\Route;

Route::get('/', [HomeController::class, 'index']);
Route::get('/pages/create', [HomeController::class, 'create']);
Route::get('/pages/execute', [HomeController::class, 'execute']);
Route::get('/pages/request', [HomeController::class, 'request']);
Route::get('/pages/read', [HomeController::class, 'read']);

// Test routes
Route::get('/test_ratelimiting_1', [HomeController::class, 'ratelimiting1']);
Route::get('/test_ratelimiting_2', [HomeController::class, 'ratelimiting2']);
Route::get('/test_bot_blocking', [HomeController::class, 'botBlock']);
Route::get('/test_user_blocking', [HomeController::class, 'userBlock']);

// API routes
Route::get('/clear', [ApiController::class, 'clear']);
Route::get('/api/pets', [ApiController::class, 'getPets']);
Route::post('/api/create', [ApiController::class, 'createPet']);
Route::post('/api/execute', [ApiController::class, 'executeCommandPost']);
Route::get('/api/execute/{command}', [ApiController::class, 'executeCommandGet']);
Route::post('/api/request', [ApiController::class, 'makeRequest']);
Route::post('/api/request2', [ApiController::class, 'makeRequest2']);
Route::get('/api/read', [ApiController::class, 'readFile']);
