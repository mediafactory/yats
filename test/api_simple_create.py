import xmlrpclib

ticket = {
    'summary': '2. new Ticket via API simple',
    'description': 'nice desc',
    'priority': None,
    'assigned': None,
}
rpc_srv = xmlrpclib.ServerProxy('http://admin:admin@192.168.33.11:8080/rpc/', allow_none=True, use_datetime=True)
info = rpc_srv.ticket.createSimple(ticket, True)
