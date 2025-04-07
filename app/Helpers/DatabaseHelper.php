<?php

namespace App\Helpers;

use Illuminate\Support\Facades\DB;
use Exception;

class DatabaseHelper
{
    // Regex pattern for input validation
    const REGEX = '/^[A-Za-z0-9 ,-.]+$/';

    public static function isValidInput($inputStr)
    {
        return preg_match(self::REGEX, $inputStr);
    }

    public static function clearAll()
    {
        try {
            $rowsAffected = DB::delete('DELETE FROM pets');
            echo "{$rowsAffected} pets have been removed from the database.";
        } catch (Exception $e) {
            echo "Database error occurred: " . $e->getMessage();
        }
    }

    public static function getAllPets()
    {
        $pets = [];
        try {
            $results = DB::select('SELECT * FROM pets');
            
            foreach ($results as $row) {
                $name = $row->pet_name;
                $owner = $row->owner;

                // Validate input for XSS risks
                if (!self::isValidInput($name)) {
                    $name = "[REDACTED: XSS RISK]";
                }
                if (!self::isValidInput($owner)) {
                    $owner = "[REDACTED: XSS RISK]";
                }

                $pets[] = [
                    'pet_id' => $row->pet_id,
                    'name' => $name,
                    'owner' => $owner,
                ];
            }
        } catch (Exception $e) {
            echo "Database error occurred: " . $e->getMessage();
        }

        return $pets;
    }

    public static function getPetById($id)
    {
        try {
            $row = DB::selectOne('SELECT * FROM pets WHERE pet_id = ?', [$id]);
            
            if ($row) {
                return [
                    'pet_id' => $row->pet_id,
                    'name' => $row->pet_name,
                    'owner' => $row->owner,
                ];
            }
        } catch (Exception $e) {
            echo "Database error occurred: " . $e->getMessage();
        }

        return [
            'pet_id' => "-1",
            'name' => "unknown",
            'owner' => "the void",
        ];
    }

    public static function createPetByName($petName)
    {
        try {
            // Intentionally vulnerable to SQL injection by using string concatenation
            $query = "INSERT INTO pets (pet_name, owner) VALUES ('" . $petName . "', 'Aikido Security')";
            $rowsAffected = DB::statement($query);
            return $rowsAffected ? 1 : 0;
        } catch (Exception $e) {
            echo "Database error occurred: " . $e->getMessage();
        }
        return -1;
    }
}
