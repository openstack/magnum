ARG KUBE_VERSION=v1.13.0
FROM gcr.io/google-containers/kube-proxy-amd64:${KUBE_VERSION}
ARG ADD_KUBE_ALLOW_PRIV=false
ENV container=docker

ENV NAME=kubernetes-proxy VERSION=0 RELEASE=8 ARCH=x86_64
LABEL bzcomponent="$NAME" \
        name="$FGC/$NAME" \
        version="$VERSION" \
        release="$RELEASE.$DISTTAG" \
        architecture="$ARCH" \
        atomic.type='system' \
        maintainer="Jason Brooks <jbrooks@redhat.com>"

COPY launch.sh /usr/bin/kube-proxy-docker.sh

COPY service.template config.json.template /exports/

COPY proxy config /etc/kubernetes/
RUN [ "$ADD_KUBE_ALLOW_PRIV" = "true" ] && echo "KUBE_ALLOW_PRIV=\"--allow-privileged=false\"" >> /etc/kubernetes/config || true

RUN mkdir -p /exports/hostfs/etc/kubernetes && \
    cp /etc/kubernetes/config /exports/hostfs/etc/kubernetes/ && \
    cp /etc/kubernetes/proxy /exports/hostfs/etc/kubernetes/

ENTRYPOINT ["/usr/bin/kube-proxy-docker.sh"]

