'''
This module implements a JSON 1.0 compatible dispatcher

see http://json-rpc.org/wiki/specification
'''

import json

# indent the json output by this many characters
# 0 does newlines only and None does most compact
# This is consistent with SimpleXMLRPCServer output
JSON_INDENT = 0

# These error codes may be defined by the json-rpc spec at a later date
# see http://json-rpc.org/wd/JSON-RPC-1-1-WD-20060807.html#ErrorObject
JSONRPC_SERVER_ERROR = 100
JSONRPC_PARSE_ERROR = 101
JSONRPC_BAD_CALL_ERROR = 102
JSONRPC_SEQUENCE_ERROR = 103
JSONRPC_SERVICE_ERROR = 104
JSONRPC_PROCEDURE_NOT_FOUND_ERROR = 105

try:
    # Python2
    basestring
except NameError:
    # Python3
    basestring = str


class JSONRPCException(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code


class JSONRPCDispatcher(object):
    '''
    This class can be used encode and decode jsonrpc messages, dispatch
    the requested method with the passed parameters, and return any response
    or error.
    '''

    def __init__(self, json_encoder=None):
        self.json_encoder = json_encoder
        self.methods = {}

    def register_function(self, method, external_name):
        '''
        Registers a method with the jsonrpc dispatcher.

        This method can be called later via the dispatch method.
        '''
        self.methods[external_name] = method

    def _encode_result(self, jsonid, result, error):
        res = {'jsonrpc': '2.0', 'id': jsonid}

        if error is None:
            res['result'] = result
        else:
            res['error'] = error
            res['error']['name'] = 'JSONRPCError'
        try:
            return json.dumps(res, indent=JSON_INDENT, cls=self.json_encoder)
        except:
            err = {'message': 'failed to encode return value',
                   'code': JSONRPC_SERVICE_ERROR,
                   'name': 'JSONRPCError'}

            res['result'] = None
            res['error'] = err
            return json.dumps(res, indent=JSON_INDENT, cls=self.json_encoder)

    def dispatch(self, json_data, **kwargs):
        '''
        Verifies that the passed json encoded string
        is in the correct form according to the json-rpc spec
        and calls the appropriate Python method

        **Checks**

         1. that the string encodes into a javascript Object (dictionary)
         2. that 'method' and 'params' are present
         3. 'method' must be a javascript String type
         4. 'params', if passed, must be a javascript Array type

        Returns the JSON encoded response
        '''

        try:
            # attempt to do a json decode on the data
            jsondict = json.loads(json_data)
        except ValueError:
            return self._encode_result('', None, {
                'message': 'JSON decoding error',
                'code': JSONRPC_PARSE_ERROR})

        if not isinstance(jsondict, dict):
            # verify the json data was a javascript Object which gets decoded
            # into a python dictionary
            return self._encode_result('', None, {
                'message': 'Cannot decode to a javascript Object',
                'code': JSONRPC_BAD_CALL_ERROR})

        if 'method' not in jsondict:
            # verify the dictionary contains the method key
            return self._encode_result(jsondict.get('id', ''), None, {
                'message': "JSONRPC requests must have the 'method' attribute.",
                'code': JSONRPC_BAD_CALL_ERROR})

        if not isinstance(jsondict['method'], basestring):
            return self._encode_result(jsondict.get('id', ''), None, {
                'message': 'method must be a javascript String',
                'code': JSONRPC_BAD_CALL_ERROR})

        if 'params' in jsondict and not isinstance(jsondict['params'], list):
            return self._encode_result(jsondict.get('id', ''), None, {
                'message': 'params must be a javascript Array',
                'code': JSONRPC_BAD_CALL_ERROR})

        if jsondict['method'] in self.methods:
            try:
                try:
                    result = self.methods[jsondict.get('method')](*jsondict.get('params', []), **kwargs)
                except TypeError:
                    # Catch unexpected keyword argument error
                    result = self.methods[jsondict.get('method')](*jsondict.get('params', []))
            except JSONRPCException as e:
                # Custom message and code
                return self._encode_result(jsondict.get('id', ''), None, {
                    'message': e.message, 'code': e.code})
            except Exception as e:
                # this catches any error from the called method raising
                # an exception to the wrong number of params being sent
                # to the method.
                return self._encode_result(jsondict.get('id', ''), None, {
                    'message': repr(e),
                    'code': JSONRPC_SERVICE_ERROR})
            return self._encode_result(jsondict.get('id', ''), result, None)
        else:
            return self._encode_result(jsondict.get('id', ''), None, {
                'message': 'method "%s" is not supported' % jsondict['method'],
                'code': JSONRPC_PROCEDURE_NOT_FOUND_ERROR})
