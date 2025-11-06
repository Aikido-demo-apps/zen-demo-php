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
                return response()->json(["error" => "Command execution failed with code: $returnVar"], 400);
            }
        } catch (Exception $e) {
            if (str_contains($e->getMessage(), "Aikido firewall has blocked")) {
                return response()->json(["error" => $e->getMessage()], 500);
            } else {
                return response()->json(["error" => $e->getMessage()], 400);
            }
        }
        return $output;
    }

    public static function makeHttpRequest($urlString)
    {
        try {
            // Initialize cURL session
            $ch = curl_init();
    
            // Set cURL options
            curl_setopt($ch, CURLOPT_URL, $urlString);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); 
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true); 
            curl_setopt($ch, CURLOPT_TIMEOUT, 30); 
    
            // Execute the request
            $response = curl_exec($ch);
    
            // Check for errors
            if (curl_errno($ch)) {
                throw new Exception("cURL error: " . curl_error($ch));
            }
    
            // Get HTTP status code
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    
            // Close cURL session
            curl_close($ch);
    
            // Return response and status code
            return  response()->json($response, $httpCode);
    
        } catch (Exception $e) {
            return response()->json($e->getMessage(), 500);
        }
    }
    
    

    public static function makeHttpRequest2($urlString)
    {
        try {
            // Intentionally vulnerable to SSRF
            $response = Http::get($urlString);
            return $response->body();
        } catch (Exception $e) {
            if (str_contains($e->getMessage(), "Aikido firewall has blocked")) {
                return response()->json(["error" => $e->getMessage()], 500);
            } else if (str_contains($e->getMessage(), "Could not resolve host") || str_contains($e->getMessage(), "Unable to parse URI")) {
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
            echo "filePath: " . $filePath . "\n";
            var_dump($_GET['path']);
            $fullPath = "/var/www/html/resources/blogs/" . $filePath;
            echo "fullPath: " . $fullPath . "\n";
            $content = file_get_contents($fullPath);
        } catch (Exception $e) {
            if (str_contains($e->getMessage(), "Aikido firewall has blocked") || 
                str_contains($e->get2Message(), "No such file or directory") ||
                str_contains($e->getMessage(), "Is a directory") ||
                str_contains($e->getMessage(), "Array to string conversion") 
            ) {
                return response()->json(["error" => $e->getMessage()], 500);
            } else {
                return response()->json(["error" => $e->getMessage()], 400);
            }
            $content = "Error: " . $e->getMessage();
        }
        return $content;
    }

    public static function readFile2($filePath)
    {
        $content = "";
        try {
            // Intentionally vulnerable to path traversal
            $fullPath = resource_path('blogs/' . $filePath);
            $content = file_get_contents($fullPath);
        } catch (Exception $e) {
            if (str_contains($e->getMessage(), "Aikido firewall has blocked") || 
                str_contains($e->get2Message(), "No such file or directory") ||
                str_contains($e->getMessage(), "Is a directory") ||
                str_contains($e->getMessage(), "Array to string conversion") 
            ) {
                return response()->json(["error" => $e->getMessage()], 500);
            } else {
                return response()->json(["error" => $e->getMessage()], 400);
            }
            $content = "Error: " . $e->getMessage();
        }
        return $content;
    }
}
