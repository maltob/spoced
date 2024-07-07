class ProviderBase(object):
    def __init__(self, config) -> None:
        pass
    def get_user_vm(provider, template_name, user_id):
        pass
    def get_vm_connection(provider,user_id,vmid):
        pass
    async def wait_for_vm_start(vm):
        pass
    async def wait_for_vm_guest(vm):
        pass
    async def run_vm_command(vm, command):
        pass
    async def get_vm_ip(vm):
        pass