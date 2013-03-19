"""Vanguardistas API client library

This is a thin layer over the python HTTP library to simplify access to the
Vanguardistas APIs. It provides the functionality:

    * Serialization and deserialization of data
    * Convert API errors into python exceptions
    * Retrieving/renewing access tokens as required
    * Re-trying requests if possible on various errors
"""

import sys
import logging
from pprint import pformat

try:
    from json import loads as _json_loads
    from json import dumps as _json_dumps
except ImportError:
    # python 2.5
    from simplejson import dumps as _json_dumps
    from simplejson import loads as _sj_json_loads
    def _json_loads(data):
        return _sj_json_loads(unicode(data))

_PY3 = sys.version_info[0] == 3

if _PY3:
    from urllib.parse import urlencode
    import http.client as httplib
else:
    from urllib import urlencode
    import httplib

if _PY3:
    _unicode = str
else:
    _unicode = unicode

if _PY3:
    def _reraise(exc_info):
        raise exc_info[1].with_traceback(exc_info[2])
else:
    exec("""def _reraise(exc_info):
    raise exc_info[0], exc_info[1], exc_info[2]
""")


class APIError(Exception):

    def __init__(self,
            request,
            response,
            error,
            description=None,
            info=None,
            url=None):
        self.request = request
        self.response = response
        self.error = error
        self.description = description
        self.info = info
        self.url = url
        msg = error
        if description:
            msg = '%s: %s\n%s' % (msg, description, pformat(info))
        Exception.__init__(self, msg)

class Retryable(Exception):
    """Represents a caught, but retryable error"""

    def __init__(self, msg, exc_info=None):
        self.exc_info = exc_info
        Exception.__init__(self, msg)

    def reraise(self):
        if self.exc_info is not None:
            _reraise(self.exc_info)
        raise

class _HTTPConnection(object):
    """Mixing class deailing with a single HTTP/HTTPS connection.

    Handles connect/disconnect, requests and retries for the connection.
    """

    _conn = None
    _conn_factory = None

    def __init__(self, host, conn_factory=httplib.HTTPSConnection, logger=logging):
        self.host = host
        self.logger = logger
        self._conn_factory = conn_factory

    def http(self, method, url, body=None, headers=None, handler=None):
        """Send a single HTTP request to the API.

        This is a low level method. It fails on all errors.
        """
        conn = self._get_conn()
        request = dict(method=method, host=self.host, url=url, body=body, headers=headers)
        if self.logger is not None:
            self.logger.debug('REQUEST:\n%s', pformat(request))
        try:
            conn.request(method, url, body=body, headers=headers)
            resp = conn.getresponse()
            response = dict(
                    status = resp.status,
                    headers = resp.getheaders(),
                    body = resp.read(),
                    reason = resp.reason)
        except:
            self._disconnect()
            if self.logger is not None:
                self.logger.info("HTTP Connection Error", exc_info=True)
            raise Retryable('HTTP Connection Error', exc_info=sys.exc_info())
        if self.logger is not None:
            self.logger.debug('RESPONSE:\n%s', pformat(response))
        if handler is not None:
            response = handler(request, response)
        return response

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        self._conn = self._conn_factory(self.host)
        return self._get_conn()

    def http_retry(self, *args, **kw):
        """Run an http query, retrying on retriable errors"""
        attempt = 1
        while True:
            try:
                return self.http(*args, **kw)
            except Retryable:
                if self.logger is not None:
                    self.logger.warn('Attempt %s failed',
                            attempt,
                            exc_info=True)
                if attempt >= 5:
                    exc = sys.exc_info()[1]
                    exc.reraise()
                    raise AssertionError("Bad retryable exception: %s" % exc)
            attempt += 1

    def _disconnect(self):
        conn = self._conn
        self._conn = None
        if conn is not None:
            conn.close()


