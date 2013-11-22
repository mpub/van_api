#!/usr/bin/python
"""Example of archiving an MP site to the filesystem.

This script will spider a Metropublisher instance, download as much as it can
and write it out to the filesystem.

This example probably does not work on Windows, help appreciated...
"""

import os
import sys
import datetime
import logging
import tempfile
from urlparse import urlparse
from pprint import pprint
import json

import van_api

API_KEY = 'mxvsm129bm7RgcGRYedzLersZXGQSwQjMiyilovZL7A'
API_SECRET = 'hSBADtfwcEnxeatj'
START_URL = '/1'

def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError:
        pass

class Spider:

    def __init__(self, api, start_url, outdir):
        self.api = api
        self.start_url = start_url
        self.outdir = outdir

    def run(self):
        todo_urls = set([self.start_url])
        seen_urls = set([])
        while todo_urls:
            self.spider_one(seen_urls, todo_urls)

    def get_outfile(self, url):
        url = urlparse(url)
        path = url.path[1:] # remove leading /
        outfile = os.path.join(self.outdir, path) #not working on windows??
        mkdirs(os.path.dirname(outfile))
        return outfile

    def http_handler(self, request, resp):
        headers = resp.getheaders()
        for h, v in headers:
            if h.lower() == 'content-type':
                content_type = v.split(';')[0].strip()
                break
        outfile = self.get_outfile(request['url'])
        if content_type == 'application/json':
            body = resp.read()
            outfile = '%s.json' % outfile
            with open(outfile, 'wb') as f:
                f.write(body)
        else:
            body = None
            with open(outfile, 'wb') as f:
                van_api.write_body_to_file(resp, f)
        return dict(
                status=resp.status,
                headers=headers,
                body=body,
                reason=resp.reason)

    def spider_one(self, seen_urls, todo_urls):
        url = todo_urls.pop()
        logging.info('Spidering: %s' % url)
        assert url not in seen_urls
        seen_urls.add(url)
        go_urls = set([])
        resp = self.api.request('GET', url, http_handler=self.http_handler)
        if resp is not None:
            # look for urls in the response
            if 'download_url' in resp:
                go_urls.add(resp['download_url'])
            if 'items' in resp:
                for item in resp['items']:
                    if isinstance(item, list):
                        url = item[0]
                    else:
                        url = item['url']
                    go_urls.add(url)
        todo_urls.update(go_urls - seen_urls)

def connect(api_key, api_secret, endpoint='api.metropublisher.com'):
    logging.info("Connection to the API")
    credentials = van_api.ClientCredentialsGrant(api_key, api_secret)
    return van_api.API(endpoint, credentials)

def get_outdir():
    outdir = 'MP-export-%s' % datetime.datetime.now().isoformat()
    return os.path.join(os.curdir, outdir)

def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
    logging.info('Connecting to API')
    api = connect(API_KEY, API_SECRET)
    outdir = get_outdir()
    logging.info('Saving result to %s' % outdir)
    s = Spider(api, START_URL, outdir)
    s.run()

if __name__ == '__main__':
    main()
