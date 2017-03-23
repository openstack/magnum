FROM ubuntu:trusty

RUN \
  apt-get -yqq update && \
  apt-get -yqq install git qemu-utils python-dev python-pip python-yaml python-six uuid-runtime curl sudo kpartx parted wget && \
  pip install diskimage-builder && \
  mkdir /output

WORKDIR /build

ENV PATH="dib-utils/bin:$PATH" ELEMENTS_PATH="$(python -c 'import os, diskimage_builder, pkg_resources;print(os.path.abspath(pkg_resources.resource_filename(diskimage_builder.__name__, "elements")))'):tripleo-image-elements/elements:heat-templates/hot/software-config/elements:magnum/magnum/drivers/mesos_ubuntu_v1/image" DIB_RELEASE=trusty

RUN git clone https://git.openstack.org/openstack/magnum
RUN git clone https://git.openstack.org/openstack/dib-utils.git
RUN git clone https://git.openstack.org/openstack/tripleo-image-elements.git
RUN git clone https://git.openstack.org/openstack/heat-templates.git

CMD disk-image-create ubuntu vm docker mesos os-collect-config os-refresh-config os-apply-config heat-config heat-config-script -o /output/ubuntu-mesos.qcow2
