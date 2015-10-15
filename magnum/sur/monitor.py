from magnum.sur.common.cadvisor_utils import CadvisorUtils

from oslo_log import log


LOG = log.getLogger(__name__)


def pull_data(address_list):
    
    total_memory = 0.0
    used_memory = 0.0

    lost_flag = False
    
    for address in address_list:
        utils = CadvisorUtils(host=address)

        total_memory_info = utils.get_machine_memory()
        used_memory_info = utils.get_containers_memory_usage()

        if total_memory_info is None or used_memory_info is None:
            lost_flag = True
            LOG.warn('Cannot pull metrics from %s. '
                     'cAdvisor is still pulling.' % address)
            break

        LOG.info('Pull metrics from %s successfully. [Total Memory=%s, '
                 'Usage Memory=%s]' % (address, total_memory_info, used_memory_info))
        
        total_memory += total_memory_info
        used_memory += used_memory_info

    if lost_flag or total_memory == 0.0:
        return 0.0
    
    return used_memory / total_memory * 100

