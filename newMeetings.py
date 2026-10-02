import asyncio
import datetime

from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendNtfyAlert
from config_loader import load_config
from ramco_client import fetch_entities, MEETING_ATTRIBUTES
from event_processor import process_meeting
from wordpress_client import (
    load_reference_data, build_meeting_payload, submit_event_create, check_event_exists
)
from classsync_logger import get_logger

logger = get_logger("new_meetings")


def newMeetings():
    config = load_config()
    failures = []
    
    logger.info("Starting new meetings job")

    logger.info("Refreshing WordPress reference data")
    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    date_start = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")

    logger.info("Looking for meetings created since %s", date_start)
    try:
        meetings = fetch_entities(
            config, 'cobalt_meeting',
            f'createdon<ge>{date_start} AND statuscode<eq>1',
            MEETING_ATTRIBUTES,
            logger=logger,
        )
    except Exception as e:
        logger.error("Error fetching new meetings: %s", e)
        sendNtfyAlert(str(e), title="NewMeetings: Error fetching new meetings")
        return

    if not meetings:
        logger.info("No new meetings to process")
        return

    prices, tag_search, cat_search, venue_search = load_reference_data(logger=logger)

    try:
        for obj in meetings:
            logger.info(
                "Processing meeting: %s - %s",
                obj['cobalt_name'],
                obj['cobalt_meetingId'],
            )
            process_meeting(obj, prices, tag_search, cat_search, venue_search, logger=logger)
    except Exception as e:
        logger.exception("Error processing meetings")
        sendNtfyAlert(str(e), title="NewMeetings: Error processing meetings")

    new_meetings = list(meetings)

    logger.info("New meetings to submit: %d", len(new_meetings))

    async def submit_new_meeting(data):
        if check_event_exists(config, data['cobalt_meetingId'], logger=logger):
            logger.info(
                "Skipping existing meeting: %s - %s",
                data['cobalt_name'],
                data['cobalt_meetingId'],
            )
            return
        payload = build_meeting_payload(data)
        response = submit_event_create(config, payload, logger=logger)
        if response.status_code == 201:
            logger.info("Meeting submitted: %s", data['cobalt_name'])
        else:
            msg = f"Error submitting meeting: {data['cobalt_name']} - {response.text} - {response.status_code}"
            logger.error(msg)
            sendNtfyAlert(msg, title="NewMeetings: Error submitting meeting")

    async def submit_all(items):
        for obj in items:
            await submit_new_meeting(obj)

    asyncio.run(submit_all(new_meetings))


try:
    newMeetings()
except Exception as e:
    logger.exception("New meetings job failed")
    sendNtfyAlert(str(e), title="NewMeetings: Unhandled Error")
