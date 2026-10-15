<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Helpers\DatabaseHelper;
use App\Helpers\Helpers;

class ApiController extends Controller
{
    public function customEvent(Request $request)
    {
        $count = filter_var($request->query('count', 1), FILTER_VALIDATE_INT, [
            'options' => ['min_range' => 1, 'max_range' => 100],
        ]);
        if ($count === false) {
            return response('count must be an integer between 1 and 100', 400);
        }

        for ($index = 0; $index < $count; $index++) {
            \aikido\track('user.login_failed');
        }
        return 'Events tracked';
    }

    public function clear()
    {
        DatabaseHelper::clearAll();
        return "Cleared successfully.";
    }

    public function getPets()
    {
        $pets = DatabaseHelper::getAllPets();
        return response()->json($pets);
    }

    public function createPet(Request $request)
    {
        return DatabaseHelper::createPetByName($request->input('name', ''));
    }

    public function executeCommandPost(Request $request)
    {
        $data = $request->json()->all();
        $userCommand = $data['userCommand'] ?? '';

        $result = Helpers::executeShellCommand($userCommand);
        return $result;
    }

    public function executeCommandGet($command)
    {
        $result = Helpers::executeShellCommand($command);
        return $result;
    }

    public function makeRequest(Request $request)
    {
        $data = $request->json()->all();
        $url = $data['url'] ?? '';

        $response = Helpers::makeHttpRequest($url);
        return $response;
    }

    public function makeRequest2(Request $request)
    {
        $data = $request->json()->all();
        $url = $data['url'] ?? '';

        $response = Helpers::makeHttpRequest2($url);
        return $response;
    }

    public function makeRequestDifferentPort(Request $request)
    {
        $data = $request->json()->all();
        $url = $data['url'] ?? '';
        $port = $data['port'] ?? '';

        $separatorPosition = strrpos($url, ':');
        if ($separatorPosition === false || $port === '') {
            return response()->json(["error" => "Invalid URL or port"], 400);
        }

        $response = Helpers::makeHttpRequest(substr($url, 0, $separatorPosition) . ':' . $port);
        return $response;
    }

    public function readFile(Request $request)
    {
        $filePath = $request->query('path');
        $content = Helpers::readFile($filePath);
        return $content;
    }

    public function readFile2(Request $request)
    {
        $filePath = $request->query('path');
        $content = Helpers::readFile2($filePath);
        return $content;
    }
}
