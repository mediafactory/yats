# -*- coding: utf-8 -*-
from django.template import loader, RequestContext
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import authenticate, login, get_user
from yats.models import UserProfile

import re
import base64

class OrgaAdditionMiddleware(object):
    def process_request(self, request):
        if request.user.is_active and request.user.is_authenticated():
            try:
                request.organisation = UserProfile.objects.get(user=request.user).organisation
            except:
                pass

            if not request.organisation:
                response = HttpResponse(loader.render_to_string('no_orga.html', {'source': 'middleware', 'request_path': request.build_absolute_uri()}, RequestContext(request)))
                response.status_code = 200
                return response
            return

        else:
            request.organisation = None

class BasicAuthMiddleware(object):
    def __init__(self):
        self.realm = 'yats'
        self.login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/' )

        if hasattr(settings,'PUBLIC_URLS'):
            public_urls = [re.compile(url) for url in settings.PUBLIC_URLS]
        else:
            public_urls = [(re.compile("^%s$" % ( self.login_url[1:] )))]

        self.public_urls = tuple(public_urls)

    def _checkUnicode(self, credentials):
        try:
            credentials[0].decode('utf-8')
        except UnicodeDecodeError:
            credentials[0] = credentials[0].decode('iso-8859-1').encode('utf8')
        try:
            credentials[1].decode('utf-8')
        except UnicodeDecodeError:
            credentials[1] = credentials[1].decode('iso-8859-1').encode('utf8')
        return credentials

    def process_request(self, request):
        for url in self.public_urls:
            if url.match(request.path[1:]):
                return None

        # lookup, if user was already authenticated
        request.user = get_user(request)
        if request.user.is_authenticated():
            try:
                request.organisation = UserProfile.objects.get(user=request.user).organisation
            except:
                pass
            return

        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                # NOTE: We only support basic authentication for now.
                #
                if auth[0].lower() == "basic":
                    uname, passwd = self._checkUnicode(base64.b64decode(auth[1]).split(':', 1))
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        if user.is_active:
                            request.user = user
                            try:
                                request.organisation = UserProfile.objects.get(user=user).organisation
                            except:
                                pass
                            login(request, user)
                            return

        # Either they did not provide an authorization header or
        # something in the authorization attempt failed. Send a 401
        # back to them to ask them to authenticate.
        #
        from socket import gethostname

        response = HttpResponse(loader.render_to_string('401.html', {'source': 'middleware', 'request_path': request.build_absolute_uri(), 'hostname': gethostname()}, RequestContext(request)))
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic realm="%s"' % self.realm
        return response

class TryBasicAuthMiddleware(BasicAuthMiddleware):
    def process_request(self, request):
        for url in self.public_urls:
            if url.match(request.path[1:]):
                return None

        # lookup, if user was already authenticated
        request.user = get_user(request)
        if request.user.is_authenticated():
            try:
                request.organisation = UserProfile.objects.get(user=request.user).organisation
            except:
                pass
            return

        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                # NOTE: We only support basic authentication for now.
                #
                if auth[0].lower() == "basic":
                    uname, passwd = self._checkUnicode(base64.b64decode(auth[1]).split(':', 1))
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        if user.is_active:
                            request.user = user
                            try:
                                request.organisation = UserProfile.objects.get(user=user).organisation
                            except:
                                pass
                            login(request, user)
                            return
