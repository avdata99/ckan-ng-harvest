from logs import logger
import config
from libs.ckan_adapters import DataJSONSchema1_1
from libs.data_gov_api import CKANPortalAPI
import json
from datetime import datetime
import pytz
import hashlib


def hash_dataset(datasetdict):
    # hash the dataset.
    # We change the way that previous harvester do this
    #  https://github.com/GSA/ckanext-datajson/blob/datagov/ckanext/datajson/harvester_base.py#L730
    dmp_dataset = json.dumps(datasetdict, sort_keys=True)
    str_to_hash = dmp_dataset.encode('utf-8')
    return hashlib.sha1(str_to_hash).hexdigest()


def write_results_to_ckan(rows):
    """ each row it's a dataset to delete/update/create """

    actions = {}
    c = 0
    for row in rows:
        c += 1

        comparison_results = row['comparison_results']
        action = comparison_results['action']
        if action not in actions.keys():
            actions[action] = {'total': 0, 'success': 0, 'fails': 0}
        actions[action]['total'] += 1

        dump_comp_res = json.dumps(comparison_results, indent=4)
        # logger.info(f'Previous results {dump_comp_res}')
        """ comparison_results is something like this
        row['comparison_results'] {
            "action": "update" | "delete" | "create",
            "ckan_id": "1bfc8520-17b0-46b9-9940-a6646615436c",
            "new_data": {data json dataset format},
            "reason": "Some reason for the action"
            }
        """

        if action == 'error':
            results = {'success': False}
            comparison_results['action_results'] = results
            yield row
            continue

        if action in ['update', 'create']:
            datajson_dataset = comparison_results['new_data']

            # add required extras

            schema_version = datajson_dataset['headers']['schema_version']  # 1.1 or 1.0
            assert schema_version in ['1.0', '1.1']
            datajson_dataset['source_schema_version'] = schema_version
            datajson_dataset['source_hash'] = hash_dataset(datasetdict=datajson_dataset)

            # harvest extras
            # check if a local harvest source is required
            # https://github.com/ckan/ckanext-harvest/blob/master/ckanext/harvest/logic/action/create.py#L27
            datajson_dataset['harvest_ng_source_title'] = config.SOURCE_NAME
            datajson_dataset['harvest_ng_source_id'] = config.SOURCE_ID

            # CKAN hides this extras if we not define as harvest type
            # if https://github.com/ckan/ckanext-harvest/blob/3a72337f1e619bf9ea3221037ca86615ec22ae2f/ckanext/harvest/plugin.py#L125
            datajson_dataset['harvest_source_title'] = config.SOURCE_NAME
            datajson_dataset['harvest_source_id'] = config.SOURCE_ID

            djss = DataJSONSchema1_1(original_dataset=datajson_dataset)
            # ORG is required!
            djss.ckan_owner_org_id = config.CKAN_OWNER_ORG

            ckan_dataset = djss.transform_to_ckan_dataset()

        results = {'success': False}
        if action == 'create':
            cpa = CKANPortalAPI(base_url=config.CKAN_CATALOG_URL,
                                api_key=config.CKAN_API_KEY)

            try:
                ckan_response = cpa.create_package(ckan_package=ckan_dataset)
            except Exception as e:
                ckan_response = {'success': False, 'error': str(e)}

            results = {'success': ckan_response['success']}
            results['ckan_response'] = ckan_response

            if ckan_response['success']:
                actions[action]['success'] += 1
            else:
                actions[action]['fails'] += 1

        elif action == 'update':
            cpa = CKANPortalAPI(base_url=config.CKAN_CATALOG_URL,
                                api_key=config.CKAN_API_KEY)

            try:
                ckan_response = cpa.update_package(ckan_package=ckan_dataset)
            except Exception as e:
                ckan_response = {'success': False, 'error': str(e)}

            results = {'success': ckan_response['success']}
            results['ckan_response'] = ckan_response

            if ckan_response['success']:
                actions[action]['success'] += 1
            else:
                actions[action]['fails'] += 1

        elif action == 'delete':
            ckan_id = row['comparison_results']['ckan_id']
            cpa = CKANPortalAPI(base_url=config.CKAN_CATALOG_URL, api_key=config.CKAN_API_KEY)

            try:
                ckan_response = cpa.delete_package(ckan_package_ir_or_name=ckan_id)
            except Exception as e:
                ckan_response = {'success': False, 'error': str(e)}

            results = {'success': ckan_response['success']}
            results['ckan_response'] = ckan_response

            if ckan_response['success']:
                actions[action]['success'] += 1
            else:
                actions[action]['fails'] += 1

        elif action == 'ignore':
            continue
            results = {'success': True}

        else:
            error = 'Unexpected action for this dataset: {}'.format(action)
            results = {'success': False, 'error': error}

        results['timestamp'] = datetime.now(pytz.utc).isoformat()  # iso format move as string to save to disk
        comparison_results['action_results'] = results
        yield row

    logger.info(f'Actions detected {actions}')


def write_final_report():
    """ take all generated data and write a final report """
    pass
