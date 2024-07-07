from providers.providerbase import ProviderBase
from proxmoxer import ProxmoxAPI
import time
from hashlib import md5
from proxmoxer.tools import Tasks

class Proxmox(ProviderBase):
    def __init__(self, config) -> None:
        self.proxmox = ProxmoxAPI(host=str(config.get('PROXMOX_HOST')),backend="https", service="PVE",user=str(config.get('PROXMOX_TOKEN_USER')),token_name=str(config.get('PROXMOX_TOKEN_NAME')),token_value=str(config.get('PROXMOX_TOKEN_VALUE')),verify_ssl=bool(config.get('PROXMOX_VERIFY_SSL',default=True)))

    async def get_user_vm(self, template_name, user_id):
        #Check if we have a VM for this user
        valid_vm = False
        template_vm = ''
        template_vm_node = ''
        user_tag = md5(bytes(user_id,encoding='UTF-8')).hexdigest()
        #Get all the templates on the 
        for node in self.proxmox.get('/api2/json/nodes'):
            for vm in self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu"):
                #We already have a VM
                if str.startswith(vm['name'],str(template_name)) and vm['name'] != template_name and 'template' not in vm and str(vm['tags']).find(user_tag)>=0 :
                    valid_vm = vm
                #Template in case we need a VM
                if 'template' in vm and vm['name'] == template_name:
                    template_vm = vm
                    template_vm_node = node
        if valid_vm == False:
            valid_vm = await self.clone_the_template(template_vm_node,template_vm,user_tag)
        return valid_vm
    
    async def get_vm_connection(self,user_id,vmid):
        pass

    async def get_next_vm_id(self):
        lowest_id=100
        taken_ids = []
        for node in self.proxmox.get('/api2/json/nodes'):
                for vm in self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu"):
                    taken_ids.append(int(vm['vmid']))
                for lxc in self.proxmox.get(f"/api2/json/nodes/{node['node']}/lxc"):
                    taken_ids.append(int(lxc['vmid']))
        while lowest_id in taken_ids:
            lowest_id+=1
        return lowest_id
    
    async def clone_the_template(self,node, vm, user_tag):
        newid = await self.get_next_vm_id()
        print(f"Creating {newid} for {user_tag}")
        res = self.proxmox.post(f"/api2/json/nodes/{node['node']}/qemu/{vm['vmid']}/clone",newid=newid,name=f"{vm['name']}.{newid}")
        self.proxmox.post(f"/api2/json/nodes/{node['node']}/qemu/{newid}/config",tags=f"auto_created;{user_tag}")
        
        Tasks.blocking_status(self.proxmox,res,timeout=120,polling_interval=1)
        valid_vm = self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu/{newid}/status/current")
        return valid_vm
    
    async def get_vm_node(self,vm):
         for node in self.proxmox.get('/api2/json/nodes'):
            for node_vm in self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu"):
                if int(vm['vmid']) == int(node_vm['vmid']):
                    return node
                
    async def get_vm_ip(self,vm,timelimit=30):
        node = await self.get_vm_node(vm)
        net = self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu/{vm['vmid']}/agent/network-get-interfaces")
        ip = None
        total_sleep = 0
        while ip == None and total_sleep < timelimit:
            for ipaddr in net['result'][0]['ip-addresses']:
                #TODO - Fix in the future for both ipv6 and if 127/8 is reallocated
                if ipaddr['ip-address-type'] == 'ipv4':
                    if not str.startswith(ipaddr['ip-address'],"127.0") and not str.startswith(ipaddr['ip-address'],"169."):
                        ip = ipaddr['ip-address']
            total_sleep += 1
            time.sleep(1)
        return ip

    async def wait_for_vm_start(self,vm):
        node = await self.get_vm_node(vm)
        if self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu/{vm['vmid']}/status/current")['status'] != 'running':
            self.proxmox.post(f"/api2/json/nodes/{node['node']}/qemu/{vm['vmid']}/status/start")
            #Wait for it to start
            time.sleep(5)
            while self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu/{vm['vmid']}/status/current")['status'] != 'running':
                time.sleep(0.3)
    
    async def wait_for_vm_guest(self,vm,timelimit=30):
        agent_up = False
        total_sleep = 0
        node = await self.get_vm_node(vm)
        while not agent_up and total_sleep < timelimit:
            try :
                agent_up = ('result' in self.proxmox.get(f"/api2/json/nodes/{node['node']}/qemu/{vm['vmid']}/agent/info"))
            except:
                total_sleep += 1
            time.sleep(1)
        return agent_up