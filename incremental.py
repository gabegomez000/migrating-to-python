import asyncio
import datetime

from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendNtfyAlert
from config_loader import load_config
from ramco_client import fetch_entities, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, check_event_exists, merge_wp_tags_and_categories,
    build_class_payload, submit_event_update,
)
from classsync_logger import get_logger

logger = get_logger("incremental_classes")


def incremental():
    config = load_config()

    logger.info("Starting incremental class sync")
    logger.info("Refreshing WordPress reference data")

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    date_start = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")

    try:
        classes = fetch_entities(
            config, 'cobalt_class', f'modifiedon<ge>{date_start}', CLASS_ATTRIBUTES,
            logger=logger,
        )
    except Exception as e:
        logger.exception("Error fetching modified classes")
        sendNtfyAlert(str(e), title="Incremental: Error fetching classes")
        return

    if not classes:
        logger.info("No classes to process")
        return

    prices, tag_search, cat_search, venue_search = load_reference_data(logger=logger)

    try:
        for obj in classes:
            logger.info("Processing class: %s - %s", obj['cobalt_name'], obj['cobalt_classId'])
            process_class(obj, prices, tag_search, cat_search, venue_search, logger=logger)
    except Exception as e:
        logger.exception("Error processing classes")
        sendNtfyAlert(str(e), title="Incremental: Error processing classes")

    existing_classes = []
    featured_classes = []
    new_classes = []
    class_shadowrealm = []

    def check_if_exists(classes):
        for obj in classes:
            if obj['ramcosub_calendar_override'] == 'false':
                logger.info("Checking class: %s - %s", obj['cobalt_name'], obj['cobalt_classId'])
                wp_response = check_event_exists(config, obj['cobalt_classId'], logger=logger)

                if wp_response is not None:
                    merge_wp_tags_and_categories(
                        obj, wp_response, 'cobalt_cobalt_tag_cobalt_class', 'categories'
                    )
                    if wp_response.get('image') is False:
                        logger.info("No class image for %s", obj['cobalt_classId'])
                        existing_classes.append(obj)
                    else:
                        obj['featuredImage'] = wp_response['image']['url']
                        logger.info("Found class image: %s", wp_response['image']['url'])
                        featured_classes.append(obj)
                else:
                    new_classes.append(obj)
            else:
                logger.info("Skipping overridden class: %s - %s", obj['cobalt_name'], obj['cobalt_classId'])
                class_shadowrealm.append(obj)

    try:
        check_if_exists(classes)
    except Exception as e:
        logger.exception("Error checking whether classes exist")
        sendNtfyAlert(str(e), title="Incremental: Error checking if class exists")

    logger.info("Existing classes: %d", len(existing_classes))
    logger.info("Featured classes: %d", len(featured_classes))
    logger.info("New classes: %d", len(new_classes))
    logger.info("Overridden classes skipped: %d", len(class_shadowrealm))

    async def submit_existing_class(data):
        logger.info("Updating existing class: %s - %s", data['cobalt_classId'], data['cobalt_name'])
        payload = build_class_payload(data)
        submit_event_update(config, data['cobalt_classId'], payload, logger=logger)
        logger.info("Class updated: %s", data['cobalt_name'])

    async def submit_featured_class(data):
        logger.info("Updating featured class: %s", data['cobalt_classId'])
        payload = build_class_payload(data, featured_image=data['featuredImage'])
        submit_event_update(config, data['cobalt_classId'], payload, logger=logger)
        logger.info("Featured class updated: %s", data['cobalt_name'])

    async def submit_all(items, submit_fn):
        for obj in items:
            await submit_fn(obj)

    asyncio.run(submit_all(existing_classes, submit_existing_class))
    asyncio.run(submit_all(featured_classes, submit_featured_class))


try:
    incremental()
except Exception as e:
    logger.exception("Incremental class sync failed")
    sendNtfyAlert(str(e), title="Incremental: Unhandled Error")
