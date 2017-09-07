#!/bin/bash

set -euxo pipefail

SCRIPT=$(readlink -f $0)
SCRIPTDIR=$(dirname $SCRIPT)

export SDC_URL=https://secure-staging.sysdig.com

# we expect this to fail with 405. It only works for on-premise accounts.
set +e
OUT=`$SCRIPTDIR/../examples/set_secure_system_falco_rules.py $PYTHON_SDC_TEST_API_TOKEN $SCRIPTDIR/sample-falco-rules.yaml`
if [[ $? != 1 ]]; then
   echo "set_secure_system_falco_rules.py succeeded when it should have failed"
   exit 1
fi

if [[ "$OUT" != "status code 405" ]]; then
    echo "Unexpected output from set_secure_system_falco_rules.py: $OUT"
    exit 1
fi
set -e

# There's a known system falco rules file. Get it and compare it to the expected file
$SCRIPTDIR/../examples/get_secure_system_falco_rules.py $PYTHON_SDC_TEST_API_TOKEN > /tmp/falco_rules.yaml
diff /tmp/falco_rules.yaml $SCRIPTDIR/sample-falco-rules.yaml

NOW=$(date)
cat <<EOF > /tmp/test_apis_user_rules.yaml
- rule: My Rule as of $NOW
  desc: My Description
  condition: evt.type=open and fd.name="/tmp/some-file.txt"
  output: Impossible file opened
  priority: INFO
EOF

$SCRIPTDIR/../examples/set_secure_user_falco_rules.py $PYTHON_SDC_TEST_API_TOKEN /tmp/test_apis_user_rules.yaml
$SCRIPTDIR/../examples/get_secure_user_falco_rules.py $PYTHON_SDC_TEST_API_TOKEN > /tmp/falco_rules.yaml
diff /tmp/falco_rules.yaml /tmp/test_apis_user_rules.yaml

# Delete all policies and then get them. There should be none.
$SCRIPTDIR/../examples/delete_all_policies.py $PYTHON_SDC_TEST_API_TOKEN
OUT=`$SCRIPTDIR/../examples/list_policies.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"policies\": []"* ]]; then
    echo "Unexpected output after deleting all policies"
    exit 1
fi

# Create the default set of policies and then get them. There should
# be 1, corresponding to the system falco rule.
$SCRIPTDIR/../examples/create_default_policies.py $PYTHON_SDC_TEST_API_TOKEN
OUT=`$SCRIPTDIR/../examples/list_policies.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"name\": \"My Rule\""* ]]; then
    echo "Unexpected output after creating default policies"
    exit 1
fi

# Get that policy, change the name, and create a new duplicate policy.
OUT=`$SCRIPTDIR/../examples/get_policy.py $PYTHON_SDC_TEST_API_TOKEN "My Rule"`
MY_POLICY=$OUT
if [[ $OUT != *"\"name\": \"My Rule\""* ]]; then
    echo "Could not fetch policy with name \"My Rule\""
    exit 1
fi

NEW_POLICY=`echo $MY_POLICY | sed -e "s/My Rule/Copy Of My Rule/g" | sed -e 's/"id": [0-9]*,//' | sed -e 's/"version": [0-9]*/"version": null/'`
OUT=`echo $NEW_POLICY | $SCRIPTDIR/../examples/add_policy.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"name\": \"Copy Of My Rule\""* ]]; then
    echo "Could not create new policy"
    exit 1
fi

# Change the description of the new policy and update it.
MODIFIED_POLICY=`echo $MY_POLICY | sed -e "s/My Description/My New Description/g"`
OUT=`echo $MODIFIED_POLICY | $SCRIPTDIR/../examples/update_policy.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"description\": \"My New Description\""* ]]; then
    echo "Could not update policy \"Copy Of My Rule\""
    exit 1
fi

# Delete the new policy.
OUT=`$SCRIPTDIR/../examples/delete_policy.py --name "Copy Of My Rule" $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"name\": \"Copy Of My Rule\""* ]]; then
    echo "Could not delete policy \"Copy Of My Rule\""
    exit 1
fi

OUT=`$SCRIPTDIR/../examples/list_policies.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT = *"\"name\": \"Copy Of My Rule\""* ]]; then
    echo "After deleting policy Copy Of My Rule, policy was still present?"
    exit 1
fi

# Make a copy again, but this time delete by id
NEW_POLICY=`echo $MY_POLICY | sed -e "s/My Rule/Another Copy Of My Rule/g" | sed -e 's/"id": [0-9]*,//' | sed -e 's/"version": [0-9]*/"version": null/'`
OUT=`echo $NEW_POLICY | $SCRIPTDIR/../examples/add_policy.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"name\": \"Another Copy Of My Rule\""* ]]; then
    echo "Could not create new policy"
    exit 1
fi

ID=`echo $OUT | grep -E -o '"id": [^,]+,' | awk '{print $2}' | awk -F, '{print $1}'`

OUT=`$SCRIPTDIR/../examples/delete_policy.py --id $ID $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT != *"\"name\": \"Another Copy Of My Rule\""* ]]; then
    echo "Could not delete policy \"Copy Of My Rule\""
    exit 1
fi

OUT=`$SCRIPTDIR/../examples/list_policies.py $PYTHON_SDC_TEST_API_TOKEN`
if [[ $OUT = *"\"name\": \"Another Copy Of My Rule\""* ]]; then
    echo "After deleting policy Another Copy Of My Rule, policy was still present?"
    exit 1
fi

# Start an agent using this account's api key and trigger some events
docker run -d -it --rm --name sysdig-agent --privileged --net host --pid host -e COLLECTOR=collector-staging.sysdigcloud.com -e ACCESS_KEY=$PYTHON_SDC_TEST_ACCESS_KEY -v /var/run/docker.sock:/host/var/run/docker.sock  -v /dev:/host/dev -v /proc:/host/proc:ro -v /boot:/host/boot:ro -v /lib/modules:/host/lib/modules:ro -v /usr:/host/usr:ro -e ADDITIONAL_CONF="security: {enabled: true}\ncommandlines_capture: {enabled: true}\nmemdump: {enabled: true}" --shm-size=350m sysdig/agent

FOUND=0

for i in $(seq 10); do
    sleep 10
    touch /tmp/some-file.txt

    EVTS=`$SCRIPTDIR/../examples/get_secure_policy_events.py $PYTHON_SDC_TEST_API_TOKEN 60`

    if [[ "$EVTS" != "" ]]; then
       FOUND=1
       break;
    fi
done
docker logs sysdig-agent
docker stop sysdig-agent

if [[ $FOUND == 0 ]]; then
   echo "Did not find any policy events after 10 attempts..."
   exit 1
fi
