# -*- coding: utf-8 -*-
from django.template import loader, RequestContext
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import authenticate, login, get_user
from yats.models import UserProfile

import re
import base64

def OrgaAdditionMiddleware(get_response):

    def middleware(request):
        if request.user.is_active and request.user.is_authenticated:
            try:
                request.organisation = UserProfile.objects.get(user=request.user).organisation
            except Exception:
                pass

            if not hasattr(request, 'organisation') or not request.organisation:
                response = HttpResponse(loader.render_to_string('no_orga.html', {'source': 'middleware', 'request_path': request.build_absolute_uri()}, RequestContext(request)))
                response.status_code = 200
                return response
            return get_response(request)

        else:
            request.organisation = None

        response = get_response(request)
        return response

    return middleware

class BasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.realm = 'yats'
        self.login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')

        if hasattr(settings, 'PUBLIC_URLS'):
            public_urls = [re.compile(url) for url in settings.PUBLIC_URLS]
        else:
            public_urls = [(re.compile("^%s$" % (self.login_url[1:])))]
        public_urls.append(re.compile(r'^' + settings.DJRADICALE_CONFIG['server']['base_prefix'].lstrip('/')))

        self.public_urls = tuple(public_urls)

    def __call__(self, request):
        for url in self.public_urls:
            if url.match(request.path[1:]):
                return self.get_response(request)

        # lookup, if user was already authenticated
        request.user = get_user(request)
        if request.user.is_authenticated:
            try:
                request.organisation = UserProfile.objects.get(user=request.user).organisation
            except Exception:
                pass
            return self.get_response(request)

        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                # NOTE: We only support basic authentication for now.
                #
                if auth[0].lower() == "basic":
                    auth_data = auth[1]
                    auth_data += "=" * ((4 - len(auth_data) % 4) % 4)
                    auth_data = base64.b64decode(auth_data).decode('utf-8')
                    uname, passwd = auth_data.split(':', 1)
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        if user.is_active:
                            request.user = user
                            try:
                                request.organisation = UserProfile.objects.get(user=user).organisation
                            except Exception:
                                pass
                            login(request, user)
                            return self.get_response(request)

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
    def __call__(self, request):
        for url in self.public_urls:
            if url.match(request.path[1:]):
                return self.get_response(request)

        # lookup, if user was already authenticated
        request.user = get_user(request)
        if request.user.is_authenticated:
            try:
                request.organisation = UserProfile.objects.get(user=request.user).organisation
            except Exception:
                pass
            return self.get_response(request)

        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                # NOTE: We only support basic authentication for now.
                #
                if auth[0].lower() == "basic":
                    auth_data = auth[1]
                    auth_data += "=" * ((4 - len(auth_data) % 4) % 4)
                    auth_data = base64.b64decode(auth_data).decode('utf-8')
                    uname, passwd = auth_data.split(':', 1)
                    user = authenticate(username=uname, password=passwd)
                    if user:
                        if user.is_active:
                            request.user = user
                            try:
                                request.organisation = UserProfile.objects.get(user=user).organisation
                            except Exception:
                                pass
                            login(request, user)
                            return self.get_response(request)

        return self.get_response(request)
