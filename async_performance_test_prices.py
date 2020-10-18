#!/usr/bin/env
import logging
import os
import sys
from datetime import datetime

import requests

import src.Reporting as Reporting
from src.Entities import Batch
from src.Entities import Price
from src.Methods import BulkUpdatePricesWithinOneDict, BulkUpdatePricesWithinListOfDicts

host = sys.argv[1]
token = sys.argv[2]
batch_size = int(sys.argv[3])
ids_file_name = sys.argv[4]

ids_file = open(ids_file_name, "r")
ids = ids_file.read().splitlines()
ids_file.close()

query_headers = {'Authorization': 'Bearer ' + token}

entities = [Price()]
methods = [BulkUpdatePricesWithinOneDict(ids), BulkUpdatePricesWithinListOfDicts(ids)]

elapsed_sum = {i: {batch_size: 0} for i in methods}
total_time = {i: {batch_size: 0} for i in methods}
success_updated_percentage = {i: {batch_size: 0} for i in methods}

if __name__ == '__main__':

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    try:
        if not os.path.exists('Results'):
            os.makedirs('Results')
        os.makedirs(Reporting.PATH_TO_SAVE_FOLDER)
        os.makedirs(Reporting.PATH_TO_SAVE_IMAGES)
        os.makedirs(Reporting.PATH_TO_SAVE_CSV)
    except OSError:
        logger.info("Fail on batch folder creation, results will be saved in current directory")
        PATH_TO_SAVE_FOLDER = ''
        PATH_TO_SAVE_IMAGES = ''
        PATH_TO_SAVE_CSV = ''

    handler = logging.FileHandler(Reporting.PATH_TO_SAVE_FOLDER + '/log.log')
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    for entity in entities:
        for method in methods:
            batch = Batch(batch_size, entity)
            method.send_batch(batch, host, query_headers, logger)
            method.wait_until_all_requests_processed(batch, host, query_headers, logger)
            elapsed_sum[method][batch_size] = batch.elapsed_sum
            endpoint = host + '/rest/V1/' + entity.search_endpoint_key + '?searchCriteria[pageSize]=' + str(
                batch_size) + '&searchCriteria[filterGroups][0][filters][0][field]=' + entity.search_by_field + \
                       '&searchCriteria[filterGroups][0][filters][0][value]=' + method.name + '_' + str(
                batch.start_timestamp) + '%25&searchCriteria[filterGroups][0][filters][0][condition_type]=like'
            response = requests.get(endpoint, headers=query_headers)
            updated_items = response.json()
            updated_items_count = int(updated_items['total_count'])
            success_updated_percentage[method][batch_size] = updated_items_count * 100 / batch_size
            if updated_items_count > 0:
                max_timestamp = max([datetime.timestamp(
                    datetime.strptime(updated_items['items'][k]['updated_at'], '%Y-%m-%d %H:%M:%S'))
                    for k in range(0, updated_items_count)])
                total_time[method][batch_size] = int(max_timestamp - batch.start_timestamp)
            else:
                logger.info(
                    'Entity: ' + entity.name + ' RunID: ' + str(
                        batch.start_timestamp) + ' Method: ' + method.name + ' Batch size: ' + str(
                        batch_size) + ' There\'s no item was created.')
            del batch

        Reporting.create_csv(Reporting.PATH_TO_SAVE_CSV, entity.name + ' summary_response_time', methods, [batch_size],
                             elapsed_sum)
        Reporting.create_png(Reporting.PATH_TO_SAVE_IMAGES, entity.name + ' Summary response time, s', methods, elapsed_sum)

        Reporting.create_csv(Reporting.PATH_TO_SAVE_CSV, entity.name + ' total_time', methods, [batch_size], total_time)
        Reporting.create_png(Reporting.PATH_TO_SAVE_IMAGES, entity.name + ' Total time, s', methods, total_time)

        Reporting.create_csv(Reporting.PATH_TO_SAVE_CSV, entity.name + ' total_success_percentage', methods, [batch_size],
                             success_updated_percentage)
        Reporting.create_png(Reporting.PATH_TO_SAVE_IMAGES, entity.name + ' Succeed created items, %', methods,
                             success_updated_percentage)