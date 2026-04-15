from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendDiscordAlert
from config_loader import load_config
from logging_setup import setup_logging
from ramco_client import fetch_entity, CLASS_ATTRIBUTES
from event_processor import process_class
from wordpress_client import (
    load_reference_data, check_event_exists, merge_wp_tags_and_categories,
    build_class_payload, submit_event_create,
)

setup_logging('logs/newClassSingle.log')


def newClassSingle(guid, staging):
    config = load_config(staging)

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    prices, tag_search, cat_search, venue_search = load_reference_data()

    try:
        data = fetch_entity(config, 'cobalt_class', guid, CLASS_ATTRIBUTES)
    except Exception as e:
        return e

    try:
        process_class(data, prices, tag_search, cat_search, venue_search)
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e

    new_classes = []
    existing_classes = []
    featured_classes = []
    class_shadowrealm = []

    def check_if_exists(obj):
        if obj['ramcosub_calendar_override'] == 'false':
            print(f"Checking {obj['cobalt_name']} - {obj['cobalt_classId']}")
            wp_response = check_event_exists(config, obj['cobalt_classId'])

            if wp_response is not None:
                merge_wp_tags_and_categories(
                    obj, wp_response, 'cobalt_cobalt_tag_cobalt_class', 'categories'
                )
                if wp_response.get('image') is False:
                    print("No class image!")
                    existing_classes.append(obj)
                else:
                    obj['featuredImage'] = wp_response['image']['url']
                    print(wp_response['image']['url'])
                    featured_classes.append(obj)
            else:
                new_classes.append(obj)
        else:
            print(f"Sending {obj['cobalt_name']} - {obj['cobalt_classId']} to the shadowrealm")
            class_shadowrealm.append(obj)

    try:
        check_if_exists(data)
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e

    if not new_classes:
        return "No new classes to process"

    try:
        obj = new_classes[0]
        print(f"Submitting new class: {obj['cobalt_name']} - {obj['cobalt_classId']}")
        payload = build_class_payload(obj)
        response = submit_event_create(config, payload)

        if response.status_code == 201:
            print(f"Class processed: {obj['cobalt_name']}")
            return f"Class submitted: {obj['cobalt_name']}"
        else:
            msg = f"Error submitting class: {obj['cobalt_name']} - {response.text} - {response.status_code}"
            print(msg)
            sendDiscordAlert(msg)
            return msg
    except Exception as e:
        sendDiscordAlert(f"Error: {e}")
        print(f"Error: {e}")
        return e
