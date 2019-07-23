ARG KUBE_VERSION=v1.13.0

FROM fedora:rawhide
ARG KUBE_VERSION
ARG ADD_KUBE_ALLOW_PRIV=false
RUN curl -o /root/kubectl -O https://storage.googleapis.com/kubernetes-release/release/${KUBE_VERSION}/bin/linux/amd64/kubectl

FROM gcr.io/google-containers/kube-apiserver-amd64:${KUBE_VERSION}

ENV container=docker

ENV NAME=kubernetes-apiserver VERSION=0.1 RELEASE=8 ARCH=x86_64
LABEL bzcomponent="$NAME" \
        name="$FGC/$NAME" \
        version="$VERSION" \
        release="$RELEASE.$DISTTAG" \
        architecture="$ARCH" \
        atomic.type='system' \
        maintainer="Jason Brooks <jbrooks@redhat.com>"

COPY launch.sh /usr/bin/kube-apiserver-docker.sh

COPY service.template config.json.template /exports/

# copy kubectl into the host, another way to do this would be:
#
#     echo "runc exec -- kube-apiserver /usr/bin/kubectl \$@"  \
#     > /exports/hostfs/usr/local/bin/kubectl && chmod +x \
#     /exports/hostfs/usr/local/bin/kubectl
#
# however, this would require hard-coding the container name

COPY apiserver config /etc/kubernetes/
RUN [ "$ADD_KUBE_ALLOW_PRIV" = "true" ] && echo "KUBE_ALLOW_PRIV=\"--allow-privileged=false\"" >> /etc/kubernetes/config || true
RUN mkdir -p /exports/hostfs/usr/local/bin/
COPY --from=0 /root/kubectl /exports/hostfs/usr/local/bin/
RUN chmod +x /exports/hostfs/usr/local/bin/kubectl && \
    mkdir -p /exports/hostfs/etc/kubernetes && \
    cp /etc/kubernetes/config /exports/hostfs/etc/kubernetes/ && \
    cp /etc/kubernetes/apiserver /exports/hostfs/etc/kubernetes/

ENTRYPOINT ["/usr/bin/kube-apiserver-docker.sh"]
