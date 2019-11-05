import csv
import logging
import os
import sys
import time
from datetime import datetime

import matplotlib.pyplot as plt
import requests

host = sys.argv[1]
token = sys.argv[2]
max_size = int(sys.argv[3])

query_headers = {'Authorization': 'Bearer ' + token}
batch_size_per_run = [1] + [i for i in range(10, max_size + 1, 10)]

methods = ['sync', 'async', 'bulk']
colors = ['r', 'b', 'g']

elapsed_sum_per_method_per_run = {i: {} for i in methods}
start_timestamps = {i: {} for i in methods}
total_time = {i: {} for i in methods}
success_created_percentage = {i: {} for i in methods}

TIMEOUT_S = 10

PATH_TO_SAVE_FOLDER = 'Results/' + datetime.strftime(datetime.now(), '%d-%m-%Y %H-%M')
PATH_TO_SAVE_IMAGES = PATH_TO_SAVE_FOLDER + "/images/"
PATH_TO_SAVE_CSV = PATH_TO_SAVE_FOLDER + "/csvs/"

WARNING_PRODUCTS_IN_PROGRESS = 'Some products are still in progress'
TIMEOUT_MESSAGE_ON_PRODUCT_CREATION = 'Timeout on waiting for items creation'


def timestamp_s():
    return int(datetime.timestamp(datetime.utcnow()))


def create_item_request_body(item_id):
    return {
        "product": {
            "sku": item_id,
            "name": item_id,
            "attribute_set_id": 4,
            "price": "100",
            "status": 1,
            "visibility": 4,
            "type_id": "simple",
            "extension_attributes": {
                "stock_item": {
                    "manage_stock": 1,
                    "is_in_stock": 1,
                    "qty": "10"
                }
            }
        }
    }


def get_end_time_per_run_request_body():
    return """
    query ($search_criteria: String!, $pageSize: Int)
    {
      products(
        filter: { sku: { like: $search_criteria } }
        pageSize: $pageSize
        currentPage: 1
        sort: { name: DESC }
      ) {
        items {
          created_at
          sku
        }
      }
    }
    """


def get_end_time_per_batch_request(host, query, variables):
    endpoint = host + '/graphql'
    request = requests.get(endpoint, json={'query': query, 'variables': variables})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))


