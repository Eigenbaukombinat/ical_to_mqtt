from icalevents.icalevents import events
import argparse
import datetime
import json
import logging
import os
import paho.mqtt.client as mqtt
import pytz
import sys
import time


def setup_logging(level):
    log = logging.getLogger()
    log.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def get_events(fn):
    # getting all events from the coming year, just in case someone
    # sets very early alarms. ;)
    start = datetime.datetime.now() - datetime.timedelta(days=1)
    end = start + datetime.timedelta(days=365)
    es = events(file=fn, start=start, end=end)
    notifications = []
    # return all alarms of all events
    for event in es:
        for alarm in event.alarms:
            notifications.append((alarm, event))
    return notifications


def load_calendar_files(path):
    """Load and parse all .ics files in the given path.
    Returns all alarms from all found calendars."""
    result = []
    log.info('Looking for calendar files in %s.', path)
    for filename in os.listdir(path):
        if filename.endswith('.ics'):
            log.info('Reading %s', filename)
            result += get_events(filename)
    log.info('Done loading calendars. Found %s notifications.', len(result))
    return result


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


def filter_multiple_alarms_by_next_occurrence(notifications):
    # despite being different objects, events can
    # share the same UID, if they are recurring events, or have
    # more then 1 alarm defined.
    # if we have this case, we only want the next alarm
    event_alarms_dict = {}
    for alarm, event in notifications:
        _, existing = event_alarms_dict.get(alarm['uid'], (None, None))
        if existing:
            if event.time_left() < existing.time_left():
                event_alarms_dict[alarm['uid']] = alarm, event
        else:
            event_alarms_dict[alarm['uid']] = alarm, event
    return event_alarms_dict



def get_alarm_data(alarm, event):
    data = dict(
        summary=alarm['summary'],
        alarm_since=str(alarm['alarm_dt']),
        uid=str(alarm['uid']),
        time_left_to_event=str(event.time_left()),
        event_start=str(event.start))
    return data


def send_mqtt(config, data):
    mqtt_client = mqtt.Client(client_id='ical2mqtt for an event alarm')
    mqtt_client.enable_logger(logger=log)
    mqtt_client.connect(config.mqtt_broker)
    mqtt_client.publish(config.mqtt_topic, json.dumps(data))

def main(config):
    last_load = 0
    alarms_data = {}

    # create output file if it does not exist
    if not os.path.isfile(config.json_file):
        with open(config.json_file, 'w') as outfile:
            outfile.write('{"alarms":[]}')

    # read last state from output file
    with open(config.json_file, 'r') as json_file:
        json_data = json.loads(json_file.read())
        for alarm in json_data['alarms']:
            alarms_data[alarm['uid']] = alarm

    while True:
        if time.time() - last_load > 300:
            # reload calendars every ~5 minutes
            notifications = load_calendar_files(config.calendar_path)
            last_load = time.time()

        now = datetime.datetime.now().astimezone(tz=config.tz)
        seen_uids = []
        event_alarms_dict = filter_multiple_alarms_by_next_occurrence(notifications)

        for alarm, event in event_alarms_dict.values():
            log.debug('Found inactive alarm: %s at %s.', alarm['summary'], alarm['alarm_dt'])
            if (alarm['alarm_dt']-now).total_seconds() < 0:
                seen_uids.append(alarm['uid'])
                if alarm['uid'] in alarms_data:
                    log.debug('Active alarm "%s" was already handeled (%s).', alarm['summary'], alarm['uid'])
                    continue
                data = get_alarm_data(alarm, event)
                log.info('Handling alarm with uid %s for %s in %s.',
                            str(alarm['uid']),
                            str(alarm['summary']),
                            str(event.time_left()))
                send_mqtt(config, data)
                alarms_data[alarm['uid']] = data

        # remove no longer active alarms from data structure
        current_uids = []
        for uid in alarms_data.keys():
            current_uids.append(uid)
        delete_current = set(current_uids) - set(seen_uids)
        for del_uid in delete_current:
            log.info('Remove no longer active alarm "%s" from data. (%s)', alarms_data[del_uid]['summary'],  alarms_data[del_uid]['uid'])
            del alarms_data[del_uid]

        # re-format datastructure and write json file
        better_data = dict(alarms=list(alarms_data.values()))
        json_data = json.dumps(better_data)
        with open(config.json_file, 'w') as json_file:
            json_file.write(json_data)

        time.sleep(15)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert ics event alarms to mqtt messages and json data.')
    parser.add_argument('--calendar_path', dest='calendar_path', type=dir_path,
                        help='Location of your ics files (default: current working dir)',
                        default=os.getcwd())
    parser.add_argument('--json_file', dest='json_file', required=True,
                        help='Where to store the json file with all active events.')
    parser.add_argument('--mqtt_broker', dest='mqtt_broker', default='localhost',
                        help='Hostname of the mqtt server (default: localhost)')
    parser.add_argument('--mqtt_topic', dest='mqtt_topic', required=True,
                        help='Which mqtt topic to use.')
    parser.add_argument('--timezone', dest='timezone', help='The timezone you are in. Defaults to your system timezone.',
                        default=None)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', help='Sets log level to DEBUG. Default is ERROR.',
                        default=None)

    config = parser.parse_args()

    # create timezone from input if any
    config.tz = None
    if config.timezone is not None:
        config.tz = pytz.timezone(config.timezone)

    # setup logging with given value
    level = logging.ERROR
    if config.verbose:
        level = logging.DEBUG
    log = setup_logging(level)

    main(config)





