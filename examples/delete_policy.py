#!/usr/bin/env python
#
# Delete a policy, by either id or name.
#

import os
import sys
import json
import getopt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '..'))
from sdcclient import SdSecureClient

def usage():
    print 'usage: %s [-i|--id <id>] [-n|--name <name>] <sysdig-token>' % sys.argv[0]
    print '-i|--id: the id of the policy to delete'
    print '-n|--name: the name of the policy to delete'
    print 'You can find your token at https://secure.sysdig.com/#/settings/user'
    sys.exit(1)

#
# Parse arguments
#
try:
    opts, args = getopt.getopt(sys.argv[1:],"i:n:",["id=","name="])
except getopt.GetoptError:
    usage()

id = ""
name = ""
for opt, arg in opts:
    if opt in ("-i", "--id"):
        id = arg
    elif opt in ("-n", "--name"):
        name = arg

if len(id) + len(name) == 0:
    usage()

if len(args) < 1:
    usage()

sdc_token = args[0]

#
# Instantiate the SDC client
#
sdclient = SdSecureClient(sdc_token, 'https://secure.sysdig.com')

if len(id) > 0:
    res = sdclient.delete_policy_id(id)
else:
    res = sdclient.delete_policy_name(name)

#
# Return the result
#
if res[0]:
    print json.dumps(res[1], indent=2)
else:
    print res[1]
    sys.exit(1)
