# -*- coding: utf-8 -*-
from xmlrpc import client as xmlrpclib

import httplib2

h = httplib2.Http()
headers = {
   'User-Agent': 'miadi',
   'Authorization': 'Basic YWRtaW46YWRtaW4=',
   'content-type': 'text/plain',
}
(resp, content) = h.request("http://192.168.33.11/tickets/upload/1/?filename=test.txt",
                            "PUT", body="X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
                            headers=headers)
print(resp)
print(content)
