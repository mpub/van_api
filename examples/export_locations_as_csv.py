#!/usr/bin/python
"""Export Locations to a CSV file.

This example downloads all location data for all locations to a CSV file on stdout
"""

import sys
import csv
import json
import urllib
import logging

import van_api

# Configuration
INSTANCE_ID = 1
GEONAME_USER = 'demo' # A registered username at http://www.geonames.org/ 
API_KEY = 'mxvsm129bm7RgcGRYedzLersZXGQSwQjMiyilovZL7A'
API_SECRET = 'hSBADtfwcEnxeatj'

def get_all_items(api, start_url):
    """Return an iterator of all the items in a collection
    
    Pages through all available URLS
    """
    result = api.GET(start_url)
    page = 1
    while True:
        items = result['items']
        logging.info('got page {} ({} items), processing...'.format(page, len(items)))
        page += 1
        for i in items:
            yield i
        next_url = result.get('next')
        if not next_url:
            break
        if '?' not in next_url:
            next_url = start_url.split('?')[0] + '?' + next_url
        result = api.GET(next_url)

def to_csv_value(in_loc):
    """Convert location object from the API to dict of UTF-8 encoded bytes."""
    out_loc = {}
    for k, v in in_loc.items():
        if v is None:
            v = u''
        elif isinstance(v, list):
            v = [unicode(i) for i in v]
            v = u'|'.join(v)
        elif not isinstance(v, basestring):
            v = unicode(v)
        out_loc[k] = v.encode('utf-8')
    return out_loc

_GEONAMES_CACHE = {}
def get_one_geoname(geoname_id):
    """Get geoname info from http://api.geonames.org/"""
    geoname = _GEONAMES_CACHE.get(geoname_id)
    if geoname is None:
        geoname_url = 'http://api.geonames.org/getJSON?geonameId={}&username={}&style=full'.format(geoname_id, GEONAME_USER)
        geoname = urllib.urlopen(geoname_url)
        geoname = geoname.read()
        geoname = json.loads(geoname)
        _GEONAMES_CACHE[geoname_id] = geoname
    return geoname

def add_geoname_data(loc):
    """Merge some data from the geoname into the location dict"""
    geoname_id = loc['geoname_id']
    if geoname_id is None:
        geoname = {}
    else:
        geoname = get_one_geoname(geoname_id)
    loc['geoname_name'] = geoname.get('name')

def main():
    # setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

    # Get an API connection
    credentials = van_api.ClientCredentialsGrant(API_KEY, API_SECRET)
    api = van_api.API('api.metropublisher.com', credentials)

    fields = ['url', 'location_types']
    start_url = '/{}/locations?fields={}&rpp=100'.format(INSTANCE_ID, '-'.join(fields))

    csv_file = None
    count = 0
    for loc_url, location_types in get_all_items(api, start_url):
        count += 1
        # get full location info
        loc = api.GET(loc_url)
        add_geoname_data(loc)
        # cast everything to a string
        loc = to_csv_value(loc)
        if csv_file is None:
            # create our csv file writer if none already exists
            fieldnames = sorted(loc.keys())
            csv_file = csv.DictWriter(sys.stdout, fieldnames)
            # write headers
            headers = dict([(k, k) for k in loc])
            csv_file.writerow(headers)
        # write out one line of the CSV
        csv_file.writerow(loc)
    logging.info('Exported {} locations'.format(count))
    return 0

if __name__ == '__main__':
    sys.exit(main())
