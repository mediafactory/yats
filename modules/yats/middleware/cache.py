# -*- coding: utf-8 -*- 
from django.middleware.cache import UpdateCacheMiddleware, FetchFromCacheMiddleware
from django.core.cache import cache
from django.conf import settings
from django.utils.encoding import iri_to_uri
from django.utils.cache import get_max_age, patch_response_headers
from django.utils.translation import get_language
from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS

import hashlib
import warnings

md5_constructor = hashlib.md5
md5_hmac = md5_constructor
sha_constructor = hashlib.sha1
sha_hmac = sha_constructor

def get_cache_key(request, key_prefix=None):
    """
    depending on user, request-method gererate a key with respect to
    GET with querystring and POST with data
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX

    if request.method in ('GET', 'HEAD'):
        method = 'GET'
        content = md5_constructor(request.GET.urlencode())
    elif request.method == 'POST':
        method = 'POST'
        content = md5_constructor(request.raw_post_data)
    else:
        method = ''
        content = md5_constructor()
    path = md5_constructor(iri_to_uri(request.path))
    
    if request.user.is_authenticated():
        user = iri_to_uri(request.user)
    else:
        user = ''
    
    # on response lang was DE again although on request it was EN, so cache that :-)        
    if hasattr(request, '_cache_lang'):
        lang = request._cache_lang
    else:
        lang = get_language()
        request._cache_lang = lang
    
    return '%s.%s.%s.%s.%s.%s.%s' % (
               request.get_host(), key_prefix, lang, method, user, path.hexdigest(), content.hexdigest())

class yatsUpdateCacheMiddleware(UpdateCacheMiddleware):
    """
    extending djangos standard cache mechanism for POST
    """

    def process_response(self, request, response):
        """Sets the cache, if needed."""
        if not self._should_update_cache(request, response):
            # We don't need to update the cache, just return.
            return response
        if response.streaming or response.status_code != 200:
            return response
        # Try to get the timeout from the "max-age" section of the "Cache-
        # Control" header before reverting to using the default cache_timeout
        # length.
        timeout = get_max_age(response)
        if timeout == None:
            timeout = self.cache_timeout
        elif timeout == 0:
            # max-age was set to 0, don't bother caching.
            return response
        patch_response_headers(response, timeout)
        if timeout:
            #cache_key = learn_cache_key(request, response, timeout, self.key_prefix, cache=self.cache)
            cache_key = get_cache_key(request, key_prefix=None)
            if hasattr(response, 'render') and callable(response.render):
                response.add_post_render_callback(
                    lambda r: self.cache.set(cache_key, r, timeout)
                )
            else:
                self.cache.set(cache_key, response, timeout)
        return response

class yatsFetchFromCacheMiddleware(FetchFromCacheMiddleware):
    """
    extending djangos standard cache mechanism for POST
    """
    
    def process_request(self, request):
        """
        Checks whether the page is already cached and returns the cached
        version if available.
        """
        if not request.method in ('GET', 'HEAD'):
            request._cache_update_cache = False
            return None # Don't bother checking the cache.

        # try and get the cached GET response
        #cache_key = get_cache_key(request, self.key_prefix, 'GET', cache=self.cache)
        cache_key = get_cache_key(request, self.key_prefix)
        if cache_key is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.
        response = self.cache.get(cache_key, None)
        # if it wasn't found and we are looking for a HEAD, try looking just for that
        if response is None and request.method == 'HEAD':
            #cache_key = get_cache_key(request, self.key_prefix, 'HEAD', cache=self.cache)
            cache_key = get_cache_key(request, self.key_prefix)
            response = self.cache.get(cache_key, None)

        if response is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        # hit, return cached response
        request._cache_update_cache = False
        return response    
    
class yatsCacheMiddleware(yatsUpdateCacheMiddleware, yatsFetchFromCacheMiddleware):
    """
    Cache middleware that provides basic behavior for many simple sites.

    Also used as the hook point for the cache decorator, which is generated
    using the decorator-from-middleware utility.
    """
    def __init__(self, cache_timeout=None, cache_anonymous_only=None, **kwargs):
        # We need to differentiate between "provided, but using default value",
        # and "not provided". If the value is provided using a default, then
        # we fall back to system defaults. If it is not provided at all,
        # we need to use middleware defaults.

        cache_kwargs = {}

        try:
            self.key_prefix = kwargs['key_prefix']
            if self.key_prefix is not None:
                cache_kwargs['KEY_PREFIX'] = self.key_prefix
            else:
                self.key_prefix = ''
        except KeyError:
            self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
            cache_kwargs['KEY_PREFIX'] = self.key_prefix

        try:
            self.cache_alias = kwargs['cache_alias']
            if self.cache_alias is None:
                self.cache_alias = DEFAULT_CACHE_ALIAS
            if cache_timeout is not None:
                cache_kwargs['TIMEOUT'] = cache_timeout
        except KeyError:
            self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
            if cache_timeout is None:
                cache_kwargs['TIMEOUT'] = settings.CACHE_MIDDLEWARE_SECONDS
            else:
                cache_kwargs['TIMEOUT'] = cache_timeout

        if cache_anonymous_only is None:
            self.cache_anonymous_only = getattr(settings, 'CACHE_MIDDLEWARE_ANONYMOUS_ONLY', False)
        else:
            self.cache_anonymous_only = cache_anonymous_only

        if self.cache_anonymous_only:
            msg = "CACHE_MIDDLEWARE_ANONYMOUS_ONLY has been deprecated and will be removed in Django 1.8."
            warnings.warn(msg, PendingDeprecationWarning, stacklevel=1)

        self.cache = get_cache(self.cache_alias, **cache_kwargs)
        self.cache_timeout = self.cache.default_timeout
