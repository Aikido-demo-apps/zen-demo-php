<?php

namespace App\Http\Controllers;

use Exception;
use Illuminate\Http\Request;
use App\Helpers\DatabaseHelper;
use App\Helpers\Helpers;

class ApiController extends Controller
{
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
        $data = $request->json()->all();
        $name = $data['name'] ?? '';

        return $this->createPetByName($name);
    }

    public function createPetForm(Request $request)
    {
        return $this->createPetByName($request->input('name', ''));
    }

    private function createPetByName($name)
    {
        try {
            if (DatabaseHelper::createPetByName($name)) {
                return response()->json(["success" => "Pet created successfully"]);
            }
            return response()->json(["error" => "Failed to create pet"], 400);
        } catch (Exception $e) {
            $statusCode = str_contains($e->getMessage(), "Aikido firewall has blocked") ? 500 : 400;
            return response()->json(["error" => $e->getMessage()], $statusCode);
        }
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
