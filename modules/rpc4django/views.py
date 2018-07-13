'''
The main entry point for RPC4Django. Usually, the user simply puts
:meth:`serve_rpc_request <rpc4django.views.serve_rpc_request>` into ``urls.py``

::

    urlpatterns = patterns('',
        # rpc4django will need to be in your Python path
        (r'^RPC2$', 'rpc4django.views.serve_rpc_request'),
    )

'''

import logging
import json
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt

from .rpcdispatcher import dispatcher
from .__init__ import version

logger = logging.getLogger('rpc4django')

# these restrictions can change the functionality of rpc4django
# but they are completely optional
# see the rpc4django documentation for more details
LOG_REQUESTS_RESPONSES = getattr(settings,
                                 'RPC4DJANGO_LOG_REQUESTS_RESPONSES', True)

RESTRICT_JSON = getattr(settings, 'RPC4DJANGO_RESTRICT_JSONRPC', False)
RESTRICT_XML = getattr(settings, 'RPC4DJANGO_RESTRICT_XMLRPC', False)
RESTRICT_METHOD_SUMMARY = getattr(settings,
                                  'RPC4DJANGO_RESTRICT_METHOD_SUMMARY', False)
RESTRICT_RPCTEST = getattr(settings, 'RPC4DJANGO_RESTRICT_RPCTEST', False)
RESTRICT_RPCTEST = getattr(settings, 'RPC4DJANGO_RESTRICT_RPCTEST', False)
HTTP_ACCESS_CREDENTIALS = getattr(settings,
                                  'RPC4DJANGO_HTTP_ACCESS_CREDENTIALS', False)
HTTP_ACCESS_ALLOW_ORIGIN = getattr(settings,
                                   'RPC4DJANGO_HTTP_ACCESS_ALLOW_ORIGIN', '')


def get_content_type(request):
    """Return the MIME content type giving the request

    Return `None` if unknown.
    """

    if hasattr(request, 'content_type'):
        conttype = request.content_type

    else:
        header = request.META.get('CONTENT_TYPE', None)

        if not header:
            return None

        conttype = header.partition(';')[0]  # remove ";charset="

    return conttype


def check_request_permission(request, request_format='xml'):
    '''
    Checks whether this user has permission to call a particular method
    This method does not check method call validity. That is done later

    **Parameters**

    - ``request`` - a django HttpRequest object
    - ``request_format`` - the request type: 'json' or 'xml'

    Returns ``False`` if permission is denied and ``True`` otherwise
    '''

    user = getattr(request, 'user', None)
    methods = dispatcher.list_methods()
    method_name = dispatcher.get_method_name(request.body, request_format)
    response = True

    for method in methods:
        if method.name == method_name:
            # this is the method the user is calling
            # time to check the permissions
            if method.permission is not None:
                logger.debug('Method "%s" is protected by permission "%s"'
                             % (method.name, method.permission))
                if user is None:
                    # user is only none if not using AuthenticationMiddleware
                    logger.warn('AuthenticationMiddleware is not enabled')
                    response = False
                elif not user.has_perm(method.permission):
                    # check the permission against the permission database
                    logger.info('User "%s" is NOT authorized' % (str(user)))
                    response = False
                else:
                    logger.debug('User "%s" is authorized' % (str(user)))
            elif method.login_required:
                logger.debug('Method "%s" is protected by login_required'
                             % method.name)
                if user is None:
                    # user is only none if not using AuthenticationMiddleware
                    logger.warn('AuthenticationMiddleware is not enabled')
                    response = False
                elif user.is_anonymous():
                    # ensure the user is logged in
                    logger.info('User "%s" is NOT authorized' % (str(user)))
                    response = False
                else:
                    logger.debug('User "%s" is authorized' % (str(user)))
            else:
                logger.debug('Method "%s" is unprotected' % (method.name))

            break

    return response


def is_xmlrpc_request(request):
    '''
    Determines whether this request should be served by XMLRPC or JSONRPC

    Returns ``True`` if this is an XML request and false for JSON

    1. If there is no post data, display documentation
    2. content-type = text/xml or application/xml => XMLRPC
    3. content-type contains json or javascript => JSONRPC
    4. Try to parse as xml. Successful parse => XMLRPC
    5. JSONRPC

    '''

    conttype = get_content_type(request) or ''

    # check content type for obvious clues
    if conttype == 'text/xml' or conttype == 'application/xml':
        return True
    elif conttype.find('json') >= 0 or conttype.find('javascript') >= 0:
        return False

    if LOG_REQUESTS_RESPONSES:
        logger.info('Unrecognized content-type "%s"' % conttype)
        logger.info('Analyzing rpc request data to get content type')

    # analyze post data to see whether it is xml or json
    # this is slower than if the content-type was set properly
    # checking JSON is safer than XML because of entity expansion
    try:
        json.loads(request.body.decode('utf-8'))
        return False
    except ValueError:
        return True


@csrf_exempt
def serve_rpc_request(request):
    '''
    Handles rpc calls based on the content type of the request or
    returns the method documentation page if the request
    was a GET.

    **Parameters**

    ``request``
        the Django HttpRequest object

    '''

    if request.method == "POST" and int(request.META.get('CONTENT_LENGTH', 0)) > 0:
        # Handle POST request with RPC payload

        if LOG_REQUESTS_RESPONSES:
            body_text = request.body.decode('utf-8')
            logger.debug('Incoming request: %s' % body_text)

        if is_xmlrpc_request(request):
            if RESTRICT_XML:
                raise Http404

            if not check_request_permission(request, 'xml'):
                return HttpResponseForbidden()

            resp = dispatcher.xmldispatch(request.body, request=request)
            response_type = 'text/xml'
        else:
            if RESTRICT_JSON:
                raise Http404

            if not check_request_permission(request, 'json'):
                return HttpResponseForbidden()

            resp = dispatcher.jsondispatch(request.body, request=request)
            response_type = 'application/json'

        if LOG_REQUESTS_RESPONSES:
            logger.debug('Outgoing %s response: %s' % (response_type, resp))

        return HttpResponse(resp, response_type)
    elif request.method == 'OPTIONS':
        # Handle OPTIONS request for "preflighted" requests
        # see https://developer.mozilla.org/en/HTTP_access_control

        response = HttpResponse('', 'text/plain')

        origin = request.META.get('HTTP_ORIGIN', 'unknown origin')
        response['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        response['Access-Control-Max-Age'] = 0
        response['Access-Control-Allow-Credentials'] = \
            str(HTTP_ACCESS_CREDENTIALS).lower()
        response['Access-Control-Allow-Origin'] = HTTP_ACCESS_ALLOW_ORIGIN

        response['Access-Control-Allow-Headers'] = \
            request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '')

        if LOG_REQUESTS_RESPONSES:
            logger.debug('Outgoing HTTP access response to: %s' % (origin))

        return response
    else:
        # Handle GET request

        if RESTRICT_METHOD_SUMMARY:
            # hide the documentation by raising 404
            raise Http404

        # show documentation
        methods = dispatcher.list_methods()
        template_data = {
            'methods': methods,
            'url': request.path,

            # rpc4django version
            'version': version(),

            # restricts the ability to test the rpc server from the docs
            'restrict_rpctest': RESTRICT_RPCTEST,
        }

        return render(
            request,
            'rpc4django/rpcmethod_summary.html',
            template_data
        )
