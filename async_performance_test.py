#!/usr/bin/env
import logging
import os
import sys
from datetime import datetime

import requests

import src.Reporting as Reporting
from src.Entities import Batch
from src.Entities import SimpleProduct, ConfigurableProduct, Customer
from src.Methods import Sync, Async, Bulk

host = sys.argv[1]
token = sys.argv[2]
max_batch_size = int(sys.argv[3])

query_headers = {'Authorization': 'Bearer ' + token}
batch_sizes_list = [1] + [i for i in range(10, max_batch_size + 1, 10)]

entities = [SimpleProduct()]
methods = [Sync()]

elapsed_sum = {i: {j: 0 for j in batch_sizes_list} for i in methods}
total_time = {i: {j: 0 for j in batch_sizes_list} for i in methods}
success_created_percentage = {i: {j: 0 for j in batch_sizes_list} for i in methods}

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
        for batch_size in batch_sizes_list:
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
                created_items = response.json()
                created_items_count = int(created_items['total_count'])
                success_created_percentage[method][batch_size] = created_items_count * 100 / batch_size
                if created_items_count > 0:
                    max_timestamp = max([datetime.timestamp(
                        datetime.strptime(created_items['items'][k]['created_at'], '%Y-%m-%d %H:%M:%S'))
                        for k in range(0, created_items_count)])
                    total_time[method][batch_size] = int(max_timestamp - batch.start_timestamp)
                else:
                    logger.info(
                        'Entity: ' + entity.name + ' RunID: ' + str(
                            batch.start_timestamp) + ' Method: ' + method.name + ' Batch size: ' + str(
                            batch_size) + ' There\'s no item was created.')
                del batch

        Reporting.create_csv(Reporting.PATH_TO_SAVE_CSV, entity.name + ' summary_response_time', methods, batch_sizes_list,
                             elapsed_sum)
        Reporting.create_png(Reporting.PATH_TO_SAVE_IMAGES, entity.name + ' Summary response time, s', methods, elapsed_sum)

        Reporting.create_csv(Reporting.PATH_TO_SAVE_CSV, entity.name + ' total_time', methods, batch_sizes_list, total_time)
        Reporting.create_png(Reporting.PATH_TO_SAVE_IMAGES, entity.name + ' Total time, s', methods, total_time)

        Reporting.create_csv(Reporting.PATH_TO_SAVE_CSV, entity.name + ' total_success_percentage', methods, batch_sizes_list,
                             success_created_percentage)
        Reporting.create_png(Reporting.PATH_TO_SAVE_IMAGES, entity.name + ' Succeed created items, %', methods,
                             success_created_percentage)
