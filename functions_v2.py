import json
from logs import logger
import os
import requests
from libs.data_gov_api import CKANPortalAPI


def get_data_json_from_url(url):
    logger.info(f'Geting data.json from {url}')
    try:
        req = requests.get(url, timeout=90)
    except Exception as e:
        error = 'ERROR Donwloading data: {} [{}]'.format(self.url, e)
        logger.error(error)
        return None

    if req.status_code >= 400:
        error = '{} HTTP error: {}'.format(url, req.status_code)
        logger.error(error)
        return None

    logger.info(f'OK {url}')

    try:
        data_json = json.loads(req.content) 
    except Exception as e:
        error = 'ERROR parsing JSON data: {}'.format(e)
        logger.error(error)
        return None

    logger.info(f'VALID JSON')

    if not data_json.get('dataset', False):
        logger.error('No dataset key')
        return None

    ret = data_json['dataset']
    logger.info('{} datasets'.format(len(ret)))

    return ret

def clean_duplicated_identifiers(rows):
    logger.info('Cleaning duplicates')
    unique_identifiers = []
    duplicates = []
    processed = 0
    for row in rows:
        if row['identifier'] not in unique_identifiers:
            unique_identifiers.append(row['identifier'])
            yield(row)
            processed += 1
        else:
            duplicates.append(row['identifier'])
            logger.error('Duplicated {}'.format(row['identifier']))
    logger.info('{} duplicates deleted. {} OK'.format(len(duplicates), processed))


def rename_datajson_package(package):
    package.pkg.descriptor['resources'][0]['name'] = 'datajson'
    yield package.pkg
    yield from package


def rename_ckanapi_package(package):
    package.pkg.descriptor['resources'][1]['name'] = 'ckanapi'
    yield package.pkg
    yield from package
    
    """
    resources = iter(package)
    if resources:
        yield from resources
    or
    yield from package

    error:

    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 62, in <genexpr>
        res_iter = (ResourceWrapper(self.get_res(current_dp, rw.res.name), rw.it)
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 65, in <genexpr>
        res_iter = (it if isinstance(it, ResourceWrapper) else ResourceWrapper(res, it)
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/helpers/iterable_loader.py", line 117, in process_resources
        yield from super(iterable_loader, self).process_resources(resources)
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 41, in process_resources
        for res in resources:
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 62, in <genexpr>
        res_iter = (ResourceWrapper(self.get_res(current_dp, rw.res.name), rw.it)
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 65, in <genexpr>
        res_iter = (it if isinstance(it, ResourceWrapper) else ResourceWrapper(res, it)
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 41, in process_resources
        for res in resources:
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 63, in <genexpr>
        for rw in res_iter_)
    File "/home/hudson/envs/data_json_etl/lib/python3.6/site-packages/dataflows/base/datastream_processor.py", line 54, in get_res
        assert ret is not None
    """

def validate_headers():
    pass


def split_headers(package):
    pass

def log_package_info(package):
    logger.info('--------------------------------')
    logger.info('Package processor')

    logger.info(f'Package: {package}')
    resources = package.pkg.descriptor['resources']
    for resource in resources:
        nice_resource = json.dumps(resource, indent=4)
        logger.info(f' - Resource: {nice_resource}')

    
    logger.info('--------------------------------')

def dbg_packages(package):
    log_package_info(package)

    yield package.pkg
    yield from package
    


def get_actual_ckan_resources_from_api(harvest_source_id=None):
    logger.info('Extracting from harvest source id: {}'.format(harvest_source_id))
    cpa = CKANPortalAPI()
    resources = 0
    
    page = 0
    for packages in cpa.search_harvest_packages(harvest_source_id=harvest_source_id):
        # getting resources in pages of packages
        page += 1
        logger.info('PAGE {} from harvest source id: {}'.format(page, harvest_source_id))
        for package in packages:
            pkg_resources = len(package['resources'])
            resources += pkg_resources
            yield(package)

        logger.info('{} total resources'.format(resources))