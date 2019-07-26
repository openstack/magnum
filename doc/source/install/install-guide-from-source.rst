.. _install-guide-from-source:

Install from source code and configure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Container
Infrastructure Management service for from source code.

.. include:: common/prerequisites.rst

Install and configure components
--------------------------------

1. Install Magnum from source:

   a. Install OS-specific prerequisites:

      * Ubuntu 16.04 (xenial) or higher:

        .. code-block:: console

           # apt update
           # apt install python-dev libssl-dev libxml2-dev \
                         libmysqlclient-dev libxslt-dev libpq-dev git \
                         libffi-dev gettext build-essential
      * CentOS 7:

        .. code-block:: console

           # yum install python-devel openssl-devel mariadb-devel \
                         libxml2-devel libxslt-devel postgresql-devel git \
                         libffi-devel gettext gcc

      * Fedora 21 / RHEL 7

        .. code-block:: console

           # yum install python-devel openssl-devel mysql-devel \
                         libxml2-devel libxslt-devel postgresql-devel git \
                         libffi-devel gettext gcc

      * Fedora 22 or higher

        .. code-block:: console

           # dnf install python-devel openssl-devel mysql-devel \
                         libxml2-devel libxslt-devel postgresql-devel git \
                         libffi-devel gettext gcc

      * openSUSE Leap 42.1

        .. code-block:: console

           # zypper install git libffi-devel libmysqlclient-devel \
                            libopenssl-devel libxml2-devel libxslt-devel \
                            postgresql-devel python-devel gettext-runtime gcc

   b. Create magnum user and necessary directories:

      * Create user:

        .. code-block:: console

           # groupadd --system magnum
           # useradd --home-dir "/var/lib/magnum" \
                 --create-home \
                 --system \
                 --shell /bin/false \
                 -g magnum \
                 magnum

      * Create directories:

        .. code-block:: console

           # mkdir -p /var/log/magnum
           # mkdir -p /etc/magnum

      * Set ownership to directories:

        .. code-block:: console

           # chown magnum:magnum /var/log/magnum
           # chown magnum:magnum /var/lib/magnum
           # chown magnum:magnum /etc/magnum

   c. Install virtualenv and python prerequisites:

      * Install virtualenv and create one for magnum's installation:

        .. code-block:: console

           # easy_install -U virtualenv
           # su -s /bin/sh -c "virtualenv /var/lib/magnum/env" magnum

      * Install python prerequisites:

        .. code-block:: console

           # su -s /bin/sh -c "/var/lib/magnum/env/bin/pip install tox pymysql \
             python-memcached" magnum

   d. Clone and install magnum:

      .. code-block:: console

         # cd /var/lib/magnum
         # git clone https://opendev.org/openstack/magnum
         # chown -R magnum:magnum magnum
         # cd magnum
         # su -s /bin/sh -c "/var/lib/magnum/env/bin/pip install -r requirements.txt" magnum
         # su -s /bin/sh -c "/var/lib/magnum/env/bin/python setup.py install" magnum

   e. Copy api-paste.ini:

      .. code-block:: console

         # su -s /bin/sh -c "cp etc/magnum/api-paste.ini /etc/magnum" magnum

   f. Generate a sample configuration file:

      .. code-block:: console

         # su -s /bin/sh -c "/var/lib/magnum/env/bin/tox -e genconfig" magnum
         # su -s /bin/sh -c "cp etc/magnum/magnum.conf.sample /etc/magnum/magnum.conf" magnum

   e. Optionally, if you want to customize the policies for Magnum API accesses,
      you can generate a sample policy file, put it into ``/etc/magnum`` folder
      for further modifications:

      .. code-block:: console

         # su -s /bin/sh -c "/var/lib/magnum/env/bin/tox -e genpolicy" magnum
         # su -s /bin/sh -c "cp etc/magnum/policy.yaml.sample /etc/magnum/policy.yaml" magnum

.. include:: common/configure_2_edit_magnum_conf.rst

* Additionally, edit the ``/etc/magnum/magnum.conf`` file:

  * In the ``[oslo_concurrency]`` section, configure the ``lock_path``:

    .. code-block:: ini

       [oslo_concurrency]
       ...
       lock_path = /var/lib/magnum/tmp

   * If you decide to customize Magnum policies in ``1.e``, then in the
     ``[oslo_policy]`` section, configure the ``policy_file``:

     .. code-block:: ini

        [oslo_policy]
        ...
        policy_file = /etc/magnum/policy.yaml

   .. note::

      Make sure that ``/etc/magnum/magnum.conf`` still have the correct
      permissions. You can set the permissions again with:

      # chown magnum:magnum /etc/magnum/magnum.conf

3. Populate Magnum database:

   .. code-block:: console

      # su -s /bin/sh -c "/var/lib/magnum/env/bin/magnum-db-manage upgrade" magnum

4. Set magnum for log rotation:

   .. code-block:: console

      # cd /var/lib/magnum/magnum
      # cp doc/examples/etc/logrotate.d/magnum.logrotate /etc/logrotate.d/magnum

Finalize installation
---------------------

#. Create init scripts and services:

   * Ubuntu 16.04 or higher, Fedora 21 or higher/RHEL 7/CentOS 7 or openSUSE
     Leap 42.1:

     .. code-block:: console

        # cd /var/lib/magnum/magnum
        # cp doc/examples/etc/systemd/system/magnum-api.service \
          /etc/systemd/system/magnum-api.service
        # cp doc/examples/etc/systemd/system/magnum-conductor.service \
          /etc/systemd/system/magnum-conductor.service

#. Start magnum-api and magnum-conductor:

   * Ubuntu 16.04 or higher, Fedora 21 or higher/RHEL 7/CentOS 7 or openSUSE
     Leap 42.1:

     .. code-block:: console

        # systemctl enable magnum-api
        # systemctl enable magnum-conductor

     .. code-block:: console

        # systemctl start magnum-api
        # systemctl start magnum-conductor

#. Verify that magnum-api and magnum-conductor services are running:

   * Ubuntu 16.04 or higher, Fedora 21 or higher/RHEL 7/CentOS 7 or openSUSE
     Leap 42.1:

     .. code-block:: console

        # systemctl status magnum-api
        # systemctl status magnum-conductor

Install the command-line client
-------------------------------

#. Install OS-specific prerequisites:

   * Fedora 21/RHEL 7/CentOS 7

     .. code-block:: console

        # yum install python-devel openssl-devel python-virtualenv \
                      libffi-devel git gcc

   * Fedora 22 or higher

     .. code-block:: console

        # dnf install python-devel openssl-devel python-virtualenv \
                      libffi-devel git gcc

   * Ubuntu

     .. code-block:: console

        # apt update
        # apt install python-dev libssl-dev python-virtualenv \
                      libffi-dev git gcc

   * openSUSE Leap 42.1

     .. code-block:: console

        # zypper install python-devel libopenssl-devel python-virtualenv \
                         libffi-devel git gcc

#. Install the client in a virtual environment:

   .. code-block:: console

      $ cd ~
      $ git clone https://opendev.org/openstack/python-magnumclient
      $ cd python-magnumclient
      $ virtualenv .magnumclient-env
      $ .magnumclient-env/bin/pip install -r requirements.txt
      $ .magnumclient-env/bin/python setup.py install

#. Now, you can export the client in your PATH:

   .. code-block:: console

      $ export PATH=$PATH:${PWD}/.magnumclient-env/bin/magnum

   .. note::

      The command-line client can be installed on the controller node or
      on a different host than the service. It is good practice to install it
      as a non-root user.
