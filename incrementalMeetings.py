import asyncio
import datetime

from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendNtfyAlert
from config_loader import load_config
from ramco_client import fetch_entities, MEETING_ATTRIBUTES
from event_processor import process_meeting
from wordpress_client import (
    load_reference_data, check_event_exists, merge_wp_tags_and_categories,
    build_meeting_payload, submit_event_update,
)
from classsync_logger import get_logger

logger = get_logger("incremental_meetings")


def incremental():
    config = load_config()

    logger.info("Starting incremental meeting sync")
    logger.info("Refreshing WordPress reference data")

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    date_start = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")

    try:
        meetings = fetch_entities(
            config, 'cobalt_meeting', f'modifiedon<ge>{date_start}', MEETING_ATTRIBUTES,
            logger=logger,
        )
    except Exception as e:
        logger.exception("Error fetching modified meetings")
        sendNtfyAlert(str(e), title="IncrementalMeetings: Error fetching meetings")
        return

    if not meetings:
        logger.info("No meetings to process")
        return

    prices, tag_search, cat_search, venue_search = load_reference_data(logger=logger)

    try:
        for obj in meetings:
            logger.info("Processing meeting: %s - %s", obj['cobalt_name'], obj['cobalt_meetingId'])
            process_meeting(obj, prices, tag_search, cat_search, venue_search, logger=logger)
    except Exception as e:
        logger.exception("Error processing meetings")
        sendNtfyAlert(str(e), title="IncrementalMeetings: Error processing meetings")

    existing_meetings = []
    featured_meetings = []
    new_meetings = []

    def check_if_exists(meetings):
        for obj in meetings:
            logger.info("Checking meeting: %s - %s", obj['cobalt_name'], obj['cobalt_meetingId'])
            wp_response = check_event_exists(config, obj['cobalt_meetingId'], logger=logger)

            if wp_response is not None:
                merge_wp_tags_and_categories(
                    obj, wp_response, 'cobalt_cobalt_tag_cobalt_meeting', 'categories'
                )
                if wp_response.get('image') is False:
                    logger.info("No meeting image for %s", obj['cobalt_meetingId'])
                    existing_meetings.append(obj)
                else:
                    obj['featuredImage'] = wp_response['image']['url']
                    logger.info("Found meeting image: %s", wp_response['image']['url'])
                    featured_meetings.append(obj)
            else:
                new_meetings.append(obj)

    try:
        check_if_exists(meetings)
    except Exception as e:
        logger.exception("Error checking whether meetings exist")
        sendNtfyAlert(str(e), title="IncrementalMeetings: Error checking if meeting exists")

    logger.info("Existing meetings: %d", len(existing_meetings))
    logger.info("Featured meetings: %d", len(featured_meetings))
    logger.info("New meetings: %d", len(new_meetings))

    async def submit_existing_meeting(data):
        logger.info("Updating existing meeting: %s - %s", data['cobalt_meetingId'], data['cobalt_name'])
        payload = build_meeting_payload(data)
        submit_event_update(config, data['cobalt_meetingId'], payload, logger=logger)
        logger.info("Meeting updated: %s", data['cobalt_name'])

    async def submit_featured_meeting(data):
        logger.info("Updating featured meeting: %s", data['cobalt_meetingId'])
        payload = build_meeting_payload(data, featured_image=data['featuredImage'])
        submit_event_update(config, data['cobalt_meetingId'], payload, logger=logger)
        logger.info("Featured meeting updated: %s", data['cobalt_name'])

    async def submit_all(items, submit_fn):
        for obj in items:
            await submit_fn(obj)

    asyncio.run(submit_all(existing_meetings, submit_existing_meeting))
    asyncio.run(submit_all(featured_meetings, submit_featured_meeting))


try:
    incremental()
except Exception as e:
    logger.exception("Incremental meeting sync failed")
    sendNtfyAlert(str(e), title="IncrementalMeetings: Unhandled Error")
