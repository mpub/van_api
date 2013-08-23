#!/usr/bin/python
import logging
import tempfile
from pprint import pprint

import van_api

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

logging.info("Connection to the API")
credentials = van_api.ClientCredentialsGrant('mxvsm129bm7RgcGRYedzLersZXGQSwQjMiyilovZL7A', 'hSBADtfwcEnxeatj')
api = van_api.API('api.metropublisher.com', credentials)

# get list of files
logging.info("Getting Files")
result = api.GET('/1/files')
pprint(result)

# get file metadata
url_to_first_file = result['items'][0][0]
logging.info("Getting Metadata of the first file from %s" % url_to_first_file)
result = api.GET(url_to_first_file)
pprint(result)

# Download data
logging.info("Downloading file data to a temproray file")
with tempfile.TemporaryFile() as myfile:
    api.GET(result['download_url'], myfile)
    bytes_written = myfile.tell()
logging.info("Downloaded %s bytes" % bytes_written)