class Credentials(object):
    """Abstract class representing credentials to access the API"""

    def __init__(self, host='go.vanguardistas.net', **kw):
        self.conn = _HTTPConnection(host, **kw)

    def access_token(self, api):
        """This method is called to get the access token.

        It must raise an error if an access token is not available.
        """
        raise NotImplementedError

    def _token(self, api, data):
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.conn.http_retry('POST', '/oauth/token',
                body=data,
                headers=headers,
                handler=api.handle)


class ClientCredentialsGrant(Credentials):

    def __init__(self, api_key, api_secret, **kw):
        Credentials.__init__(self, **kw)
        self.api_key = api_key
        self.api_secret = api_secret

    def access_token(self, api):
        data = {'grant_type': 'client_credentials',
                'api_key': self.api_key,
                'api_secret': self.api_secret}
        return self._token(api, data)


class API(_HTTPConnection):
    """A proxy object for the MP api."""

    _access_token = None

    def __init__(self, host, credentials=None, logger=logging, default_headers=None, **kw):
        self.conn = _HTTPConnection(host, logger=logger, **kw)
        self.logger = logger
        self._creds = credentials
        if default_headers is None:
            default_headers = {}
        self.default_headers = default_headers

    def GET(self, url):
        """GET a resource"""
        return self.request('GET', url)

    def PUT(self, url, data):
        """PUT data to a resource"""
        return self.request('PUT', url, data)

    def DELETE(self, url):
        """DELETE a resource"""
        return self.request('DELETE', url)

    def POST(self, url, data, content_type=None):
        """POST a resource"""
        return self.request('POST', url, data, content_type=content_type)

    def PATCH(self, url, data):
        """PATCH a resource"""
        return self.request('PATCH', url, data)

    def request(self, method, url, data=None, content_type=None):
        """Make an HTTP request to the API.

        The request will be retried on retryable errors (e.g. HTTP connection
        issues).

        If there is no access token yet the credentials will be asked for one.
        This will also occur with expired tokens. Access tokens will be cached
        for later requests.
        """
        access_token = self._get_access_token()
        headers = self.default_headers.copy()
        if access_token is not None:
            headers['Authorization'] = self._auth_header(access_token)
        data, data_headers = self._serialize(data, content_type)
        headers.update(data_headers)
        return self.conn.http_retry(method, url, body=data, headers=headers, handler=self.handle)

    def handle(self, request, response):
        handler = getattr(self, '_handle_status_%s' % response['status'], self._handle_error)
        return handler(request, response)

    def _handle_error(self, request, response):
        data = {'error': response['status']}
        if response['body']:
            content_type = self._get_header('Content-Type', response['headers'])
            data = self._deserialize(response['body'], content_type)
        raise APIError(
                request,
                response,
                data['error'],
                data.get('error_description'),
                data.get('error_info'),
                data.get('error_url'))

    def _handle_status_503(self, request, response):
        raise Retryable("Service temporarily unavailable")

    def _handle_status_401(self, request, response):
        self._access_token = None
        raise Retryable("Expired token?") # XXX - have the 401 method decide if the token was expired or not

    def _handle_status_200(self, request, response):
        data = None
        if response['body']:
            content_type = self._get_header('Content-Type', response['headers'])
            data = self._deserialize(response['body'], content_type)
        return data

    _handle_status_201 = _handle_status_200

    def _get_access_token(self):
        if self._access_token is not None:
            return self._access_token
        if self._creds is None:
            return None
        self._access_token = self._creds.access_token(self)
        return self._get_access_token()

    def _auth_header(self, token):
        assert token['token_type'] == 'bearer'
        return 'bearer %s' % token['access_token']

    def _serialize(self, data, content_type):
        if data is None:
            return None, {}
        if content_type is None:
            data = _json_dumps(data)
            content_type = 'application/json'
        return data, {'Content-Type': content_type}

    def _get_header(self, header, headers):
        header = header.lower()
        for k, v in headers:
            if k.lower() == header:
                return v

    def _deserialize(self, data, content_type):
        if _PY3:
            data = data.decode('ascii')
        return _json_loads(data)
