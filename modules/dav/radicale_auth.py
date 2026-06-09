# -*- coding: utf-8 -*-
"""
Radicale 3.x auth plugin that TRUSTS the Django layer.

The embedded WSGI view (``dav.views.caldav_view``) authenticates the request
against Django *before* handing the environ to Radicale, and injects a
synthetic ``Authorization`` header carrying the already-validated username.
This plugin therefore only needs to echo the login back — Django is the single
source of truth for authentication.
"""
from radicale.auth import BaseAuth


class Auth(BaseAuth):
    def _login(self, login, password):
        # Django already authenticated the user in caldav_view; trust the login.
        return login
