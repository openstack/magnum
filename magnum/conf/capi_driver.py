# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

capi_driver_group = cfg.OptGroup(
    name="capi_driver", title="Cluster API Driver configuration"
)

capi_driver_opts = [
    cfg.StrOpt(
        "kubeconfig_file",
        default="",
        help=(
            "Path to a kubeconfig file for a management cluster,"
            "for use in the Cluster API driver. "
            "Defaults to the environment variable KUBECONFIG, "
            "or if not defined ~/.kube/config "
            "Note we only use the default context within the "
            "kubeconfig file."
        ),
    ),
    cfg.StrOpt(
        "magnum_namespace_suffix",
        default="magnum",
        help=(
            "Resources for each openstack cluster are created in a "
            "separate namespace within the CAPI Management cluster "
            "specified by the configuration: capi_driver.kubeconfig_file "
            "You should modify this suffix when two magnum deployments "
            "want to share a single CAPI management cluster."
        ),
    ),
    # TODO(johngarbutt): move this helm chart into magnum ownerhship
    cfg.StrOpt(
        "helm_chart_repo",
        default="https://stackhpc.github.io/capi-helm-charts",
        help=(
            "Reference to the helm chart repository for "
            "the cluster API driver."
        ),
    ),
    cfg.StrOpt(
        "helm_chart_name",
        default="openstack-cluster",
        help=(
            "Name of the helm chart to use from the repo specified "
            "by the config: capi_driver.helm_chart_repo"
        ),
    ),
    cfg.StrOpt(
        "helm_chart_version",
        default="0.1.1-dev.0.main.221",
        help=(
            "Version of the helm chart specified "
            "by the config: capi_driver.helm_chart_repo "
            "and capi_driver.helm_chart_name"
        ),
    ),
]


def register_opts(conf):
    conf.register_group(capi_driver_group)
    conf.register_opts(capi_driver_opts, group=capi_driver_group)


def list_opts():
    return {capi_driver_group: capi_driver_opts}
