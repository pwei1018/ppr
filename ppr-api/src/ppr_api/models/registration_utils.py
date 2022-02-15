# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-few-public-methods

"""This module holds methods to support registration model updates - mostly account registration summary."""
# from enum import Enum
# from http import HTTPStatus
# import json

# from flask import current_app
from ppr_api.models import utils as model_utils
from ppr_api.services.authz import is_all_staff_account


PARAM_TO_ORDER_BY = {
    'registrationNumber': 'registration_number',
    'registrationType': 'registration_type',
    'registeringName': 'registering_name',
    'clientReferenceId': 'client_reference_id',
    'startDateTime': 'registration_ts',
    'endDateTime': 'registration_ts'
}
PARAM_TO_ORDER_BY_CHANGE = {
    'registrationNumber': 'arv2.registration_number',
    'registrationType': 'arv2.registration_type',
    'registeringName': 'arv2.registering_name',
    'clientReferenceId': 'arv2.client_reference_id',
    'startDateTime': 'arv2.registration_ts',
    'endDateTime': 'arv2.registration_ts'
}

FINANCING_PATH = '/ppr/api/v1/financing-statements/'
QUERY_ACCOUNT_REG_DEFAULT_ORDER = ' ORDER BY registration_ts DESC'
QUERY_ACCOUNT_CHANGE_DEFAULT_ORDER = ' ORDER BY arv2.registration_ts DESC'
QUERY_ACCOUNT_REG_LIMIT = ' LIMIT :page_size OFFSET :page_offset'
QUERY_ACCOUNT_REG_NUM_CLAUSE = """
 AND (arv.registration_number LIKE :reg_num || '%' OR
      EXISTS (SELECT arv2.financing_id
                FROM account_registration_vw arv2
               WHERE arv2.financing_id = arv.financing_id
                 AND arv2.registration_type_cl NOT IN ('CROWNLIEN', 'MISCLIEN', 'PPSALIEN')
                 AND arv2.registration_number LIKE :reg_num || '%'))
"""
QUERY_ACCOUNT_CLIENT_REF_CLAUSE = " AND arv.client_reference_id LIKE :client_reference_id || '%'"
QUERY_ACCOUNT_REG_NAME_CLAUSE = " AND arv.registering_name LIKE :registering_name || '%'"
QUERY_ACCOUNT_STATUS_CLAUSE = ' AND arv.state = :status_type'
QUERY_ACCOUNT_REG_TYPE_CLAUSE = ' AND arv.registration_type = :registration_type'
QUERY_ACCOUNT_REG_DATE_CLAUSE = """
 AND arv.registration_ts BETWEEN (TO_TIMESTAMP(:start_date_time, 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') AND
                             (TO_TIMESTAMP(:end_date_time, 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc')
 """
QUERY_ACCOUNT_CHANGE_REG_NUM_CLAUSE = " AND arv2.registration_number LIKE :reg_num || '%'"
QUERY_ACCOUNT_CHANGE_CLIENT_REF_CLAUSE = " AND arv2.client_reference_id LIKE :client_reference_id || '%'"
QUERY_ACCOUNT_CHANGE_REG_NAME_CLAUSE = " AND arv2.registering_name LIKE :registering_name || '%'"
QUERY_ACCOUNT_CHANGE_STATUS_CLAUSE = ' AND arv2.state = :status_type'
QUERY_ACCOUNT_CHANGE_REG_TYPE_CLAUSE = ' AND arv2.registration_type = :registration_type'
QUERY_ACCOUNT_CHANGE_REG_DATE_CLAUSE = """
 AND arv2.registration_ts BETWEEN (TO_TIMESTAMP(:start_date_time, 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') AND
                             (TO_TIMESTAMP(:end_date_time, 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc')
 """


class AccountRegistrationParams():
    """Contains parameter values to use when querying account summary registration information."""

    account_id: str
    collapse: bool = False
    account_name: str = None
    sbc_staff: bool = False
    from_ui: bool = False
    sort_direction: str = 'desc'
    page_number: int = 1
    sort_criteria: str = None
    registration_number: str = None
    registration_type: str = None
    start_date_time: str = None
    end_date_time: str = None
    status_type: str = None
    client_reference_id: str = None
    registering_name: str = None

    def __init__(self, account_id, collapse: bool = False, account_name: str = None, sbc_staff: bool = False):
        """Set common base initialization."""
        self.account_id = account_id
        self.account_name = account_name
        self.collapse = collapse
        self.sbc_staff = sbc_staff


def can_access_report(account_id: str, account_name: str, reg_json, sbc_staff: bool = False) -> bool:
    """Determine if request account can view the registration verification statement."""
    # All staff roles can see any verification statement.
    reg_account_id = reg_json['accountId']
    if is_all_staff_account(account_id) or sbc_staff:
        return True
    if account_id == reg_account_id:
        return True
    if account_name:
        if reg_json['registeringParty'] == account_name:
            return True
        sp_names = reg_json['securedParties']
        if sp_names and account_name in sp_names:
            return True
    return False


