#!/usr/bin/python
import os.path
import uuid
import logging
from pprint import pprint

import van_api

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

# Connect to the API
# The example API key here allows using the http://demo.metropublisher.com/ api as a public user
# it's instance id is 1
credentials = van_api.ClientCredentialsGrant('YOUR_API_KEY', 'YOUR_API_SECRET')
iid = 'YOUR_API_ID'
api = van_api.API('api.metropublisher.com', credentials)

# get flag data
file_upload_uuid = uuid.uuid1()
here = os.path.dirname(__file__)
flag = os.path.join(here, 'littlevanguardistasflag.jpg')
flag_file = open(flag, 'rb')
try:
    flag_contents = flag_file.read()
except:
    flag_file.close()

print 'Putting metadata'
result = api.PUT('/%s/files/%s' % (iid, file_upload_uuid),
        {"title": "A Flag",
            "filename": "littlevanguardistasflag.jpg",
            "created": "2000-01-01T10:30:58",
            "modified": "2000-01-01T10:30:58"})
pprint(result)
print 'Putting binary data'
result = api.POST('/%s/files/%s' % (iid, file_upload_uuid),
        flag_contents, content_type="image/jpeg")
pprint(result)
print 'Getting metadata'
result = api.GET('/%s/files/%s' % (iid, file_upload_uuid))
pprint(result)
