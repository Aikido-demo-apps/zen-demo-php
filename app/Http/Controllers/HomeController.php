<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class HomeController extends Controller
{
    public function index()
    {
        return File::get(base_path('resources') . '/index.html');
    }

    public function create()
    {
        return File::get(base_path('resources') . '/create.html');
    }

    public function execute()
    {
        return File::get(base_path('resources') . '/execute_command.html');
    }

    public function request()
    {
        return File::get(base_path('resources') . '/request.html');
    }

    public function read()
    {
        return File::get(base_path('resources') . '/read_file.html');
    }

    public function ratelimiting1()
    {
        return "Request successful (Ratelimiting 1)";
    }

    public function ratelimiting2()
    {
        return "Request successful (Ratelimiting 2)";
    }

    public function botBlock()
    {
        return "Hello World! Bot blocking enabled on this route.";
    }

    public function userBlock(Request $request)
    {
        return "Hello User with id: " . $request->header('user');
    }
}
