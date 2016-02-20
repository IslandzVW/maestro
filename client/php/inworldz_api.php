<?
/*
 *    PHP IW API v1.0
 *    a class for InWorldz Remote API calls
 */

class inworldz_api 
{
    private $_url;

    private $_session_id;
    private $_user;
    private $_password;

    function __construct ($url, $user, $password) 
	{
        $r = $this->iwrpc_request($url, $this->iwrpc_method('session.login_with_password', array($user, $password, '1.3')));
        if (is_array($r) && $r['Status'] == 'Success') 
		{
            $this->_session_id = $r['Value'];
            $this->_url = $url;
            $this->_user = $user;
            $this->_password = $password;
        } 
		else 
		{
            echo "API failure.  (" . implode(' ', $r['ErrorDescription']) . ")\n";  exit;
        }
    }

    function __call($name, $args) 
	{
        if (!is_array($args)) 
		{
            $args = array();
        }
        list($mod, $method) = explode('_', $name, 2);
        $ret = $this->iwrpc_parseresponse(
				  $this->iwrpc_request($this->_url, 
                  $this->iwrpc_method($mod . '.' . $method, array_merge(array($this->_session_id), $args))));
        return $ret;
    }

    function iwrpc_parseresponse($response) 
	{
        if (!@is_array($response) && !@$response['Status']) 
		{
            echo "API failure.  (500)\n";  exit;
        } 
		else 
		{
            if ($response['Status'] == 'Success') 
			{
               $ret = $response['Value'];
            } 
			else 
			{
               if ($response['ErrorDescription'][0] == 'SESSION_INVALID') 
			   {
                   $r = $this->iwrpc_request(
							   $url, $this->iwrpc_method('session.login_with_password', 
                               array($this->_user, $this->_password, '1.3')));
                   if (!is_array($r) && $r['Status'] == 'Success') 
				   {
                       $this->_session_id = $r['Value'];
                   } 
				   else 
				   {
                       echo "API failure.  (session)\n";  exit;
                   }
               } 
			   else 
			   {
                   echo "API failure.  (" . implode(' ', $response['ErrorDescription']) . ")\n";  exit;
               }
            }
        }
        return $ret;
    }

    function iwrpc_method($name, $params) 
	{
        $ret = xmlrpc_encode_request($name, $params);
        return $ret;
    }

    function iwrpc_request($url, $req) 
	{
        $headers = array('Content-type: text/xml', 'Content-length: ' . strlen($req));
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'POST');
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch, CURLOPT_TIMEOUT, 60);
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers); 
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, FALSE);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, FALSE);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $req); 
        $resp = curl_exec($ch);
        curl_close($ch); 

        $ret = xmlrpc_decode($resp);
        return $ret;
    }
}
