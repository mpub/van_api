#!/usr/bin/python
import logging
from pprint import pprint

import van_api

logging.basicConfig(level=logging.DEBUG)

# Connect to the API
# The example API key here allows using the http://demo.metropublisher.com/ api as a public user
# it's instance id is 1
credentials = van_api.ClientCredentialsGrant('mxvsm129bm7RgcGRYedzLersZXGQSwQjMiyilovZL7A', 'hSBADtfwcEnxeatj')
api = van_api.API('api.metropublisher.com', credentials)

# Get a list of the sections and print them
pprint("Getting Available Resources")
result = api.GET('/1')
pprint(result)

# Get a list of the sections and print them
pprint("Getting Sections")
result = api.GET('/1/sections?fields=title-urlname-url')
pprint(result)
