from pricelist import pricelist
from alerts import sendNtfyAlert
from config_loader import load_config
from logging_setup import setup_logging
from ramco_client import fetch_entity, MEETING_ATTRIBUTES
from event_processor import process_meeting
from wordpress_client import (
    load_reference_data, check_event_exists, merge_wp_tags_and_categories,
    build_meeting_payload, submit_event_create,
)

setup_logging('logs/Meeting.log')


def newMeetSingle(guid, staging):
    config = load_config(staging)

    # Only update pricelist for meetings (tags/categories/venues are loaded from cached json)
    pricelist()

    prices, tag_search, cat_search, venue_search = load_reference_data()

    try:
        data = fetch_entity(config, 'cobalt_meeting', guid, MEETING_ATTRIBUTES)
    except Exception as e:
        return e

    try:
        process_meeting(data, prices, tag_search, cat_search, venue_search)
    except Exception as e:
        sendNtfyAlert(str(e), title="NewMeetSingleModule: Error processing meeting")
        print(f"Error: {e}")
        return e

    new_meetings = []
    existing_meetings = []
    featured_meetings = []

    def check_if_exists(obj):
        print(f"Checking {obj['cobalt_name']} - {obj['cobalt_meetingId']}")
        wp_response = check_event_exists(config, obj['cobalt_meetingId'])

        if wp_response is not None:
            merge_wp_tags_and_categories(
                obj, wp_response, 'cobalt_cobalt_tag_cobalt_meeting', 'categories'
            )
            if wp_response.get('image') is False:
                print("No meeting image!")
                existing_meetings.append(obj)
            else:
                obj['featuredImage'] = wp_response['image']['url']
                print(wp_response['image']['url'])
                featured_meetings.append(obj)
        else:
            new_meetings.append(obj)

    try:
        check_if_exists(data)
    except Exception as e:
        sendNtfyAlert(str(e), title="NewMeetSingleModule: Error checking if meeting exists")
        print(f"Error: {e}")
        return e

    if not new_meetings:
        return "No new meetings to process"

    try:
        obj = new_meetings[0]
        print(f"Submitting new meeting: {obj['cobalt_name']} - {obj['cobalt_meetingId']}")
        payload = build_meeting_payload(obj)
        response = submit_event_create(config, payload)

        if response.status_code == 201:
            print(f"Meeting processed: {obj['cobalt_name']}")
            return f"Meeting submitted: {obj['cobalt_name']}"
        else:
            msg = f"Error submitting meeting: {obj['cobalt_name']} - {response.text} - {response.status_code}"
            print(msg)
            sendNtfyAlert(msg, title="NewMeetSingleModule: Error submitting meeting")
            return msg
    except Exception as e:
        sendNtfyAlert(str(e), title="NewMeetSingleModule: Error submitting meeting")
        print(f"Error: {e}")
        return e
