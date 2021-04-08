#!/bin/bash

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]
then
	echo "usage: $0 <number_of_requests> [e]"
	exit 1
fi

if [ "$#" -eq 2 ] && [ "$2" != "e" ]
then
	echo "usage: $0 <number_of_requests> [e]"
	exit 1
fi

[ "$2" = "e" ] && experimental="true" || experimental="false"

cookie="cookie.txt"
[ -f $cookie ] && rm -f $cookie

i=1
auth=$(printf "user:password" | base64)
while [ $i -le $1 ]
do
	echo "########## home"
	curl -H "experimental:$experimental" http://www.10.219.246.243.xip.io:31380/ > /dev/null
	echo
	echo "########## login"
	curl --cookie-jar $cookie -H "Authorization:Basic $auth" -H "experimental:$experimental" http://www.10.219.246.243.xip.io:31380/login
	echo
	echo "########## catalogue"
	curl -H "experimental:$experimental" -b $cookie http://www.10.219.246.243.xip.io:31380/catalogue > /dev/null
	# curl -b $cookie --header "experimental:true" http://www.10.219.246.243.xip.io:31380/catalogue > /dev/null
	echo "########## detail"
	curl -H "experimental:$experimental" -b $cookie http://www.10.219.246.243.xip.io:31380/detail.html?id=3395a43e-2d88-40de-b95f-e00e1502085b > /dev/null
	echo "########## delete"
	curl -X "DELETE" -b $cookie -H "experimental:$experimental" http://www.10.219.246.243.xip.io:31380/cart
	echo "########## post cart"
	curl -X "POST" -b $cookie -H "experimental:$experimental" --header "Content-Type: application/json" --data '{"id": "3395a43e-2d88-40de-b95f-e00e1502085b", "quantity": 1}' http://www.10.219.246.243.xip.io:31380/cart
	echo "########## basket"
	curl -H "experimental:$experimental" -b $cookie http://www.10.219.246.243.xip.io:31380/basket.html > /dev/null
	echo "########## post order"
	curl -X "POST" -b $cookie -H "experimental:$experimental" http://www.10.219.246.243.xip.io:31380/orders
	echo
	echo "########## orders"
	curl -H "experimental:$experimental" -b $cookie http://www.10.219.246.243.xip.io:31380/customer-orders.html > /dev/null

	i=$((i+1))
done
[ -f $cookie ] && rm -f $cookie