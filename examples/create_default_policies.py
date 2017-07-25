#!/usr/bin/env python
#
# Create the default set of policies given the falco rules file.
# Existing policies with the same name are unchanged. New policies
# as needed will be added. Returns JSON representing the new
# policies created.
#

import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '..'))
from sdcclient import SdSecureClient

def usage():
    print 'usage: %s <sysdig-token>' % sys.argv[0]
    print 'You can find your token at https://secure.sysdig.com/#/settings/user'
    sys.exit(1)

#
# Parse arguments
#
if len(sys.argv) != 2:
    usage()

sdc_token = sys.argv[1]

#
# Instantiate the SDC client
#
sdclient = SdSecureClient(sdc_token, 'https://secure.sysdig.com')

res = sdclient.create_default_policies()

#
# Return the result
#
if res[0]:
    print json.dumps(res[1], indent=2)
else:
    print res[1]
    sys.exit(1)


