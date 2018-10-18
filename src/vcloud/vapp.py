import vcloud.client as Client

from pyvcloud.vcd.client import QueryResultFormat
from pyvcloud.vcd.client import VCLOUD_STATUS_MAP
from pyvcloud.vcd.utils import extract_id
from pyvcloud.vcd.vapp import VApp
from pyvcloud.vcd.client import TaskStatus

def find_vm_in_vapp(ctx, vm_name=None, vm_id=None):
    result = []
    try:
        resource_type = 'vApp'
        query = ctx.client.get_typed_query(
                resource_type,
                query_result_format=QueryResultFormat.ID_RECORDS)
        records = list(query.execute())
        for curr_vapp in records:
            vapp_id = curr_vapp.get('id')
            vapp_name = curr_vapp.get('name')
            vapp_href = curr_vapp.get('href')
            the_vapp = ctx.vdc.get_vapp(vapp_name)
            for vm in the_vapp.Children.Vm:
                if vm.get('name') == vm_name or \
                        extract_id(vm.get('id')) == vm_id:
                    result.append(
                        {
                            'vapp': extract_id(vapp_id),
                            'vapp_name': vapp_name,
                            'vm': extract_id(vm.get('id')),
                            'vm_name': vm.get('name'),
                            'vm_href': vm.get('href'),
                            'status': VCLOUD_STATUS_MAP.get(int(vm.get('status')))
                        }
                    )
                    break
        # Refresh session after Typed Query
        Client.login(session_id=ctx.token)
    except Exception as e:
        if ctx.config['debug'] == True:
            raise
        else:
            pass
    return result

def add_vm_to_vapp(ctx, spec={}):
    vapp_resource = ctx.vdc.get_vapp(spec['vapp'])
    the_vapp = VApp(ctx.client, resource=vapp_resource)
    catalog_item = ctx.org.get_catalog_item(ctx.config['catalog'], ctx.config['template'])
    source_vapp_resource = ctx.client.get_resource(catalog_item.Entity.get('href'))
    spec['vapp'] = source_vapp_resource
    spec['source_vm_name'] = ctx.config['source_vm_name']
    if type(spec['storage_profile']) == type(''):
        spec['storage_profile'] = ctx.vdc.get_storage_profile(spec['storage_profile'])
    vms = [spec]
    result = the_vapp.add_vms(vms)
    task = ctx.client.get_task_monitor().wait_for_status(
                        task=result,
                        timeout=60,
                        poll_frequency=2,
                        fail_on_statuses=None,
                        expected_target_statuses=[
                            TaskStatus.SUCCESS,
                            TaskStatus.ABORTED,
                            TaskStatus.ERROR,
                            TaskStatus.CANCELED],
                        callback=None)
    assert task.get('status') == TaskStatus.SUCCESS.value
