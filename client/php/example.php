<?
include('inworldz_api.php');

$url = "https://10.0.0.1"; 
$login = "root"; /* login/user */
$password = "password"; /* password for the user */

/* Establish session with Xenserver */
$iwapi = new inworldz_api($url, $login, $password);

/* Once sucessfully logged in - any method (valid or not) is passed to the XenServer.

Replace the first period (.) of the method with a underscore (_) - because PHP doesnt like
periods in the function names.

All the methods (other then logging in) require passing the session_id as the first parameter,
however this is done automatically - so you do not need to pass it.

For example, to do VM.get_all(session_id) and get all the vms as an array, then get/print the details of each
using VM.get_record(session_id, self) (self = VM object):
*/

$vms_array = $iwapi->Console_get_all();

foreach ($vms_array as $vm) {
    $record = $iwpai->VM_get_record($vm);
    print_r($record);
}

/*

To see how parametes are returned, print_r() is your friend :)

*/
?>