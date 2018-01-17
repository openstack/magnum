FROM registry.fedoraproject.org/fedora:rawhide

# Fill out the labels
LABEL name="heat-container-agent" \
      maintainer="Spyros Trigazis <strigazi@gmail.com>" \
      license="UNKNOWN" \
      summary="Heat Container Agent system image" \
      version="1.0" \
      help="No help" \
      architecture="x86_64" \
      atomic.type="system" \
      distribution-scope="public"

RUN dnf -y --setopt=tsflags=nodocs install \
    findutils os-collect-config os-apply-config \
    os-refresh-config dib-utils python-pip python-docker-py \
    python-yaml python-zaqarclient python2-oslo-log \
    python-psutil && dnf clean all

# pip installing dpath as python-dpath is an older version of dpath
# install docker-compose
RUN pip install --no-cache dpath docker-compose

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

COPY launch /usr/bin/start-heat-container-agent

# Execution
CMD ["/usr/bin/start-heat-container-agent"]
