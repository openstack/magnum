Rolling upgrade is one of most important features user want to see for a
managed Kubernetes service. And in Magnum, we're thinking more deeper to
provide better user experience.


.. code-block:: bash

    #!/bin/bash -x

    IP="192.168.122.1"
    CLUSTER="797b39e1-fac2-48d3-8377-d6e6cc443d39"
    CT="e32c8cf7-394b-45e6-a17e-4fe6a30ad64b"

    # Upgrade curl
    req_body=$(cat << EOF
    {
        "max_batch_size": 1,
        "nodegroup": "master",
        "cluster_template": "${CT}"
    }
    EOF
    )
    USER_TOKEN=$(openstack token issue -c id -f value)
    curl -g -i -X PATCH https://${IP}:9511/v1/clusters/${CLUSTER}/actions/upgrade \
    -H "OpenStack-API-Version: container-infra latest" \
    -H "X-Auth-Token: $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -H "User-Agent: None" \
    -d "$req_body"
