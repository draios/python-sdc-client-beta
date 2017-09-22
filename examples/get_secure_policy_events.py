#!/usr/bin/env python
#
# Get all policy events for a given time range or in the last N seconds.
# The events are written in jsonl format to stdout.
#
# If --summarize is provided, summarize the policy events by sanitized
# (removing container ids when present) description and print the
# descriptions by decreasing frequency.  This allows you to see which policy
# events are occurring most often.
#
# Progress information is written to standard error.
#

import os
import sys
import json
import operator
import re
import getopt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '..'))
from sdcclient import SdSecureClient

def usage():
    print 'usage: %s [-s|--summarize] [-l|--limit <limit>] <sysdig-token> [<duration sec>|<from sec> <to sec>]' % sys.argv[0]
    print '-s|--summarize: group policy events by sanitized output and print by frequency'
    print '-l|--limit: with -s, only print the first <limit> outputs'
    print 'You can find your token at https://secure.sysdig.com/#/settings/user'
    sys.exit(1)

try:
    opts, args = getopt.getopt(sys.argv[1:],"sl:",["summarize","limit="])
except getopt.GetoptError:
    usage()

summarize = False
limit = 0
for opt, arg in opts:
    if opt in ("-s", "--summarize"):
        summarize = True
    elif opt in ("-l", "--limit"):
        limit = int(arg)
#
# Parse arguments
#
if len(args) < 2:
    usage()

sdc_token = args[0]

duration = None
from_sec = None
to_sec = None

if len(args) == 2:
    duration = args[1]
elif len(args) == 3:
    from_sec = args[1]
    to_sec = args[2]
else:
    usage()

#
# Instantiate the SDC client
#
sdclient = SdSecureClient(sdc_token, 'https://secure.sysdig.com')

if duration is not None:
    res = sdclient.get_policy_events_duration(duration)
else:
    res = sdclient.get_policy_events_range(from_sec, to_sec)

all_outputs = dict()

while True:

    #
    # Return the result
    #
    if not res[0]:
        print res[1]
        sys.exit(1)

    if len(res[1]['data']['policyEvents']) == 0:
        break

    sys.stderr.write("offset={}\n".format(res[1]['ctx']['offset']))

    for event in res[1]['data']['policyEvents']:
        if summarize:
            sanitize_output = re.sub(r'\S+\s\(id=\S+\)', '', event['output'])
            all_outputs[sanitize_output] = all_outputs.get(sanitize_output, 0) + 1
        else:
            sys.stdout.write(json.dumps(event) + "\n")

    res = sdclient.get_more_policy_events(res[1]['ctx'])

if summarize:
    sorted = sorted(all_outputs.items(), key=operator.itemgetter(1), reverse=True)
    count = 0
    for val in sorted:
        count += 1
        sys.stdout.write("{} {}\n".format(val[1], val[0]))
        if limit != 0 and count > limit:
            break

