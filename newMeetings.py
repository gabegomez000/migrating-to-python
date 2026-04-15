import asyncio
import datetime

from pricelist import pricelist, getTags, getCategories, getVenues
from alerts import sendDiscordAlert
from config_loader import load_config
from ramco_client import fetch_entities, MEETING_ATTRIBUTES
from event_processor import process_meeting
from wordpress_client import (
    load_reference_data, build_meeting_payload, submit_event_create,
)


def newMeetings():
    config = load_config()

    pricelist()
    getTags(config['WORDPRESS_URL'])
    getCategories(config['WORDPRESS_URL'])
    getVenues(config['WORDPRESS_URL'])

    date_start = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")

    try:
        meetings = fetch_entities(
            config, 'cobalt_meeting',
            f'createdon<ge>{date_start} AND statuscode<eq>1',
            MEETING_ATTRIBUTES,
        )
    except Exception as e:
        print(e)
        sendDiscordAlert(e)
        return

    if not meetings:
        print("No new meetings to process")
        return

    prices, tag_search, cat_search, venue_search = load_reference_data()

    try:
        for obj in meetings:
            print(f"Processing: {obj['cobalt_name']} - {obj['cobalt_meetingId']}")
            process_meeting(obj, prices, tag_search, cat_search, venue_search)
    except Exception as e:
        print(e)
        sendDiscordAlert(e)

    new_meetings = list(meetings)

    print(f"New Meetings: {len(new_meetings)}")

    async def submit_new_meeting(data):
        print(f"Submitting new meeting: {data['cobalt_meetingId']} - {data['cobalt_name']}")
        payload = build_meeting_payload(data)
        response = submit_event_create(config, payload)
        if response.status_code == 201:
            print(f"Meeting processed: {data['cobalt_name']}")
        else:
            msg = f"Error submitting meeting: {data['cobalt_name']} - {response.text} - {response.status_code}"
            print(msg)
            sendDiscordAlert(msg)

    async def submit_all(items):
        for obj in items:
            await submit_new_meeting(obj)

    asyncio.run(submit_all(new_meetings))


try:
    newMeetings()
except Exception as e:
    sendDiscordAlert(e)
    print(e)
