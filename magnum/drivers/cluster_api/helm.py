# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import functools
import json
import pathlib
import typing as t

from oslo_concurrency import processutils
from oslo_log import log as logging

from magnum.common import utils
from magnum import conf

LOG = logging.getLogger(__name__)
CONF = conf.CONF


def mergeconcat(defaults, *overrides):
    """Deep-merge two or more dictionaries together.

    Lists are concatenated.
    """

    def mergeconcat2(defaults, overrides):
        if isinstance(defaults, dict) and isinstance(overrides, dict):
            merged = dict(defaults)
            for key, value in overrides.items():
                if key in defaults:
                    merged[key] = mergeconcat2(defaults[key], value)
                else:
                    merged[key] = value
            return merged
        elif isinstance(defaults, (list, tuple)) and isinstance(
            overrides, (list, tuple)
        ):
            merged = list(defaults)
            merged.extend(overrides)
            return merged
        else:
            return overrides if overrides is not None else defaults

    return functools.reduce(mergeconcat2, overrides, defaults)


class Client:
    """Client for interacting with Helm CLI."""

    def __init__(self):
        self._default_timeout = "5m"
        self._executable = "helm"
        self._history_max_revisions = 10
        self._kubeconfig = CONF.capi_driver.kubeconfig_file

    def _run(self, command, **kwargs) -> bytes:
        command = [self._executable] + command
        if self._kubeconfig:
            command.extend(["--kubeconfig", self._kubeconfig])
        stdout, stderr = utils.execute(*command, **kwargs)
        LOG.debug(f"Ran helm {command} got out:{stdout} err:{stderr}")
        return stdout

    def install_or_upgrade(
        self,
        release_name: str,
        chart_ref: t.Union[pathlib.Path, str],
        *values: t.Dict[str, t.Any],
        namespace: str,
        repo: t.Optional[str],
        version: t.Optional[str],
    ) -> t.Iterable[t.Dict[str, t.Any]]:
        """Install or upgrade specified release using chart and values."""
        command = [
            "upgrade",
            release_name,
            chart_ref,
            "--history-max",
            self._history_max_revisions,
            "--install",
            "--output",
            "json",
            "--timeout",
            self._default_timeout,
            # We send the values in on stdin
            "--values",
            "-",
            "--namespace",
            namespace,
            "--repo",
            repo,
            "--version",
            version,
        ]
        process_input = json.dumps(mergeconcat({}, *values))
        return json.loads(self._run(command, process_input=process_input))

    def uninstall_release(
        self,
        release_name: str,
        namespace: str,
    ):
        """Uninstall the named release."""
        command = [
            "uninstall",
            release_name,
            "--timeout",
            self._default_timeout,
            "--namespace",
            namespace,
        ]
        try:
            self._run(command)
        except processutils.ProcessExecutionError as exc:
            # Swallow release not found errors, as that is our desired state
            if not exc.stderr or "release: not found" not in exc.stderr:
                raise
