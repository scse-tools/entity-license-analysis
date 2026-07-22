#!/usr/bin/env python3

__version__ = '20260722.000'

import inspect

'''
    version history
        20260528.000    initial build
        20260722.000    added option for CSV output (-o)

'''

__usage__ = '''
consume daily entity usage and break out entities by type (IP vs. User).
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
parser.add_argument('-o', '--csv-outfile', help='write out to CSV file instead of webhook', dest='write_to_csv', action='store_true')


args = parser.parse_args()
l = logger_util(args)


def generate_chunks(entity_list, chunk_size):
    l.debug('chunking batches')
    chunked_list = [entity_list[i: i + chunk_size] for i in range(0, len(entity_list), chunk_size)]
    return chunked_list


def analyze_tenant_entities(entity_list, daily_volumes, e_date):
    l.debug('analyzing entities and generating stats')
    entity_stats = {}
    distinct_tenants = {item['tenant_name'] for item in entity_list}
    running_total_ip = running_total_user = 0
    for tenant_name in distinct_tenants:
        t_ip_count = len([e for e in entity_list if e.get('tenant_name') == tenant_name and e.get('type') == 'device'])
        t_user_count = len([e for e in entity_list if e.get('tenant_name') == tenant_name and e.get('type') == 'user'])
        entity_stats[tenant_name] = {'ip_entity_count': t_ip_count, 'user_entity_count': t_user_count, 'total_entity_count': t_ip_count + t_user_count}
        running_total_ip += t_ip_count
        running_total_user += t_user_count
    entity_stats['All Tenants'] = {'ip_entity_count': running_total_ip, 'user_entity_count': running_total_user, 'total_entity_count': running_total_ip + running_total_user}

    # stitch in daily volumes
    daily_volume = [e for e in daily_volumes if e.get('time')[:10] == e_date]
    if daily_volume:
        usages = daily_volume[0].get('usages', [])
        for usage in usages:
            tenant_name = usage.get('tenant_name', '')
            t_vol_usage = usage.get('usage', 0)
            t_vol_percent = usage.get('percentage', 0)
            if tenant_name not in entity_stats:
                entity_stats[tenant_name] = {'ip_entity_count': 0, 'user_entity_count': 0, 'total_entity_count': 0}
            entity_stats[tenant_name] |= {'volume_usage': round(t_vol_usage, 3), 'volume_percent': t_vol_percent}
            ip_entity_count = entity_stats[tenant_name].get('ip_entity_count', 0)
            user_entity_count = entity_stats[tenant_name].get('user_entity_count', 0)
            total_entity_count = entity_stats[tenant_name].get('total_entity_count', 0)
            if t_vol_usage and total_entity_count:
                vol_per_entity = t_vol_usage / total_entity_count
                ip_entity_volume = vol_per_entity * ip_entity_count
                user_entity_volume = vol_per_entity * user_entity_count
                vol_per_entity = vol_per_entity * 1000
            else:
                vol_per_entity = ip_entity_volume = user_entity_volume = 0

            entity_stats[tenant_name] |= {'volume_per_entity': round(vol_per_entity, 3),
                                            'ip_entity_volume': round(ip_entity_volume, 3),
                                            'user_entity_volume': round(user_entity_volume, 3)}

    return entity_stats


def flatten_entity_stats(entity_stats):
    l.debug('flattening stats')
    flattened_stats = []
    # ensure unique timestamps using an incrementor
    # perhaps this might fix the doublenesting?
    ts_unique = 0
    for el_date in entity_stats:
        ts_unique += 1
        el_timestamp = (int(datetime.strptime(el_date, "%Y-%m-%d").timestamp()) * 1000) + ts_unique
        for tenant in entity_stats[el_date]:
            r = entity_stats[el_date][tenant]
            r['tenant_name'] = tenant
            r['date'] = el_date
            r['timestamp'] = el_timestamp
            r['tag'] = RECORD_TAG
            flattened_stats.append(r)
    return flattened_stats


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
        CSV_FILENAME = config.get('csv_filename', 'entity_analysis.csv')

        DAYS_BACK = config.get('days_back_to_query', 1)
        CHUNK_SIZE = config.get('batch_record_size', 100)
        RECORD_TAG = config.get('record_tag', '')
        day_count = 0
        e_stats = {}

        l.info("Getting volume usage")
        daily_volumes = SU.get_storage_usages()

        l.info(f"Getting entity counts for the past {DAYS_BACK} day(s)")
        while day_count < DAYS_BACK:
            day_count += 1
            start_date = (date.today() - timedelta(days=day_count)).strftime("%Y-%m-%d")
            l.info(f"Getting entity usage for date: [{start_date}] ({day_count}/{DAYS_BACK})")
            tenant_entities = SU.get_license_entities(date=start_date, days_back=1, daily_count=False)
            e_stats[start_date] = analyze_tenant_entities(tenant_entities, daily_volumes, start_date)

        # prepare records (flatten so that stellar can display)
        flattened_stats = flatten_entity_stats(e_stats)
        l.info(f"Generated records: [{len(flattened_stats)}]")
        # print(json.dumps(flattened_stats, indent=4))

        if args.write_to_csv:
            l.info(f"Writing output to CSV file: [{CSV_FILENAME}]")
            total_rec_cnt = len(flattened_stats)
            write_to_csv(flattened_stats, CSV_FILENAME)

        else:
            # chunk into batches and send
            chunked_stats = generate_chunks(flattened_stats, chunk_size=CHUNK_SIZE)
            chunk_count = 0
            total_rec_cnt = 0
            for chunk in chunked_stats:
                chunk_count += 1
                rec_cnt = len(chunk)
                total_rec_cnt += rec_cnt
                l.info(f'Sending records: [{rec_cnt}] | chunk: [{chunk_count} of {len(chunked_stats)}]')
                l.send_to_webhook_async(chunk)

        l.info(f"Wrote records: [{total_rec_cnt}] with tag: [{RECORD_TAG}]")
        l.info('Done')

    except Exception as e:
        l.critical("Fatal Error - {}".format(traceback.format_exc()))
        exit(1)
