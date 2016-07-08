FROM ubuntu:trusty

RUN \
  apt-get -yqq update && \
  apt-get -yqq install git qemu-utils python-pip uuid-runtime curl sudo parted wget && \
  pip install pyyaml && \
  mkdir /output

WORKDIR /build

ENV PATH="/build/dib-utils/bin:$PATH" ELEMENTS_PATH="magnum/magnum/templates/mesos/elements" DIB_RELEASE=trusty

RUN git clone https://git.openstack.org/openstack/magnum
RUN git clone https://git.openstack.org/openstack/diskimage-builder.git
RUN git clone https://git.openstack.org/openstack/dib-utils.git

CMD diskimage-builder/bin/disk-image-create ubuntu vm docker mesos -o /output/ubuntu-mesos.qcow2
