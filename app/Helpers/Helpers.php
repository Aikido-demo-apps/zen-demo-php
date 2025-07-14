<?php

namespace App\Helpers;

use Exception;
use Illuminate\Support\Facades\Http;

class Helpers
{
    public static function executeShellCommand($command)
    {
        $output = "";
        try {
            // Intentionally vulnerable to command injection
            exec($command, $outputArray, $returnVar);
            $output = implode("\n", $outputArray);
            if (empty($output) && $returnVar !== 0) {
                $output = "Command execution failed with code: $returnVar";
            }
        } catch (Exception $e) {
            $output = "Error: " . $e->getMessage();
        }
        return $output;
    }

    public static function makeHttpRequest($urlString)
    {
        try {
            // Intentionally vulnerable to SSRF
            $response = Http::get($urlString);
            return $response->body();
        } catch (Exception $e) {
            if (str_contains($e->getMessage(), "Aikido firewall has blocked")) {
                return response()->json(["error" => $e->getMessage()], 500);
            } else if (str_contains($e->getMessage(), "Could not resolve host")) {
                return response()->json(["error" => $e->getMessage()], 500);
            } else {
                return response()->json(["error" => $e->getMessage()], 400);
            }
        }
    }

    public static function readFile($filePath)
    {
        $content = "";
        try {
            // Intentionally vulnerable to path traversal
            $fullPath = resource_path('blogs/' . $filePath);
            $content = file_get_contents($fullPath);
        } catch (Exception $e) {
            $content = "Error: " . $e->getMessage();
        }
        return $content;
    }
}