def update_summary_optional(reg_json, account_id: str, sbc_staff: bool = False):
    """Single summary result replace optional property 'None' with ''."""
    if not reg_json['registeringName'] or reg_json['registeringName'].lower() == 'none':
        reg_json['registeringName'] = ''
    # Only staff role or matching account includes registeringName
    elif not is_all_staff_account(account_id) and not sbc_staff and 'accountId' in reg_json and \
            account_id != reg_json['accountId']:
        reg_json['registeringName'] = ''

    if not reg_json['clientReferenceId'] or reg_json['clientReferenceId'].lower() == 'none':
        reg_json['clientReferenceId'] = ''
    return reg_json


def build_account_collapsed_json(financing_json, registrations_json):
    """Organize account registrations as parent/child financing statement/change registrations."""
    for statement in financing_json:
        changes = []
        for registration in registrations_json:
            if statement['registrationNumber'] == registration['baseRegistrationNumber']:
                changes.append(registration)
        if changes:
            statement['changes'] = changes
    return financing_json


def build_account_collapsed_filter_json(financing_json, registrations_json, params: AccountRegistrationParams):
    """Organize account registrations as parent/child financing statement/change registrations."""
    for statement in financing_json:
        changes = []
        for registration in registrations_json:
            if statement['registrationNumber'] == registration['baseRegistrationNumber']:
                changes.append(registration)
                if params.registration_number and \
                        registration['registrationNumber'].startswith(params.registration_number):
                    statement['expand'] = True
                elif params.client_reference_id and \
                        registration['clientReferenceId'].startswith(params.client_reference_id):
                    statement['expand'] = True
        if changes:
            statement['changes'] = changes
    return financing_json


def set_path(params: AccountRegistrationParams, result, reg_num: str, base_reg_num: str):
    """Set path to the verification statement."""
    reg_class = result['registrationClass']
    if model_utils.is_financing(reg_class):
        result['baseRegistrationNumber'] = reg_num
        result['path'] = FINANCING_PATH + reg_num
    elif reg_class == model_utils.REG_CLASS_DISCHARGE:
        result['path'] = FINANCING_PATH + base_reg_num + '/discharges/' + reg_num
    elif reg_class == model_utils.REG_CLASS_RENEWAL:
        result['path'] = FINANCING_PATH + base_reg_num + '/renewals/' + reg_num
    elif reg_class == model_utils.REG_CLASS_CHANGE:
        result['path'] = FINANCING_PATH + base_reg_num + '/changes/' + reg_num
    elif reg_class in (model_utils.REG_CLASS_AMEND, model_utils.REG_CLASS_AMEND_COURT):
        result['path'] = FINANCING_PATH + base_reg_num + '/amendments/' + reg_num

    if not can_access_report(params.account_id, params.account_name, result, params.sbc_staff):
        result['path'] = ''

    return result


def get_account_reg_query_order(params: AccountRegistrationParams) -> str:
    """Get the account registration query order by clause from the provided parameters."""
    order_by: str = QUERY_ACCOUNT_REG_DEFAULT_ORDER
    if not params.sort_criteria:
        return order_by
    if param_order_by := PARAM_TO_ORDER_BY.get(params.sort_criteria, None):
        sort_order = 'DESC'
        if params.sort_direction and params.sort_direction in ('asc', 'ascending', 'desc', 'descending'):
            sort_order = params.sort_direction
        order_by = ' ORDER BY ' + param_order_by + ' ' + sort_order
    return order_by


def get_account_change_query_order(params: AccountRegistrationParams) -> str:
    """Get the account change registration query order by clause from the provided parameters."""
    order_by: str = QUERY_ACCOUNT_CHANGE_DEFAULT_ORDER
    if not params.sort_criteria:
        return order_by
    if param_order_by := PARAM_TO_ORDER_BY_CHANGE.get(params.sort_criteria, None):
        sort_order = 'DESC'
        if params.sort_direction and params.sort_direction in ('asc', 'ascending', 'desc', 'descending'):
            sort_order = params.sort_direction
        order_by = ' ORDER BY ' + param_order_by + ' ' + sort_order
    return order_by


def build_account_reg_base_query(params: AccountRegistrationParams) -> str:
    """Build the account registration base query from the provided parameters."""
    base_query: str = model_utils.QUERY_ACCOUNT_BASE_REG_BASE
    if params.registration_number:
        base_query += QUERY_ACCOUNT_REG_NUM_CLAUSE
    if params.registration_type:
        base_query += QUERY_ACCOUNT_REG_TYPE_CLAUSE
    if params.client_reference_id:
        base_query += QUERY_ACCOUNT_CLIENT_REF_CLAUSE
    if params.registering_name:
        base_query += QUERY_ACCOUNT_REG_NAME_CLAUSE
    if params.status_type:
        base_query += QUERY_ACCOUNT_STATUS_CLAUSE
    if params.start_date_time and params.end_date_time:
        base_query += QUERY_ACCOUNT_REG_DATE_CLAUSE
    return base_query


