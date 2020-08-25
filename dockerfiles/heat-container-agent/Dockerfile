FROM fedora:rawhide

ARG ARCH=x86_64

# Fill out the labels
LABEL name="heat-container-agent" \
      maintainer="Spyros Trigazis <strigazi@gmail.com>" \
      license="UNKNOWN" \
      summary="Heat Container Agent system image" \
      version="1.0" \
      help="No help" \
      architecture=$ARCH \
      atomic.type="system" \
      distribution-scope="public"

RUN dnf -y --setopt=tsflags=nodocs --nogpgcheck install \
        bash \
        findutils \
        gcc \
        kubernetes-client \
        libffi-devel \
        openssh-clients \
        openssl \
        openssl-devel \
        python-devel \
        python-lxml \
        python-pip \
        python-psutil \
        hostname \
        redhat-rpm-config && \
    pip install --no-cache --no-cache-dir \
        dib-utils \
        dpath \
        os-apply-config \
        os-collect-config \
        os-refresh-config \
        python-heatclient \
        python-keystoneclient && \
    dnf remove -y gcc redhat-rpm-config -y && \
    dnf clean all

ADD ./scripts/55-heat-config \
  /opt/heat-container-agent/scripts/

ADD ./scripts/50-heat-config-docker-compose \
  /opt/heat-container-agent/scripts/

ADD ./scripts/hooks/* \
  /opt/heat-container-agent/hooks/

ADD ./scripts/heat-config-notify \
  /usr/bin/heat-config-notify
RUN chmod 755 /usr/bin/heat-config-notify

ADD ./scripts/configure_container_agent.sh /opt/heat-container-agent/
RUN chmod 700 /opt/heat-container-agent/configure_container_agent.sh

ADD ./scripts/write-os-apply-config-templates.sh /tmp
RUN chmod 700 /tmp/write-os-apply-config-templates.sh
RUN /tmp/write-os-apply-config-templates.sh

COPY manifest.json service.template config.json.template tmpfiles.template /exports/

RUN if [ ! -f /usr/bin/python ]; then ln -s /usr/bin/python3 /usr/bin/python; fi

COPY launch /usr/bin/start-heat-container-agent

# Execution
CMD ["/usr/bin/start-heat-container-agent"]
