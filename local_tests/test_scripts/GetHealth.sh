#! /bin/bash

if [ $# -lt 3 ]; then
    echo "Not enough arguments provided - please provide admin login, password and IP address for Hammerspace anvil node"
    echo ""
    echo "Example: ./GetHealth.sh MyUserName MyPassword 192.168.0.100"
    echo ""
    exit 1
fi

CURL=`which curl`
if [ -z $CURL ]; then 
	echo "curl is not installed.. exiting"
	exit 1
fi

PYTHON=`which python`
if [ -z $PYTHON ]; then 
	echo "python is not installed.. exiting"
	exit 1
fi

PUBLIC_IP="$3"
PROTO='https'
PORT='8443'
CONTENT_HEADER="accept:application/json"
AUTH_HEADER="username=$1&password=$2"

token="$($CURL -i -k -X POST "$PROTO://$PUBLIC_IP:$PORT/mgmt/v1.2/rest/login" -H "$CONTENT_HEADER" -d "$AUTH_HEADER" -s | grep -i "Set-Cookie" | cut -d: -f2 | cut -d\; -f1 | sed -e 's/^[[:space:]]*//')"

if [ -z $token ]; then echo "Failed to get token"; exit 1; fi

#Create token header:
TOKEN_HEADER="Cookie: $token"
node_info="$($CURL -k -X GET "$PROTO://$PUBLIC_IP:$PORT/mgmt/v1.2/rest/system/health" -H "$CONTENT_HEADER" -H "$TOKEN_HEADER" -s)" 

echo $node_info | python -m json.tool
