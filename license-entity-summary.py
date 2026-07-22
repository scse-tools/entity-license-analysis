#!/usr/bin/env python3

__version__ = '20260620.000'

# import inspect

'''
    version history
        20260620.000    initial build

'''

__usage__ = '''
consume daily entity usage, summarize usage per day for unlimited number of days
'''

import argparse
import yaml
import traceback
import json
import csv
from datetime import date, timedelta, datetime
import STELLAR_UTIL
from LOGGER_UTIL import logger_util

parser = argparse.ArgumentParser(usage=__usage__)
parser.add_argument("-c", "--config", help='use yaml config (default: config.yaml)', dest='yaml_config',
                    default='config.yaml')
parser.add_argument('-l', '--log-file', help='Write stdout to logfile', dest='logfile', default='')
parser.add_argument('-d', '--debug', help='Turn on debug/verbose logging', dest='verbose', action='store_true')
parser.add_argument('-t', '--tenant-id', help='required tenant id', dest='tenant_id', required=True)

args = parser.parse_args()
l = logger_util(args)


def analyze_tenant_entities(entity_list, e_date, e_month):
    # l.debug('analyzing entities and generating stats')
    t_ip_count = len([e for e in entity_list if e.get('type') == 'device'])
    t_user_count = len([e for e in entity_list if e.get('type') == 'user'])
    entity_stats = {'month': e_month, 'date': e_date, 'ip_entity_count': t_ip_count, 'user_entity_count': t_user_count, 'total_entity_count': t_ip_count + t_user_count}
    return entity_stats


def write_to_csv(entity_stats, csv_filename):
    l.info(f"Writing entity summary to: [{csv_filename}]")
    if entity_stats:
        with open(csv_filename, "w", newline="", encoding="utf-8") as output_file:
            headers = entity_stats[0].keys()
            writer = csv.DictWriter(output_file, fieldnames=headers)
            writer.writeheader()
            writer.writerows(entity_stats)


if __name__ == "__main__":

    try:
        with open(args.yaml_config, 'r') as config_file:
            config = yaml.safe_load(config_file)
        l.configure(config)
        SU = STELLAR_UTIL.STELLAR_UTIL(logger=l, config=config)
        CSV_FILENAME = config.get('csv_filename', 'summary.csv')

        DAYS_BACK = config.get('days_back_to_query', 1)
        day_count = 0
        e_stats = []

        l.info(f"Getting entity counts for the past {DAYS_BACK} day(s) for tenent: [{args.tenant_id}]")
        while day_count < DAYS_BACK:
            day_count += 1
            record_date = (date.today() - timedelta(days=day_count)).strftime("%Y-%m-%d")
            record_month = (date.today() - timedelta(days=day_count)).strftime("%Y-%m")
            l.info(f"Getting entity usage for date: ({day_count}/{DAYS_BACK}) [{record_date}]")
            tenant_entities = SU.get_license_entities(date=record_date, days_back=1, daily_count=False, tenant_id=args.tenant_id)
            e_stats.append(analyze_tenant_entities(tenant_entities, record_date, record_month))

        # print(json.dumps(e_stats, indent=4))
        write_to_csv(e_stats, csv_filename=CSV_FILENAME)
        l.info(f"Wrote records: [{len(e_stats)}]")
        l.info('Done')

    except Exception as e:
        l.critical("Fatal Error - {}".format(traceback.format_exc()))
        exit(1)
