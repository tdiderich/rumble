import requests
import os
import uuid
from flatten_json import flatten
from ipaddress import ip_address
from typing import Any, Dict, List
import runzero
from runzero.client import AuthError
from runzero.api import CustomAssets, CustomSourcesAdmin, Sites
from runzero.types import (
    CustomAttribute,
    ImportAsset,
    IPv4Address,
    IPv6Address,
    NetworkInterface,
    ImportTask
)

# runZero creds
RUNZERO_BASE_URL = 'https://console.runZero.com/api/v1.0'
RUNZERO_ORG_ID = os.environ['RUNZERO_ORG_ID']
RUNZERO_SITE_NAME = os.environ['RUNZERO_SITE_NAME']
RUNZERO_CLIENT_ID = os.environ['RUNZERO_CLIENT_ID']
RUNZERO_CLIENT_SECRET = os.environ['RUNZERO_CLIENT_SECRET']

# FortiThings
FORTI_KEY = os.environ['FORTI_KEY']
FORTI_HEADERS = {'Authorization': f'Basic {FORTI_KEY}'}
FORTI_BASE_URL = 'https://fortixdrnfrconnectna.console.ensilo.com'


def build_assets_from_json(json_input: List[Dict[str, Any]]) -> List[ImportAsset]:
    '''
    This is an example function to highlight how to handle converting data from an API into the ImportAsset format that
    is required for uploading to the runZero platform.
    This function assumes that the json has been converted into a list of dictionaries using `json.loads()` (or any
    similar functions).
    '''

    assets: List[ImportAsset] = []
    for item in json_input:
        # grab known API attributes from the json dict that are always present
        asset_id = item.get('id', uuid.uuid4)
        name = item.get('name', '')
        os = item.get('operatingSystem', '')
        macs = item.get('macAddresses', [])
        ip = item.get('ipAddress', '')

        if len(macs) > 0:
            mac = macs[0].replace('-', ':')
        else:
            mac = None

        # create the network interface
        network = build_network_interface(ips=[ip], mac=mac)

        # handle any additional values and insert into custom_attrs
        custom_attrs: Dict[str, CustomAttribute] = {}
        
        for key, value in item.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    custom_attrs[k] = CustomAttribute(str(v)[:1023])
            else:
                custom_attrs[key] = CustomAttribute(str(value))

        assets.append(
            ImportAsset(
                id=asset_id,
                networkInterfaces=[network],
                os=os,
                hostnames=[name],
                customAttributes=custom_attrs,
            )
        )
    return assets


def build_network_interface(ips: List[str], mac: str = None) -> NetworkInterface:
    '''
    This function converts a mac and a list of strings in either ipv4 or ipv6 format and creates a NetworkInterface that
    is accepted in the ImportAsset
    '''
    ip4s: List[IPv4Address] = []
    ip6s: List[IPv6Address] = []
    for ip in ips[:99]:
        ip_addr = ip_address(ip)
        if ip_addr.version == 4:
            ip4s.append(ip_addr)
        elif ip_addr.version == 6:
            ip6s.append(ip_addr)
        else:
            continue
    if mac is None:
        return NetworkInterface(ipv4Addresses=ip4s, ipv6Addresses=ip6s)
    else:
        return NetworkInterface(macAddress=mac, ipv4Addresses=ip4s, ipv6Addresses=ip6s)


def import_data_to_runzero(assets: List[ImportAsset]):
    '''
    The code below gives an example of how to create a custom source and upload valid assets from a CSV to a site using
    the new custom source.
    '''
    # create the runzero client
    c = runzero.Client()

    # try to log in using OAuth credentials
    try:
        c.oauth_login(RUNZERO_CLIENT_ID, RUNZERO_CLIENT_SECRET)
    except AuthError as e:
        print(f'login failed: {e}')
        return

    # create the site manager to get our site information
    site_mgr = Sites(c)
    site = site_mgr.get(RUNZERO_ORG_ID, RUNZERO_SITE_NAME)
    if not site:
        print(f'unable to find requested site')
        return

    # get or create the custom source manager and create a new custom source
    custom_source_mgr = CustomSourcesAdmin(c)
    my_asset_source = custom_source_mgr.get(name='fortiedr')
    if my_asset_source:
        source_id = my_asset_source.id
    else:
        my_asset_source = custom_source_mgr.create(name='fortiedr')
        source_id = my_asset_source.id

    # create the import manager to upload custom assets
    import_mgr = CustomAssets(c)
    import_task = import_mgr.upload_assets(
        org_id=RUNZERO_ORG_ID, site_id=site.id, source_id=source_id, assets=assets, task_info=ImportTask(name='FortiEDR Sync')
        )

    if import_task:
        print(
            f'task created! view status here: https://console.runzero.com/tasks?task={import_task.id}')


def main():
    url = f'{FORTI_BASE_URL}/management-rest/inventory/list-collectors'
    assets = requests.get(url, headers=FORTI_HEADERS)
    assets_json = assets.json()
    for a in assets_json:
        for k in a.keys():
            if isinstance(a[k], dict):
                a[k] = flatten(a[k])
    import_assets = build_assets_from_json(assets_json)
    import_data_to_runzero(assets=import_assets)


if __name__ == '__main__':
    main()
