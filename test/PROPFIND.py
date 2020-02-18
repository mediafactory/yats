# -*- coding: utf-8 -*-

"""
PROPFIND /tickets/dav/admin/ HTTP/1.1
Host: 192.168.33.11:8080
Content-Type: text/xml
Depth: 0
Brief: t
Accept: */*
Connection: keep-alive
Prefer: return=minimal
User-Agent: Mac+OS+X/10.13.6 (17G10021) CalendarAgent/399.2.2
Content-Length: 127
Accept-Language: de-de
Accept-Encoding: gzip, deflate

HTTP/1.1 401 Unauthorized
Date: Mon, 17 Feb 2020 17:14:03 GMT
Server: WSGIServer/0.2 CPython/3.7.3
Content-Type: text/html; charset=utf-8
WWW-Authenticate: Basic realm="YATS Tickets - Password Required"
X-ProcessedBy: yats-dev
Cache-Control: no-cache, must-revalidate
Expires: Sat, 26 Jul 1997 05:00:00 GMT
X-Frame-Options: SAMEORIGIN
Content-Length: 0
Vary: Accept-Language, Cookie
Content-Language: de
"""
import httplib2

body = """<?xml version="1.0" encoding="UTF-8"?>
<A:propfind xmlns:A="DAV:">
  <A:prop>
    <A:principal-URL/>
  </A:prop>
</A:propfind>"""

h = httplib2.Http()
headers = {
   'User-Agent': 'Mac+OS+X/10.13.6 (17G10021) CalendarAgent/399.2.2',
   'Authorization': 'Basic YWRtaW46YWRtaW4=',
   'Content-Type': 'text/xml',
   'Depth': '0',
   'Brief': 't',
   'Accept': '*/*',
   'Connection': 'keep-alive',
   'Prefer': 'return=minimal',
   'Content-Length': str(len(body)),
   'Accept-Language': 'de-de',
   'Accept-Encoding': 'gzip, deflate',
}
(resp, content) = h.request("https://mf.mediafactory.de/tickets/dav/henrik.genssen/",
                            "PROPFIND", body=body,
                            headers=headers)
print('HTTP/1.1 %s' % resp['status'])
for header in resp:
    if header != 'status':
        print('%s: %s' % (header, resp[header]))
print(content)
