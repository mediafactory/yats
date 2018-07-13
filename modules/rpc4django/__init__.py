from .rpcdispatcher import RPCDispatcher, rpcmethod   # noqa

_MAJOR = 0
_MINOR = 4
_PATCH = 0

__version__ = str(_MAJOR) + '.' + str(_MINOR) + '.' + str(_PATCH)


def version():
    '''
    Returns a string representation of the version
    '''
    return __version__


def version_tuple():
    '''
    Returns a 3-tuple of ints that represent the version
    '''
    return (_MAJOR, _MINOR, _PATCH)
