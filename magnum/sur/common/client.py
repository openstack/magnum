'''
Created on Aug 7, 2015

'''

import copy
import hashlib
import logging
import requests

from oslo_utils import encodeutils

LOG = logging.getLogger(__name__)
USER_AGENT = 'python-surclient'
SENSITIVE_HEADERS = ('X-Auth-Token',)


class SURHTTPClient(object):

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint

        self.auth_url = kwargs.get('auth_url')
        self.auth_token = kwargs.get('token')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')

    def safe_header(self, name, value):
        if name in SENSITIVE_HEADERS:
            value = hashlib.sha1(value.encode("utf-8")).hexdigest()
            return (encodeutils.safe_decode(name), "{SHA1}%s" % value)
        else:
            return (encodeutils.safe_decode(name),
                    encodeutils.safe_decode(value))

    def _log_curl_request(self, method, url, kwargs):
        curl = ['curl -g -i -X %s' % method]

        curl.append('%s%s' % (self.endpoint, url))

        for (key, value) in kwargs.get('headers').items():
            curl.append('-H \'%s: %s\'' % self.safe_header(key, value))

        if 'data' in kwargs:
            curl.append('-d \'%s\'' % kwargs.get('data'))

        LOG.debug(' '.join(curl))

    def _http_request(self, url, method, **kwargs):
        # reuse original headers in case of redirect
        kwargs['headers'] = copy.deepcopy(kwargs.get('headers', {}))
        kwargs['headers'].setdefault('User-Agent', USER_AGENT)
        if self.auth_token:
            kwargs['headers'].setdefault('X-Auth-Token', self.auth_token)
        if self.auth_url:
            kwargs['headers'].setdefault('X-Auth-Url', self.auth_url)

        self._log_curl_request(method, url, kwargs)

        try:
            resp = requests.request(method, self.endpoint + url, **kwargs)
        except Exception as ex:
            raise Exception

        return resp

    def credentials_headers(self):
        creds = {}
        if self.username:
            creds['X-Auth-User'] = self.username
        if self.password:
            creds['X-Auth-Key'] = self.password
        return creds

    def _get_response_json_body(self, resp):
        body = None
        if 'application/json' in resp.headers.get('content-type', ''):
            try:
                body = resp.json()
            except ValueError, e:
                LOG.error(e)
        return body

    def simple_request(self, method, url, request_type='json', **kwargs):
        kwargs.setdefault('headers', {})
        if request_type == 'json':
            kwargs['headers'].setdefault('Content-Type', 'application/json')
            kwargs['headers'].setdefault('Accept', 'application/json')
        elif request_type == 'raw':
            kwargs['headers'].setdefault('Content-Type',
                                         'application/octet-stream')

        return self._http_request(url, method, **kwargs)

    def raw_request(self, method, url, **kwargs):
        return self.simple_request(method, url, 'raw', **kwargs)

    def json_request(self, method, url, **kwargs):
        resp = self.simple_request(method, url, 'json', **kwargs)
        body = self._get_response_json_body(resp)
        return body

    def client_request(self, method, url, **kwargs):
        resp = self.json_request(method, url, **kwargs)
        return resp

    def get(self, url, **kwargs):
        return self.client_request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self.client_request('POST', url, **kwargs)

    def put(self, url, **kwargs):
        return self.client_request('PUT', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.client_request('DELETE', url, **kwargs)


def construct_sur_client(endpoint=None, **kwargs):
    return SURHTTPClient(endpoint=endpoint, **kwargs)
