#!/usr/bin/env python
#
# Print all connected agents, each with list of available metadata (e.g. tags).
#

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '..'))
from sdcclient import SdcClient

#
# Parse arguments
#
if len(sys.argv) < 2:
    print 'usage: %s <sysdig-token> <filter>' % sys.argv[0]
    print 'You can find your token at https://app.sysdigcloud.com/#/settings/user'
    sys.exit(1)

sdc_token = sys.argv[1]

#
# Get filter from parameters (e.g. "cloudProvider.tag.Name = 'something'")
#
filter = sys.argv[2] if len(sys.argv) == 3 else None

sdclient = SdcClient(sdc_token)

#
# Get all available metadata
#
res = sdclient.get_metrics()
if res[0]:
    metrics = res[1]
    metadata = []

    for metricId in metrics:
        if metrics[metricId].get('canGroupBy') and metricId.startswith('aws') == False:
            metadata.append(metricId)

else:
    print 'Error fetching metrics'
    print res[1]
    sys.exit(1)

#
# Prepare list of metrics with agent.id and all metadata
#
metrics = [ { 'id': 'host.mac' } ]
for m in metadata:
    if m != 'host.mac':
        metrics.append({ 'id': m })

start =     -600
end =       0
paging =    { 'from': 0, 'to': 9 }

#
# Get agents metadata
#
res = sdclient.get_data(metrics, start, end, filter = filter, paging = paging)
if res[0]:
    data = res[1].get('data')

    agentsMetadata = dict()

    for d in data:
        agentsMetadata[d.get('d')[0]] = d.get('d')
else:
    print 'Error fetching agents configuration'
    print res[1]
    sys.exit(1)

#
# Get agents configurations
#
res = sdclient.get_connected_agents()
if res[0]:
    agentsConfiguration = res[1]

    agents = []

    for agentConfiguration in agentsConfiguration:
        hostMac = agentConfiguration.get('machineId')
        if hostMac in agentsMetadata:
            agent = dict()
            agent.update(agentConfiguration)
            agent['metadata'] = agentsMetadata[hostMac]
            agents.append(agent)
        else:
            print 'Metadata for agent %s not found' % (hostMac)

    # Simple print of each agent
    for agent in agents:
        print agent
        print '---'
else:
    print 'Error fetching agents metadata'
    print res[1]
    sys.exit(1)