def build_account_change_base_query(params: AccountRegistrationParams) -> str:
    """Build the account change registration base query from the provided parameters."""
    base_query: str = model_utils.QUERY_ACCOUNT_CHANGE_REG_BASE
    if params.registration_number:
        base_query += QUERY_ACCOUNT_CHANGE_REG_NUM_CLAUSE
    if params.registration_type:
        base_query += QUERY_ACCOUNT_CHANGE_REG_TYPE_CLAUSE
    if params.client_reference_id:
        base_query += QUERY_ACCOUNT_CHANGE_CLIENT_REF_CLAUSE
    if params.registering_name:
        base_query += QUERY_ACCOUNT_CHANGE_REG_NAME_CLAUSE
    if params.status_type:
        base_query += QUERY_ACCOUNT_CHANGE_STATUS_CLAUSE
    if params.start_date_time and params.end_date_time:
        base_query += QUERY_ACCOUNT_CHANGE_REG_DATE_CLAUSE
    order_by: str = get_account_change_query_order(params)
    base_query += order_by
    base_query += QUERY_ACCOUNT_REG_LIMIT
    return base_query


def build_account_reg_query(params: AccountRegistrationParams) -> str:
    """Build the account registration query from the provided parameters."""
    base_query: str = build_account_reg_base_query(params)
    order_by: str = get_account_reg_query_order(params)
    query: str = 'SELECT * FROM (' + base_query + ') AS q '
    query += order_by
    query += QUERY_ACCOUNT_REG_LIMIT
    return query


def build_account_change_query(params: AccountRegistrationParams) -> str:
    """Build the account registration change query from the provided parameters."""
    base_query: str = build_account_change_base_query(params)
    query: str = model_utils.QUERY_ACCOUNT_CHANGE_REG.replace('QUERY_ACCOUNT_CHANGE_REG_BASE', base_query)
    return query


def build_account_query_params(params: AccountRegistrationParams) -> dict:
    """Build the account query runtime parameter set from the provided parameters."""
    page_size: int = model_utils.get_max_registrations_size()
    page_offset: int = params.page_number
    if page_offset <= 1:
        page_offset = 0
    else:
        page_offset = (page_offset - 1) * page_size
    query_params = {
        'query_account': params.account_id,
        'page_size': page_size,
        'page_offset': page_offset
    }
    if params.registration_number:
        query_params['reg_num'] = params.registration_number.upper()
    if params.registration_type:
        query_params['registration_type'] = params.registration_type
    if params.client_reference_id:
        query_params['client_reference_id'] = params.client_reference_id
    if params.registering_name:
        query_params['registering_name'] = params.registering_name
    if params.status_type:
        query_params['status_type'] = params.status_type
    if params.start_date_time and params.end_date_time:
        start_ts: str = params.start_date_time.replace('T', ' ')
        end_ts: str = params.end_date_time.replace('T', ' ')
        query_params['start_date_time'] = start_ts
        query_params['end_date_time'] = end_ts
    return query_params


def build_account_base_reg_results(params, rows) -> dict:
    """Build the account query base registration results from the query result set."""
    results_json = []
    if rows is not None:
        for row in rows:
            mapping = row._mapping  # pylint: disable=protected-access; follows documentation
            reg_class = str(mapping['registration_type_cl'])
            if model_utils.is_financing(reg_class):
                results_json.append(__build_account_reg_result(params, mapping, reg_class))

    return results_json


def update_account_reg_results(params, rows, results_json) -> dict:
    """Build the account query base registration results from the query result set."""
    if results_json and rows is not None:
        changes_json = []
        for row in rows:
            mapping = row._mapping  # pylint: disable=protected-access; follows documentation
            reg_class = str(mapping['registration_type_cl'])
            if not model_utils.is_financing(reg_class):
                changes_json.append(__build_account_reg_result(params, mapping, reg_class))
        if changes_json:
            return build_account_collapsed_filter_json(results_json, changes_json, params)
    return results_json


def __build_account_reg_result(params, mapping, reg_class) -> dict:
    """Build a registration result from a query result set row."""
    reg_num = str(mapping['registration_number'])
    base_reg_num = str(mapping['base_reg_number'])
    registering_name = str(mapping['registering_name'])
    if not registering_name:
        registering_name = ''
    result = {
        'accountId': str(mapping['orig_account_id']),
        'registrationNumber': reg_num,
        'baseRegistrationNumber': base_reg_num,
        'createDateTime': model_utils.format_ts(mapping['registration_ts']),
        'registrationType': str(mapping['registration_type']),
        'registrationDescription': str(mapping['registration_desc']),
        'registrationClass': reg_class,
        'statusType': str(mapping['state']),
        'expireDays': int(mapping['expire_days']),
        'lastUpdateDateTime': model_utils.format_ts(mapping['last_update_ts']),
        'registeringParty': str(mapping['registering_party']),
        'securedParties': str(mapping['secured_party']),
        'clientReferenceId': str(mapping['client_reference_id']),
        'registeringName': registering_name,
        'expand': False
    }
    result = set_path(params, result, reg_num, base_reg_num)
    result = update_summary_optional(result, params.account_id, params.sbc_staff)
    if 'accountId' in result:
        del result['accountId']  # Only use this for report access checking.
    return result