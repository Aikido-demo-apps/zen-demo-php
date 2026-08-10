<?php

namespace App\Helpers;

use Exception;
use Illuminate\Support\Facades\Http;

class Helpers
{
    public static function executeShellCommand($command)
    {
        try {
            // Intentionally vulnerable to command injection
            exec($command, $outputArray, $returnVar);
            $output = implode("\n", $outputArray);
            if (empty($output) && $returnVar !== 0) {
                return response()->json(["error" => "Command execution failed with code: $returnVar"], 400);
            }
        } catch (Exception $e) {
            return self::errorResponse($e);
        }
        return $output;
    }

    public static function makeHttpRequest($urlString)
    {
        $handle = curl_init();

        if ($handle === false) {
            return response()->json(["error" => "Failed to initialize cURL"], 500);
        }

        try {
            // Intentionally vulnerable to SSRF using the native cURL sink
            curl_setopt_array($handle, [
                CURLOPT_URL => $urlString,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_FOLLOWLOCATION => true,
                CURLOPT_TIMEOUT => 30,
            ]);

            $response = curl_exec($handle);
            if ($response === false) {
                throw new Exception("cURL error: " . curl_error($handle));
            }

            $statusCode = curl_getinfo($handle, CURLINFO_HTTP_CODE);
            return response($response, $statusCode ?: 200);
        } catch (Exception $e) {
            return self::errorResponse($e);
        } finally {
            curl_close($handle);
        }
    }

    public static function makeHttpRequest2($urlString)
    {
        try {
            // Intentionally vulnerable to SSRF using Laravel's HTTP client
            $response = Http::get($urlString);
            return response($response->body(), $response->status());
        } catch (Exception $e) {
            return self::errorResponse($e);
        }
    }

    public static function readFile($filePath)
    {
        return self::readPath("/var/www/html/resources/blogs/" . $filePath);
    }

    public static function readFile2($filePath)
    {
        return self::readPath(resource_path('blogs/' . $filePath));
    }

    private static function readPath($fullPath)
    {
        try {
            // Intentionally vulnerable to path traversal
            return file_get_contents($fullPath);
        } catch (Exception $e) {
            return response()->json(["error" => $e->getMessage()], 500);
        }
    }

    private static function errorResponse(Exception $e)
    {
        $statusCode = str_contains($e->getMessage(), "Aikido firewall has blocked") ? 500 : 400;
        return response()->json(["error" => $e->getMessage()], $statusCode);
    }
}
