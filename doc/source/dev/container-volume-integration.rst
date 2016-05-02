===============================================
Using Container Volume Integration Feature
===============================================

For Magnum user, we use Container Volume Integration in Kubernetes, Swarm
and Mesos. This document details instructions how to use the container volume
integration in Kubernetes, Swarm and Mesos.

Using container volume integration in Kubernetes
------------------------------------------------

**NOTE:**  The Container Volume Model of Kubernetes needs the kubernetes
version >= 1.1.1 and docker version >= 1.8.3

1. Store the Fedora Atomic micro-OS in glance

   The steps for updating Fedora Atomic images are a bit detailed.Fortunately
   one of the core developers has made Atomic images available at
   https://fedorapeople.org/groups/magnum::

    cd ~
    wget https://fedorapeople.org/groups/magnum/fedora-23-atomic-7.qcow2
    glance image-create --name fedora-23-atomic-7 \
                        --visibility public \
                        --disk-format qcow2 \
                        --os-distro fedora-atomic \
                        --container-format bare < fedora-23-atomic-7.qcow2

2. Edit the file::

    sudo vi /opt/stack/magnum/magnum/templates/kubernetes/kubecluster.yaml

   The default value of the kube_version entries needs to change 'v1.0.6' to
   'v1.1.8', then restart magnum-conduct service.(Magnum team will make the
   step automation as soon as possible.)

3. Create the baymodel.

   The new attribute volume-driver for a baymodel specifies the volume backend
   driver to use when deploying a bay. The volume-driver value needs to be
   specified as 'cinder' for kubernetes::

    magnum baymodel-create --name k8sbaymodel \
                           --image-id fedora-23-atomic-7 \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --flavor-id m1.small \
                           --docker-volume-size 5 \
                           --network-driver flannel \
                           --coe kubernetes \
                           --volume-driver cinder

4. Create the bay::

    magnum bay-create --name k8sbay --baymodel k8sbaymodel --node-count 1

To enable the container volume integration in kubernetes, log into each minion
node of your bay and perform the following step 5, step 6, step 7 and step 8:

5. Configure kubelet::

    sudo vi /etc/kubernetes/kubelet

   Comment out the line::

    #KUBELET_ARGS=--config=/etc/kubernetes/manifests --cadvisor-port=4194

   Uncomment the line::

    #KUBELET_ARGS="--config=/etc/kubernetes/manifests --cadvisor-port=4194 --cloud-provider=openstack --cloud-config=/etc/kubernetes/kube_openstack_config"

**NOTE:** This is a temporary workaround, and Magnum team is working
on a long term solution to automate this step.

6. Enter OpenStack user credential::

    sudo vi /etc/kubernetes/kube_openstack_config

  The username, tenant-name and region entries have been filled in with the
  Keystone values of the user who created the bay.  Enter the password
  of this user on the entry for password::

    password=ChangeMe

7. Restart Kubernetes services::

    sudo systemctl restart kubelet

8. Run the docker container::

    sudo docker run -v /usr/local/bin:/target jpetazzo/nsenter

Kubernetes container volume integration has configured by the above steps,
And you can use the kubernetes container volume now. The following steps is
an example for container volume integration with kubernetes bay.

1. Create the cinder volume::

    cinder create --display-name=test-repo 1

    ID=$(cinder create --display-name=test-repo 1 | awk -F'|' '$2~/^[[:space:]]*id/ {print $3}')

   The command will generate the volume with a ID. The volume ID will be specified in
   Step 2.

2. Create a container in this bay.

The following example illustrates how to mount an cinder volume for a pod.

Create a file (e.g nginx-cinder.yaml) describing a pod::

    cat > nginx-cinder.yaml << END
    apiVersion: v1
    kind: Pod
    metadata:
      name: aws-web
    spec:
      containers:
        - name: web
          image: nginx
          ports:
            - name: web
              containerPort: 80
              hostPort: 8081
              protocol: TCP
          volumeMounts:
            - name: html-volume
              mountPath: "/usr/share/nginx/html"
      volumes:
        - name: html-volume
          cinder:
            # Enter the volume ID below
            volumeID: $ID
            fsType: ext4
    END

**NOTE:** The cinder volume ID needs to be configured into the yaml file
so that an existing Cinder volume can be mounted in a pod by specifying
the volume ID in the pod manifest as follows::

    volumes:
    - name: html-volume
      cinder:
        volumeID: $ID
        fsType: ext4

3. Create a pod with container. Please refer to the quickstart guide on how to
   connect to Kubernetes running on the launched bay.::

    kubectl create -f ./nginx-cinder.yaml

You can log in the container to check if existing the mountPath, and check
if your cinder volume status is 'in-use' by running the command 'cinder list'.

Using container volume integration in Swarm
-------------------------------------------
*To be filled in*

Using container volume integration in Mesos
-------------------------------------------

1. Create the baymodel.

   One of the new attributes volume-driver for a baymodel specifies the volume
   backend driver to use when deploying a bay. The volume-driver value needs to
   be specified as rexray for Mesos.
   The other new attributes rexray_preempt for a baymodel is an optional
   parameter here which enables any host to take control of a volume
   irrespective of whether other hosts are using the volume. If this is set to
   false then mostly plugins ensure safety first for locking the volume::

    magnum baymodel-create --name mesosbaymodel \
                           --image-id ubuntu-mesos \
                           --keypair-id testkey \
                           --external-network-id public \
                           --dns-nameserver 8.8.8.8 \
                           --master-flavor-id m1.magnum \
                           --docker-volume-size 4 \
                           --tls-disabled \
                           --flavor-id m1.magnum \
                           --coe mesos \
                           --volume-driver rexray \
                           --labels rexray-preempt=true

2. Create the mesos bay::

    magnum bay-create --name mesosbay --baymodel mesosbaymodel --node-count 1

3. Create the cinder volume and a container in this bay::

    cinder create --display-name=redisdata 1

   Create the following mesos.json file::

    cat > mesos.json << END
    {
      "id": "redis",
      "container": {
        "docker": {
        "image": "redis",
        "network": "BRIDGE",
        "portMappings": [
          { "containerPort": 80, "hostPort": 0, "protocol": "tcp"}
        ],
        "parameters": [
           { "key": "volume-driver", "value": "rexray" },
           { "key": "volume", "value": "redisdata:/data" }
        ]
        }
     },
     "cpus": 0.2,
     "mem": 32.0,
     "instances": 1
    }
    END

**NOTE:** When the mesos bay is created using this baymodel, the mesos bay
will be configured so that an existing cinder volume can be mounted in a
container by configuring the parameters to mount the cinder volume in the
json file::

    "parameters": [
       { "key": "volume-driver", "value": "rexray" },
       { "key": "volume", "value": "redisdata:/data" }
    ]

4. Using the REST API of Marathon::

    MASTER_IP=$(magnum bay-show mesosbay | awk '/ api_address /{print $4}')
    curl -X POST -H "Content-Type: application/json" \
    http://${MASTER_IP}:8080/v2/apps -d@mesos.json

You can log in the container to check if existing the mountPath, and check
if your cinder volume status is 'in-use' by running the command 'cinder list'.
