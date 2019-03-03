# -*- coding: utf-8 -*-
import xmlrpclib

import httplib2
import base64
h = httplib2.Http()
headers = {
   'User-Agent': 'miadi',
   'Authorization': 'Basic ' + base64.b64encode('admin:admin'),
   'content-type': 'text/plain',
}
(resp, content) = h.request("http://192.168.33.11/tickets/upload/1/?filename=test.txt",
                            "PUT", body="X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
                            headers=headers)
print resp
