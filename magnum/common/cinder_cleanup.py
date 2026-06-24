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

import time

import heatclient.exc as heat_exc
from cinderclient import exceptions as cinder_exc
from oslo_log import log as logging

from magnum.common import clients
from magnum.common import exception

LOG = logging.getLogger(__name__)

VOLUME_RESOURCE_TYPES = [
    "Magnum::Optional::Cinder::Volume",
    "Magnum::Optional::Etcd::Volume",
    "OS::Cinder::Volume",
]


def _wait_for_volumes_deleted(cinder_client, volume_ids, timeout=120,
                              max_error_retries=3):
    """Wait for volumes to be fully deleted.

    If a volume reverts to 'error' or 'error_deleting' after a delete
    attempt, reset its state and retry up to max_error_retries times
    before giving up on that volume.
    """
    start_time = time.time()
    remaining = set(volume_ids)
    error_counts = {}

    while remaining:
        if (time.time() - start_time) > timeout:
            LOG.warning("Timed out waiting for volumes %s to be deleted",
                        remaining)
            return

        still_pending = set()
        for vol_id in remaining:
            try:
                vol = cinder_client.volumes.get(vol_id)
            except cinder_exc.NotFound:
                # Gone — success
                continue

            if vol.status in ('error', 'error_deleting'):
                error_counts[vol_id] = error_counts.get(vol_id, 0) + 1
                if error_counts[vol_id] > max_error_retries:
                    LOG.error("Volume %s stuck in %s after %d retries, "
                              "giving up", vol_id, vol.status,
                              max_error_retries)
                    continue
                LOG.warning("Volume %s in %s state (attempt %d/%d), "
                            "resetting and retrying delete",
                            vol_id, vol.status,
                            error_counts[vol_id], max_error_retries)
                try:
                    cinder_client.volumes.reset_state(vol_id,
                                                      state='available')
                    cinder_client.volumes.delete(vol_id)
                except Exception as e:
                    LOG.warning("Retry delete for volume %s failed: %s",
                                vol_id, e)
                    try:
                        cinder_client.volumes.force_delete(vol_id)
                    except Exception:
                        pass

            still_pending.add(vol_id)

        remaining = still_pending
        if remaining:
            time.sleep(2)


def _force_detach_and_delete(cinder_client, volume_id, cluster_uuid):
    """Force-detach a stuck volume and delete it.

    Handles volumes stuck in 'in-use' state after their VM was deleted.
    """
    try:
        vol = cinder_client.volumes.get(volume_id)
    except cinder_exc.NotFound:
        LOG.info("Volume %s already deleted for cluster %s",
                 volume_id, cluster_uuid)
        return False

    if vol.status in ('deleting', 'deleted'):
        LOG.info("Volume %s already %s for cluster %s",
                 volume_id, vol.status, cluster_uuid)
        return False

    # Force-detach if volume is stuck in 'in-use' or 'attaching'/'detaching'
    if vol.status in ('in-use', 'attaching', 'detaching'):
        LOG.info("Force-detaching volume %s (status: %s) for cluster %s",
                 volume_id, vol.status, cluster_uuid)
        for attachment in vol.attachments:
            try:
                cinder_client.volumes.detach(volume_id,
                                             attachment['attachment_id'])
            except Exception:
                LOG.warning("Detach failed for volume %s attachment %s, "
                            "resetting state", volume_id,
                            attachment['attachment_id'])
        # Reset state to 'available' so we can delete
        try:
            cinder_client.volumes.reset_state(volume_id, state='available')
        except Exception as e:
            LOG.warning("Failed to reset volume %s state: %s",
                        volume_id, e)

    # If volume is in error state, reset to available first
    if vol.status == 'error':
        try:
            cinder_client.volumes.reset_state(volume_id, state='available')
        except Exception as e:
            LOG.warning("Failed to reset volume %s from error state: %s",
                        volume_id, e)

    try:
        cinder_client.volumes.delete(volume_id)
        LOG.info("Deleted volume %s for cluster %s",
                 volume_id, cluster_uuid)
        return True
    except cinder_exc.NotFound:
        return False
    except Exception as e:
        LOG.warning("Failed to delete volume %s for cluster %s: %s",
                    volume_id, cluster_uuid, e)
        # Try force-delete as last resort
        try:
            cinder_client.volumes.force_delete(volume_id)
            LOG.info("Force-deleted volume %s for cluster %s",
                     volume_id, cluster_uuid)
            return True
        except Exception as e2:
            LOG.error("Force-delete also failed for volume %s: %s",
                      volume_id, e2)
            raise


def delete_volumes(context, cluster):
    """Delete Cinder volumes for the cluster before Heat stack deletion.

    Finds all volume resources in the Heat stack, force-detaches any that
    are stuck in 'in-use' state (from deleted VMs), and deletes them.
    """
    if not cluster.stack_id:
        return

    from magnum.common import context as magnum_context
    adm_ctx = magnum_context.make_admin_context()
    adm_clients = clients.OpenStackClients(adm_ctx)

    try:
        heat_client = adm_clients.heat()
        cinder_client = adm_clients.cinder()
    except Exception as e:
        LOG.warning("Failed to initialize clients for volume cleanup "
                    "of cluster %s: %s", cluster.uuid, e)
        return

    # Collect all volume resource IDs from the Heat stack
    volume_ids = []
    for res_type in VOLUME_RESOURCE_TYPES:
        try:
            resources = heat_client.resources.list(
                cluster.stack_id, nested_depth=2,
                filters={"type": res_type})
            for res in resources:
                if res.physical_resource_id:
                    volume_ids.append(res.physical_resource_id)
        except heat_exc.HTTPNotFound:
            return
        except Exception as e:
            LOG.warning("Failed to list %s resources for cluster %s: %s",
                        res_type, cluster.uuid, e)

    if not volume_ids:
        return

    LOG.info("Found %d volumes to clean up for cluster %s: %s",
             len(volume_ids), cluster.uuid, volume_ids)

    deleted = []
    for vol_id in volume_ids:
        try:
            if _force_detach_and_delete(cinder_client, vol_id, cluster.uuid):
                deleted.append(vol_id)
        except Exception as e:
            LOG.error("Failed to clean up volume %s for cluster %s: %s",
                      vol_id, cluster.uuid, e)

    if deleted:
        _wait_for_volumes_deleted(cinder_client, deleted)
