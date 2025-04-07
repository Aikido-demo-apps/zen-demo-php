<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
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

        $rowsCreated = DatabaseHelper::createPetByName($name);

        if ($rowsCreated == -1) {
            return "Database error occurred";
        }
        return "Success!";
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

        $response = Helpers::makeHttpRequest($url);
        return $response;
    }

    public function readFile(Request $request)
    {
        $filePath = $request->query('path');
        $content = Helpers::readFile($filePath);
        return $content;
    }
}
