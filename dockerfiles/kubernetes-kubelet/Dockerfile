ARG KUBE_VERSION=v1.13.0
FROM gcr.io/google-containers/hyperkube-amd64:${KUBE_VERSION}
ARG ADD_KUBE_ALLOW_PRIV=false

ENV container=docker

ENV NAME=kubernetes-kubelet VERSION=0 RELEASE=8 ARCH=x86_64
LABEL bzcomponent="$NAME" \
        name="$FGC/$NAME" \
        version="$VERSION" \
        release="$RELEASE.$DISTTAG" \
        architecture="$ARCH" \
        atomic.type='system' \
        maintainer="Jason Brooks <jbrooks@redhat.com>"

COPY launch.sh /usr/bin/kubelet-docker.sh
COPY kubelet config /etc/kubernetes/
RUN [ "$ADD_KUBE_ALLOW_PRIV" = "true" ] && echo "KUBE_ALLOW_PRIV=\"--allow-privileged=false\"" >> /etc/kubernetes/config || true

COPY manifest.json tmpfiles.template service.template config.json.template /exports/

RUN mkdir -p /exports/hostfs/etc/cni/net.d && \
    mkdir -p /exports/hostfs/etc/kubernetes && \
    cp /etc/kubernetes/{config,kubelet} /exports/hostfs/etc/kubernetes

ENTRYPOINT ["/usr/bin/kubelet-docker.sh"]
