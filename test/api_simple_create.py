import xmlrpclib

ticket = {
    'summary': '2. new Ticket via API simple',
    'description': 'nice desc',
    'priority': None,
    'assigned': None,
}
rpc_srv = xmlrpclib.ServerProxy('http://admin:admin@192.168.33.11:8080/rpc/', allow_none=True, use_datetime=True)
info = rpc_srv.ticket.createSimple(ticket, True)

print 'ticket created #%s' % info[0]


import httplib2
import base64
h = httplib2.Http()
headers = {
   'User-Agent': 'miadi',
   'Authorization': 'Basic ' + base64.b64encode('admin:admin'),
   'content-type':'text/plain',
}
(resp, content) = h.request("http://192.168.33.11:8080/tickets/upload/%s/?filename=test.txt" % info[0],
                            "PUT", body="This is text",
                            headers=headers )
print resp
#print content
