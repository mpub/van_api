from unittest import TestCase
import mock

def mock_API():
    from van_api import API
    return mock.Mock(spec_set=API)

class TestCredentials(TestCase):

    def test_access_token(self):
        from van_api import Credentials
        one = Credentials()
        self.assertRaises(NotImplementedError, one.access_token, mock_API())

    def test_token(self):
        from van_api import Credentials
        one = Credentials()
        api = mock_API()
        result = one._token(api, dict(param='param value'), )
        api.retry.assert_called_once_with(
                api.http,
                'POST',
                '/oauth/token',
                host='go.vanguardistas.net',
                body='param=param+value',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                handler=api.handle
                )
        self.assertEqual(result, api.retry())


class TestClientCredentialsGrant(TestCase):

    @mock.patch('van_api.Credentials._token')
    def test_access_token(self, token):
        from van_api import ClientCredentialsGrant
        creds = ClientCredentialsGrant('key', 'secret')
        creds.access_token('api')
        token.assert_called_once_with('api', dict(
                grant_type='client_credentials',
                api_key="key",
                api_secret="secret"))


class TestAPI(TestCase):

    def _one(self, host='apihost', response=None, logger=None):
        try:
            from http.client import HTTPSConnection
        except ImportError:
            #python 2
            from httplib import HTTPSConnection
        from van_api import Credentials, API
        creds = mock.Mock(spec_set=Credentials)
        creds.access_token.return_value = 'my_token'
        conn = mock.Mock(spec_set=HTTPSConnection)
        if response is not None:
            resp = conn().getresponse()
            resp.getheaders.return_value = response['headers']
            resp.read.return_value = response['body']
            resp.status = response['status']
            resp.reason = response.get('reason', 'dummy reason')
            conn.reset_mock()
        return API(host, creds, logger=logger, conn_factory=conn)

    def test_init_defaults(self):
        try:
            from http.client import HTTPSConnection
        except ImportError:
            #python 2
            from httplib import HTTPSConnection
        import logging
        from van_api import API
        one = API('host', 'creds')
        self.assertEqual(one.host, 'host')
        self.assertEqual(one._creds, 'creds')
        self.assertEqual(one._conn, {})
        self.assertEqual(one.logger, logging)
        self.assertEqual(one._conn_factory, HTTPSConnection)

    def test_retry_no_exception(self):
        func = mock.Mock()
        api = self._one()
        result = api.retry(func, 55, a=42)
        func.assert_called_once_with(55, a=42)
        self.assertEqual(func(), result)

    def test_retry_logging(self):
        from van_api import Retryable
        import logging
        from mock import call
        func = mock.Mock()
        logger = mock.Mock(spec_set=logging.Logger)
        class MyException(Retryable):
            pass
        func.side_effect = MyException('oops')
        api = self._one(logger=logger)
        result = self.assertRaises(Exception, api.retry, func, 55, a=42)
        self.assertEqual(
                logger.exception.call_args_list,
                [call('Attempt 1 failed'),
                    call('Attempt 2 failed'),
                    call('Attempt 3 failed'),
                    call('Attempt 4 failed'),
                    call('Attempt 5 failed')])

    def test_retry_non_retryable_exception(self):
        func = mock.Mock()
        class MyException(Exception):
            pass
        func.side_effect = MyException('oops')
        api = self._one()
        self.assertRaises(MyException, api.retry, func, 55, a=42)
        func.assert_called_once_with(55, a=42)

    def test_retry_retryable_exception_exhausted(self):
        from van_api import Retryable
        from mock import call
        func = mock.Mock()
        class MyException(Retryable):
            pass
        func.side_effect = MyException('oops')
        api = self._one()
        self.assertRaises(MyException, api.retry, func, 55, a=42)
        self.assertEqual(func.call_args_list, [call(55, a=42)] * 5)

    def test_retry_retryable_wrapping_other_exception(self):
        import sys
        from van_api import Retryable
        from mock import call
        func = mock.Mock()
        class MyException(Exception):
            pass
        def side_effect(one, a=0):
            try:
                raise MyException()
            except:
                raise Retryable("A retryable error", exc_info=sys.exc_info())
        func.side_effect = side_effect
        api = self._one()
        self.assertRaises(MyException, api.retry, func, 55, a=42)
        self.assertEqual(func.call_args_list, [call(55, a=42)] * 5)

    def test_retry_retryable_exception_third_time_lucky(self):
        from van_api import Retryable
        from mock import call
        class MyException(Retryable):
            pass
        return_val = [MyException('oops'), MyException('oops')]
        def side_effect(b, a=0):
            if return_val:
                raise return_val.pop()
            return a + b
        func = mock.Mock()
        func.side_effect = side_effect
        api = self._one()
        self.assertEqual(42, api.retry(func, 2, a=40))
        self.assertEqual(func.call_args_list, [call(2, a=40)] * 3)

    def test_retry_bad_retryable_exception(self):
        from van_api import Retryable
        from mock import call
        func = mock.Mock()
        class MyException(Retryable):
            def reraise(self):
                pass # should raise
        func.side_effect = MyException('oops')
        api = self._one()
        # no infinite loops here
        self.assertRaises(AssertionError, api.retry, func, 55, a=42)

    def test_http_connect(self):
        one = self._one(host='myapi')
        one.handle = mock.Mock()
        self.assertEqual(one._conn, {})
        one.http('GET', '/')
        self.assertEqual(one._conn_factory.call_count, 1)
        self.assertEqual(one._conn['myapi'], one._conn_factory())

    def test_http_retryable_error_raised(self):
        from van_api import Retryable
        class Error(Exception):
            pass
        one = self._one()
        one._conn_factory().request.side_effect = Error('boom')
        try:
            one.http('GET', '/')
        except Retryable:
            import sys
            e = sys.exc_info()[1]
            self.assertTrue(isinstance(e.exc_info[1], Error))
            self.assertEqual(e.exc_info[0], Error)
        else:
            self.fail('Exceptiong not raised')

    def test_http_disconnect_on_error(self):
        from mock import Mock
        one = self._one()
        conn = Mock()
        conn.request.side_effect = Exception('boom')
        one._conn['myhost'] = conn
        self.assertRaises(Exception, one.http, 'GET', '/', host='myhost')
        self.assertEqual(one._conn, {})
        conn.close.assert_called_once_with()

    def test_http_log_on_error(self):
        import logging
        logger = mock.Mock(spec_set=logging.Logger)
        one = self._one(logger=logger)
        one._conn_factory().request.side_effect = Exception('boom')
        one._conn_factory.reset_mock()
        self.assertRaises(Exception, one.http, 'GET', '/')
        logger.info.assert_called_once_with('HTTP Connection Error', exc_info=True)

    def test_get(self):
        one = self._one()
        one.request = mock.Mock()
        result = one.GET('/')
        one.request.assert_called_once_with('GET', '/')
        self.assertEqual(result, one.request())

    def test_put(self):
        one = self._one()
        one.request = mock.Mock()
        result = one.PUT('/', 'data')
        one.request.assert_called_once_with('PUT', '/', 'data')
        self.assertEqual(result, one.request())

    def test_delete(self):
        one = self._one()
        one.request = mock.Mock()
        result = one.DELETE('/')
        one.request.assert_called_once_with('DELETE', '/')
        self.assertEqual(result, one.request())

    def test_patch(self):
        one = self._one()
        one.request = mock.Mock()
        result = one.PATCH('/', 'data')
        one.request.assert_called_once_with('PATCH', '/', 'data')
        self.assertEqual(result, one.request())

    def test_post(self):
        one = self._one()
        one.request = mock.Mock()
        result = one.POST('/', 'data')
        one.request.assert_called_once_with('POST', '/', 'data')
        self.assertEqual(result, one.request())

    def test_http_calls_handle(self):
        one = self._one(response=dict(
            headers=[('Header1', 'value'), ],
            reason='OK',
            body='',
            status=200))
        handle = mock.Mock()
        result = one.http('POST', '/', handler=handle)
        handle.assert_called_once_with(
                {'body': None, 'headers': None, 'host': None, 'url': '/', 'method': 'POST'},
                {'body': '', 'headers': [('Header1', 'value'), ], 'reason': 'OK', 'status': 200})
        self.assertEqual(result, handle())

    def test_handle_ok(self):
        one = self._one()
        result = one.handle('request', dict(
            headers=[],
            body='',
            status=200))
        self.assertEqual(result, None)

    def test_handle_ok_with_data(self):
        one = self._one()
        result = one.handle('request', dict(
            headers=[('content-type', 'application/json', )],
            body='123',
            status=200))
        self.assertEqual(result, 123)

    def test_handle_ok_with_unicode_data(self):
        from van_api import _unicode
        one = self._one()
        result = one.handle('request', dict(
            headers=[('content-type', 'application/json', )],
            body='"unicode"',
            status=200))
        self.assertTrue(isinstance(result, _unicode))
        self.assertEqual(result, _unicode('unicode'))

    def test_handle_error(self):
        from van_api import APIError
        one = self._one()
        self.assertRaises(APIError, one.handle, 'request', dict(
            headers=[],
            body='',
            status=500))

    def test_handle_error_with_data(self):
        from van_api import APIError
        try:
            import json
        except ImportError:
            import simplejson as json
        one = self._one()
        self.assertRaises(APIError, one.handle, 'request', dict(
            headers=[('content-type', 'application/json')],
            body=json.dumps({'error': 'bad_parameters',
                    'error_description': 'Developer description of error',
                    'error_uri': 'http://example.com/errorpage.html',
                    'error_info': {'key': 'value'}}),
            status=400))

    def test_handle_retry_on_503(self):
        from van_api import Retryable
        one = self._one()
        self.assertRaises(Retryable, one.handle, 'request', dict(
            headers=[('content-type', 'application/json', )],
            body='123',
            status=503))

    def test_handle_retry_on_401(self):
        from van_api import Retryable
        one = self._one()
        self.assertEqual(one._access_token, None)
        one._access_token = 'token'
        self.assertRaises(Retryable, one.handle, 'request', dict(
            headers=[('content-type', 'application/json', )],
            body='123',
            status=401))
        self.assertEqual(one._access_token, None)

    def test_get_access_token(self):
        one = self._one()
        self.assertEqual(one._access_token, None)
        result = one._get_access_token()
        one._creds.access_token.assert_called_once_with(one)
        self.assertEqual(one._access_token, result)
        self.assertEqual(one._access_token, one._creds.access_token())

    def test_get_access_token_cached(self):
        one = self._one()
        one._access_token = 'cached'
        result = one._get_access_token()
        self.assertFalse(one._creds.access_token.called)
        self.assertEqual(one._access_token, 'cached')

    @mock.patch('van_api.API._get_access_token')
    @mock.patch('van_api.API.retry')
    def test_request_ok_data(self, retry, _get_access_token):
        _get_access_token.return_value = {
                'token_type': 'bearer',
                'access_token': 'value'}
        one = self._one()
        result = one.request('PUT', '/', 123)
        _get_access_token.assert_called_once_with()
        retry.assert_called_once_with(
                one.http,
                'PUT',
                '/',
                body='123',
                headers={'Content-Type': 'application/json',
                    'Authorization': 'bearer value'},
                handler=one.handle
                )
        self.assertEqual(result, retry())

    @mock.patch('van_api.API._get_access_token')
    @mock.patch('van_api.API.retry')
    def test_request_ok_no_data(self, retry, _get_access_token):
        _get_access_token.return_value = {
                'token_type': 'bearer',
                'access_token': 'value'}
        one = self._one()
        result = one.request('GET', '/')
        _get_access_token.assert_called_once_with()
        retry.assert_called_once_with(
                one.http,
                'GET',
                '/',
                body=None,
                headers={'Authorization': 'bearer value'},
                handler=one.handle
                )
        self.assertEqual(result, retry())
