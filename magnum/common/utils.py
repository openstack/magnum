# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# Copyright (c) 2012 NTT DOCOMO, INC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utilities and helper functions."""

import contextlib
import os
import random
import re
import shutil
import tempfile

import netaddr
from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_utils import netutils

from magnum.common import exception
import magnum.conf

CONF = magnum.conf.CONF
LOG = logging.getLogger(__name__)

MEMORY_UNITS = {
    'Ki': 2 ** 10,
    'Mi': 2 ** 20,
    'Gi': 2 ** 30,
    'Ti': 2 ** 40,
    'Pi': 2 ** 50,
    'Ei': 2 ** 60,
    'm': 10 ** -3,
    'k': 10 ** 3,
    'M': 10 ** 6,
    'G': 10 ** 9,
    'T': 10 ** 12,
    'p': 10 ** 15,
    'E': 10 ** 18,
    '': 1
}

DOCKER_MEMORY_UNITS = {
    'b': 1,
    'k': 2 ** 10,
    'm': 2 ** 20,
    'g': 2 ** 30,
}


def _get_root_helper():
    return 'sudo magnum-rootwrap %s' % CONF.rootwrap_config


def execute(*cmd, **kwargs):
    """Convenience wrapper around oslo's execute() method.

    :param cmd: Passed to processutils.execute.
    :param use_standard_locale: True | False. Defaults to False. If set to
                                True, execute command with standard locale
                                added to environment variables.
    :returns: (stdout, stderr) from process execution
    :raises: UnknownArgumentError
    :raises: ProcessExecutionError
    """

    use_standard_locale = kwargs.pop('use_standard_locale', False)
    if use_standard_locale:
        env = kwargs.pop('env_variables', os.environ.copy())
        env['LC_ALL'] = 'C'
        kwargs['env_variables'] = env
    if kwargs.get('run_as_root') and 'root_helper' not in kwargs:
        kwargs['root_helper'] = _get_root_helper()
    result = processutils.execute(*cmd, **kwargs)
    LOG.debug('Execution completed, command line is "%s"',
              ' '.join(map(str, cmd)))
    LOG.debug('Command stdout is: "%s"', result[0])
    LOG.debug('Command stderr is: "%s"', result[1])
    return result


def trycmd(*args, **kwargs):
    """Convenience wrapper around oslo's trycmd() method."""
    if kwargs.get('run_as_root') and 'root_helper' not in kwargs:
        kwargs['root_helper'] = _get_root_helper()
    return processutils.trycmd(*args, **kwargs)


def validate_and_normalize_mac(address):
    """Validate a MAC address and return normalized form.

    Checks whether the supplied MAC address is formally correct and
    normalize it to all lower case.

    :param address: MAC address to be validated and normalized.
    :returns: Normalized and validated MAC address.
    :raises: InvalidMAC If the MAC address is not valid.

    """
    if not netutils.is_valid_mac(address):
        raise exception.InvalidMAC(mac=address)
    return address.lower()


def validate_dns(dns_list):
    """Validate a string is a single dns address or comma separated dns list

    :param dns_list: dns_list to be validated
    :returns: original dns_list.
    :raise: InvalidDNS if dns format is invalid

    """
    dns_nameservers = dns_list.split(',')
    try:
        for dns in dns_nameservers:
            netaddr.IPAddress(dns.strip(), version=4, flags=netaddr.INET_PTON)
    except netaddr.AddrFormatError:
        raise exception.InvalidDNS(dns=dns_list)
    else:
        return dns_list


@contextlib.contextmanager
def tempdir(**kwargs):
    tempfile.tempdir = CONF.tempdir
    tmpdir = tempfile.mkdtemp(**kwargs)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            LOG.error('Could not remove tmpdir: %s', e)


def rmtree_without_raise(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
    except OSError as e:
        LOG.warning("Failed to remove dir %(path)s, error: %(e)s",
                    {'path': path, 'e': e})


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, str):
        LOG.warning("Failed to remove trailing character. "
                    "Returning original object. "
                    "Supplied object is not a string: %s,", value)
        return value

    return value.rstrip(chars) or value


def is_name_safe(name):
    """Checks whether the name is valid or not.

    :param name: name of the resource.
    :returns: True, when name is valid
              False, otherwise.
    """
    # TODO(madhuri): There should be some validation of name.
    # Leaving it now as there is no validation
    # while resource creation.
    # https://bugs.launchpad.net/magnum/+bug/1430617
    if not name:
        return False
    return True


def get_k8s_quantity(quantity):
    """This function is used to get k8s quantity.

    It supports to get CPU and Memory quantity:

    Kubernetes cpu format must be in the format of:

        <signedNumber>'m'
        for example:
        500m = 0.5 core of cpu

    Kubernetes memory format must be in the format of:

        <signedNumber><suffix>
        signedNumber = digits|digits.digits|digits.|.digits
        suffix = Ki|Mi|Gi|Ti|Pi|Ei|m|k|M|G|T|P|E|''
        or suffix = E|e<signedNumber>
        digits = digit | digit<digits>
        digit = 0|1|2|3|4|5|6|7|8|9

    :param name: String value of a quantity such as '500m', '1G'
    :returns: Quantity number
    :raises: exception.UnsupportedK8sQuantityFormat if the quantity string
             is a unsupported value
    """

    signed_num_regex = r"(^\d+\.\d+)|(^\d+\.)|(\.\d+)|(^\d+)"
    matched_signed_number = re.search(signed_num_regex, quantity)
    if matched_signed_number is None:
        raise exception.UnsupportedK8sQuantityFormat()
    else:
        signed_number = matched_signed_number.group(0)
    suffix = quantity.replace(signed_number, '', 1)
    if suffix == '':
        return float(quantity)
    if re.search(r"^(Ki|Mi|Gi|Ti|Pi|Ei|m|k|M|G|T|P|E|'')$", suffix):
        return float(signed_number) * MEMORY_UNITS[suffix]
    elif re.search(r"^[E|e][+|-]?(\d+\.\d+$)|(\d+\.$)|(\.\d+$)|(\d+$)",
                   suffix):
        return float(signed_number) * (10 ** float(suffix[1:]))
    else:
        raise exception.UnsupportedK8sQuantityFormat()


def generate_password(length, symbolgroups=None):
    """Generate a random password from the supplied symbol groups.

    At least one symbol from each group will be included. Unpredictable
    results if length is less than the number of symbol groups.

    Believed to be reasonably secure (with a reasonable password length!)

    """

    if symbolgroups is None:
        symbolgroups = CONF.password_symbols

    r = random.SystemRandom()

    # NOTE(jerdfelt): Some password policies require at least one character
    # from each group of symbols, so start off with one random character
    # from each symbol group
    password = [r.choice(s) for s in symbolgroups]
    # If length < len(symbolgroups), the leading characters will only
    # be from the first length groups. Try our best to not be predictable
    # by shuffling and then truncating.
    r.shuffle(password)
    password = password[:length]
    length -= len(password)

    # then fill with random characters from all symbol groups
    symbols = ''.join(symbolgroups)
    password.extend([r.choice(symbols) for _i in range(length)])

    # finally shuffle to ensure first x characters aren't from a
    # predictable group
    r.shuffle(password)

    return ''.join(password)


def get_openstack_ca():
    openstack_ca_file = CONF.drivers.openstack_ca_file

    if openstack_ca_file:
        with open(openstack_ca_file) as fd:
            return fd.read()
    else:
        return ''
