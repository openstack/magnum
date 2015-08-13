=========================================
Building and updating Fedora Atomic image
=========================================

For Magnum development, we use a Fedora Atomic image prebuilt with a certain
version of Docker, Kubernetes, etcd and Flannel.  This document details
instructions for building the image update it to incorporate your own changes.

The basic steps are:

1. Choose the packages and build a package repo.
2. Run a Docker container with Fedora 21 and build the rpm-ostree repo.
3. Create the new glance image from this Docker container.
4. Alternatively, update an existing container from this rpm-ostree repo.

This document was tested with Fedora 21.  This should also work for
Fedora 22 or other version with minor adjustment, and the document will be
updated when they are tested.

Create the package repo
=======================

Find the package version that you want from::

    https://kojipkgs.fedoraproject.org/packages/<packagename>

This URL does not contain a package name, so you will provide the package name
in the URL. For our case, we will use the three packages named 'kubernetes',
'etcd', and 'flannel'.

For example::

    https://kojipkgs.fedoraproject.org/packages/kubernetes/0.20.0/0.3.git835eded.fc23/src/kubernetes-0.20.0-0.3.git835eded.fc23.src.rpm
    https://kojipkgs.fedoraproject.org/packages/etcd/2.0.13/2.fc23/src/etcd-2.0.13-2.fc23.src.rpm
    https://kojipkgs.fedoraproject.org/packages/flannel/0.5.0/1.fc23/src/flannel-0.5.0-1.fc23.src.rpm


Next we build a package repo for these particular packages.  We use an
automated package builder from::

    https://copr.fedoraproject.org/coprs

If you don't have an account, you can create one on::

    http://fedoraproject.org

Once you log into Fedora copr via https://copr.fedoraproject.org, follow these
steps:

- Click on "Add a new project" and fill in the necessary information.
- Check the box for fedora-21-x86_64.
- In the box "Initial packages to build", refer the kojipkgs site mentioned
  above.  Cut and paste the links for the desired src.rpm package.
- Click build.

The build may take some time depending on how busy the system is.

When the build completes successfully, go to the Overview tab and look under
the column for "Yum repo". Find the link for a repo file to point to your
newly built package in copr. Save the text from this link to use later.

Build and host rpm-ostree repo
==============================

You will need a server with Docker installed.
Download this build configuration::

    git clone https://github.com/jasonbrooks/byo-atomic.git

Make sure httpd is not running on your server since we need to map port 80
to apache that will run in the Docker instance.  If port 80 is already in use,
we will get an error when starting the Docker instance indicating that the
address is already in use.

Verify that port tcp/80 is vacant by running this command::

    sudo netstat -antp | grep 80

The output should show no process on port 80.  For example, if apache is
using port 80, you would see something like::

    tcp6   0    0 :::80     :::*      LISTEN  26981/apache2

In the Dockerfile, we download the fedora 21 image and set up the environment.
If you are running on Ubuntu, the Dockerfile does need a minor workaround for
the httpd logs directory. Edit the Dockerfile and in the line with mkdir,
insert a command for "mkdir /etc/httpd/logs" as follows::

    mkdir /etc/httpd/logs && mkdir -p /srv/rpm-ostree/repo && cd /srv/rpm-ostree/ && ostree --repo=repo init --mode=archive-z2

Build a Docker container image to be used for hosting the rpm-ostree repo::

    sudo docker build --rm -t $USER/atomicrepo byo-atomic/.

where $USER is the user logged in.

When the build completes, you can see the image by running::

    sudo docker images

Start a container using the new Docker image. This will start apache in the
new container with tcp/80 mapped to the host::

    sudo docker run --privileged -d -p 80:80 --name atomicrepo $USER/atomicrepo

Then log into this Docker container::

    sudo docker exec -it atomicrepo bash

Once inside the Docker container, run the commands::

    cd fedora-atomic
    git checkout f21
    nscd

Edit the file fedora-atomic-docker-host.json to add the repo pointing to the
copr package repo.  Update the line "repos" as follows::

    "repos": ["fedora-21" , "my-copr-repo"],

You can rename "my-copr-repo" as needed, but make sure to use the same name
in the two steps following.  From the link on the copr site above, save the
content for the repo pointer in a file named "my-copr-repo.repo" in the same
directory, then make the following changes in the file.

Rename the first line as::

    [my-copr-repo]

And modify this flag::

    gpgcheck=0

Then build the rpm-ostree::

    rpm-ostree compose tree --repo=/srv/rpm-ostree/repo fedora-atomic-docker-host.json

When this is completed, Apache should be running on the Docker container and
serving the content of the new rpm-ostree repo.  From outside the container,
the repo can be accessed as::

    http://<ip>/repo

Create the new image
====================

From within the Docker container where the rpm-ostree repo has been built,
install additional tools::

    yum install -y rpm-ostree-toolbox nss-altfiles yum-plugin-protectbase

Create a new glance image::

    export LIBGUESTFS_BACKEND=direct
    rpm-ostree-toolbox create-vm-disk /srv/rpm-ostree/repo fedora-atomic-host fedora-atomic/f21/x86_64/docker-host my-new-f21-atomic.qcow2

The new image my-new-f21-atomic.qcow2 is in the current directory.

Update an existing Fedora Atomic server
=======================================

You may update an existing Fedora Atomic server to derive a new one.
If you have a nova instance created from an existing Fedora Atomic glance
image, you may update it from the rpm-ostree repo above. On this server,
edit this file as root::

    sudo vi /etc/ostree/remotes.d/fedora-atomic.conf

Add the content (substitute the <ip> for your Docker instance)::

    [remote "fedora-atomic-host"]
    url=http://<ip>/repo
    branches=fedora-atomic/21/x86_64/docker-host;
    gpg-verify=false

Run the command::

    sudo rpm-ostree upgrade

When the upgrade is completed, reboot to switch to the new version::

    sudo systemctl reboot

Once you have the modified server, you may snapshot it to create a new glance
image from it, and use that new glance image for subsequent new Magnum bays.
Note however that because of the way Atomic manages backup, this approach will
bloat the image size.
