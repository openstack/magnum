from magnum.sur.common.cadvisor_utils import CadvisorUtils


def pull_data(address_list):

    total_memory = 0.0
    used_memory = 0.0

    for address in address_list:
        utils = CadvisorUtils(host=address)

        total_memory += utils.get_machine_memory()
        used_memory += utils.get_containers_memory_usage()

    return used_memory / total_memory * 100
