Build openSUSE Leap 42.1 image for OpenStack Magnum
===================================================

This instruction describes how to build manually openSUSE Leap 42.1 image
for OpenStack Magnum with Kubernetes packages.

Link to the image:
 http://download.opensuse.org/repositories/Cloud:/Images:/Leap_42.1/images/openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s.x86_64.qcow2

## Requirements

Please install openSUSE (https://www.opensuse.org/) on physical or virtual machine.

## Install packages

Install `kiwi` package on openSUSE node, where do you want to build your image

`zypper install kiwi`

Create destination directory, where image will be build

`mkdir /tmp/openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s`

## Build image

Run in current directory with `openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s` kiwi template

`kiwi --verbose 3 --logfile terminal --build . --destdir /tmp/openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s`

## Get image

After `kiwi` will finish, image can be found in `/tmp/openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s`
directory with name `openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s.x86_64-1.1.1.qcow2`.

Full path

`/tmp/openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s/openSUSE-Leap-42.1-JeOS-for-OpenStack-Magnum-K8s.x86_64-1.1.1.qcow2`

Have fun !!!
