import json
import logging
import requests
from alerts import sendNtfyAlert

CLASS_ATTRIBUTES = (
    'cobalt_classbegindate,cobalt_classenddate,cobalt_classid,cobalt_locationid,'
    'cobalt_name,cobalt_description,cobalt_locationid,'
    'cobalt_cobalt_tag_cobalt_class/cobalt_name,cobalt_fullday,cobalt_publishtoportal,'
    'statuscode,cobalt_cobalt_classinstructor_cobalt_class/cobalt_name,'
    'cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_productid,'
    'cobalt_cobalt_class_cobalt_classregistrationfee/statuscode,'
    'cobalt_outsideprovider,cobalt_outsideproviderlink,'
    'cobalt_cobalt_class_cobalt_classregistrationfee/cobalt_publishtoportal,'
    'ramcosub_calendar_override'
)

MEETING_ATTRIBUTES = (
    'cobalt_BeginDate,cobalt_EndDate,cobalt_meetingId,cobalt_location,'
    'cobalt_name,ramco_description,'
    'cobalt_cobalt_tag_cobalt_meeting/cobalt_name,cobalt_fullday,cobalt_publishtoportal,'
    'statuscode,'
    'cobalt_meeting_cobalt_meetingregistrationfees/cobalt_productid,'
    'cobalt_outsideprovider,'
    'cobalt_meeting_cobalt_meetingregistrationfees/statuscode,'
    'cobalt_meeting_cobalt_meetingregistrationfees/cobalt_publishtoportal,'
    'cobalt_outsideproviderlink'
)


def fetch_entity(config, entity, guid, attributes, logger=None):
    """Fetch a single entity from the RAMCO API (GetEntity).

    Returns:
        The parsed Data object from the response.

    Raises:
        Exception: Re-raises after sending a Discord alert.
    """
    logger = logger or logging.getLogger(__name__)
    payload = {
        'Key': config['API_KEY'],
        'Operation': 'GetEntity',
        'Entity': entity,
        'Guid': guid,
        'Attributes': attributes,
    }
    try:
        logger.info("Fetching RAMCO entity %s with id %s", entity, guid)
        r = requests.post(config['API_URL'], data=payload)
        data = json.loads(r.text)
        return data['Data']
    except Exception as e:
        sendNtfyAlert(str(e), title="RAMCO API: Error fetching entity")
        logger.exception("Error fetching RAMCO entity %s with id %s", entity, guid)
        raise


def fetch_entities(config, entity, filter_str, attributes, logger=None):
    """Fetch multiple entities from the RAMCO API (GetEntities).

    Returns:
        List of entity dicts, or an empty list if the response has no 'Data' key.

    Raises:
        Exception: Re-raises after sending a Discord alert.
    """
    logger = logger or logging.getLogger(__name__)
    payload = {
        'Key': config['API_KEY'],
        'Operation': 'GetEntities',
        'Entity': entity,
        'Filter': filter_str,
        'Attributes': attributes,
    }
    try:
        logger.info("Fetching RAMCO entities for %s with filter %s", entity, filter_str)
        r = requests.post(config['API_URL'], data=payload)
        data = json.loads(r.text)
        return data.get('Data', [])
    except Exception as e:
        sendNtfyAlert(str(e), title="RAMCO API: Error fetching entities")
        logger.exception("Error fetching RAMCO entities for %s", entity)
        raise