if __name__ == '__main__':

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    try:
        if not os.path.exists('Results'):
            os.makedirs('Results')
        os.makedirs(PATH_TO_SAVE_FOLDER)
        os.makedirs(PATH_TO_SAVE_IMAGES)
        os.makedirs(PATH_TO_SAVE_CSV)
    except OSError:
        logger.info("Fail on run folder creation, results will be saved in current directory")
        PATH_TO_SAVE_FOLDER = ''
        PATH_TO_SAVE_IMAGES = ''
        PATH_TO_SAVE_CSV = ''

    handler = logging.FileHandler(PATH_TO_SAVE_FOLDER + '/log.log')
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    for j in batch_size_per_run:
        for method in methods:
            elapsed_current_run = []
            if method == 'sync':
                start_time = timestamp_s()
                for i in range(1, j + 1):
                    item_id = method + "_" + str(start_time) + "_" + str(i)
                    request = create_item_request_body(item_id)
                    response = requests.post(host + '/rest/V1/products', headers=query_headers, json=request)
                    elapsed_current_run.append(response.elapsed.total_seconds())
            elif method == 'async':
                bulk_uuids_current_run = []
                start_time = timestamp_s()
                for i in range(1, j + 1):
                    item_id = method + "_" + str(start_time) + "_" + str(i)
                    request = create_item_request_body(item_id)
                    response = requests.post(host + '/rest/async/V1/products', headers=query_headers, json=request)
                    elapsed_current_run.append(response.elapsed.total_seconds())
                    bulk_uuids_current_run.append(response.json()['bulk_uuid'])
                some_uuid_open = True
                time_to_timeout = time.time() + TIMEOUT_S
                while some_uuid_open:
                    if time.time() > time_to_timeout:
                        logger.info(
                            'Method: ' + method + ' Batch size: ' + str(j) + TIMEOUT_MESSAGE_ON_PRODUCT_CREATION)
                        break
                    some_uuid_open = False
                    for uuid in bulk_uuids_current_run:
                        bulk_inprogress_count = requests.get(host + '/rest/V1/bulk/' + uuid + '/operation-status/4',
                                                             headers=query_headers)
                        if bulk_inprogress_count.json() != 0:
                            logger.info('Method: ' + method + ' Batch size: ' + str(j) + WARNING_PRODUCTS_IN_PROGRESS)
                            some_uuid_open = True
                            time.sleep(1)
                            break
            elif method == 'bulk':
                request = []
                start_time = timestamp_s()
                for i in range(1, j + 1):
                    item_id = method + "_" + str(start_time) + "_" + str(i)
                    request.append(create_item_request_body(item_id))
                response = requests.post(host + '/rest/async/bulk/V1/products', headers=query_headers, json=request)
                bulk_uuid = response.json()['bulk_uuid']
                elapsed_current_run.append(response.elapsed.total_seconds())
                some_uuid_open = True
                time_to_timeout = time.time() + TIMEOUT_S
                while some_uuid_open:
                    if time.time() > time_to_timeout:
                        logger.info(
                            'Method: ' + method + ' Batch size: ' + str(j) + TIMEOUT_MESSAGE_ON_PRODUCT_CREATION)
                        break
                    bulk_inprogress_count = requests.get(host + '/rest/V1/bulk/' + bulk_uuid + '/operation-status/4',
                                                         headers=query_headers)
                    if bulk_inprogress_count.json() != 0:
                        logger.info('Method: ' + method + ' Batch size: ' + str(j) + WARNING_PRODUCTS_IN_PROGRESS)
                        some_uuid_open = True
                        time.sleep(1)
                        continue
                    else:
                        some_uuid_open = False
            else:
                logger.info('Method: ' + method + ' is unexpected method')
                continue
            elapsed_sum_per_method_per_run[method][j] = sum(elapsed_current_run)
            start_timestamps[method][j] = start_time
            logger.info('Method: ' + method + ' Batch size: ' + str(j) + ' Successfully sent')

    with open(PATH_TO_SAVE_CSV + 'result_request_time.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + methods)
        for i in batch_size_per_run:
            w.writerow([i] + [elapsed_sum_per_method_per_run[j].get(i, 'NaN') for j in methods])

    plt.figure(1, figsize=(12, 7))
    plt.title('Sum response time for every batch')
    for method_to_show in methods:
        plt.plot(elapsed_sum_per_method_per_run[method_to_show].keys(),
                 [elapsed_sum_per_method_per_run[method_to_show][j]
                  for j in elapsed_sum_per_method_per_run[method_to_show].keys()],
                 label=method_to_show, color=colors[methods.index(method_to_show)])
    plt.ylabel('Sum time for batch, s')
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(PATH_TO_SAVE_IMAGES + 'Sum response time for every batch.png')

    # for method in start_timestamps.keys():
    #     for batch_size in start_timestamps[method].keys():
    #         start_timestamp = start_timestamps[method][batch_size]
    #         search_criteria = method + "_" + str(start_timestamp) + "_%"
    #         query_variables = {
    #             'search_criteria': search_criteria,
    #             'pageSize': batch_size
    #         }
    #         query = get_end_time_per_run_request_body()
    #         created_orders_per_run = get_end_time_per_batch_request(host, query, query_variables)
    #         created_items_count = len(created_orders_per_run['data']['products']['items'])
    #         success_created_percentage[method][batch_size] = created_items_count * 100 / batch_size
    #         if created_items_count > 0:
    #             max_timestamp_per_run = max([datetime.timestamp(
    #                 datetime.strptime(created_orders_per_run['data']['products']['items'][k]['created_at'], '%Y-%m-%d %H:%M:%S'))
    #                 for k in range(0, created_items_count)])
    #             total_time[method][batch_size] = max_timestamp_per_run - start_timestamp
    #         else:
    #             logger.info('Method: ' + method + ' Batch size: ' + str(batch_size) + ': ' 'There\'s no item was created')
    #             total_time[method][batch_size] = 0

    for method in start_timestamps.keys():
        for batch_size in start_timestamps[method].keys():
            start_timestamp = start_timestamps[method][batch_size]
            endpoint = host + '/rest/V1/products?searchCriteria[pageSize]=' + str(batch_size) + \
                       '&searchCriteria[filterGroups][0][filters][0][field]=sku&searchCriteria[filterGroups][0][filters][0][value]=' + \
                       method + '_' + str(
                start_timestamp) + '%25&searchCriteria[filterGroups][0][filters][0][condition_type]=like'
            request = requests.get(endpoint, headers=query_headers)
            created_orders_per_run = request.json()
            created_items_count = int(created_orders_per_run['total_count'])
            success_created_percentage[method][batch_size] = created_items_count * 100 / batch_size
            if created_items_count > 0:
                max_timestamp_per_run = max([datetime.timestamp(
                    datetime.strptime(created_orders_per_run['items'][k]['created_at'], '%Y-%m-%d %H:%M:%S'))
                    for k in range(0, created_items_count)])
                total_time[method][batch_size] = int(max_timestamp_per_run - start_timestamp)
            else:
                logger.info(
                    'Method: ' + method + ' Batch size: ' + str(batch_size) + ': ' 'There\'s no item was created. ' + 'Start timestamp: ' + str(start_timestamp))
                total_time[method][batch_size] = 0

    with open(PATH_TO_SAVE_CSV + 'total_time.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + methods)
        for i in batch_size_per_run:
            w.writerow([i] + [total_time[j].get(i, 'NaN') for j in methods])

    plt.figure(2, figsize=(12, 7))
    plt.title('Total time')
    for method_to_show in methods:
        plt.plot(total_time[method_to_show].keys(),
                 [total_time[method_to_show][j] for j in total_time[method_to_show].keys()],
                 label=method_to_show, color=colors[methods.index(method_to_show)])
    plt.ylabel('Total time for batch, s')
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(PATH_TO_SAVE_IMAGES + 'Total time.png')

    with open(PATH_TO_SAVE_CSV + 'total_success_percentage.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + methods)
        for i in batch_size_per_run:
            w.writerow([i] + [success_created_percentage[j].get(i, 'NaN') for j in methods])

    plt.figure(3, figsize=(12, 7))
    plt.title('Total success created percentage')
    for method_to_show in methods:
        plt.plot(success_created_percentage[method_to_show].keys(),
                 [success_created_percentage[method_to_show][j] for j in
                  success_created_percentage[method_to_show].keys()],
                 label=method_to_show, color=colors[methods.index(method_to_show)])
    plt.ylabel('Total success created items, %')
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(PATH_TO_SAVE_IMAGES + 'Total success created percentage.png')