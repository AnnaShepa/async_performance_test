import csv
import datetime
import logging
import os
import sys
import time

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

TIMEOUT_S = 300

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
            bulk_uuids_current_run = []
            if method == 'sync':
                request = []
                start_time = timestamp_s()
                logger.info(
                    'RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(j) + ' Sending started')
                # Sync requsts sending one by one
                for i in range(1, j + 1):
                    item_id = method + "_" + str(start_time) + "_" + str(i)
                    request = create_item_request_body(item_id)
                    response = requests.post(host + '/rest/V1/products', headers=query_headers, json=request)
                    elapsed_current_run.append(response.elapsed.total_seconds())
                    logger.info('RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(
                        j) + ' ItemID: ' + str(i) + ' Is sent')
            elif method == 'async':
                request = []
                start_time = timestamp_s()
                logger.info(
                    'RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(j) + ' Sending started')
                # Async requsts sending one by one
                for i in range(1, j + 1):
                    item_id = method + "_" + str(start_time) + "_" + str(i)
                    request = create_item_request_body(item_id)
                    response = requests.post(host + '/rest/async/V1/products', headers=query_headers, json=request)
                    elapsed_current_run.append(response.elapsed.total_seconds())
                    bulk_uuids_current_run.append(response.json()['bulk_uuid'])
                    logger.info('RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(
                        j) + ' ItemID: ' + str(i) + ' Is sent')
            elif method == 'bulk':
                request = []
                start_time = timestamp_s()
                logger.info(
                    'RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(j) + ' Sending started')
                # Request body for bulk creating
                for i in range(1, j + 1):
                    item_id = method + "_" + str(start_time) + "_" + str(i)
                    request.append(create_item_request_body(item_id))
                # Bulk request sending
                response = requests.post(host + '/rest/async/bulk/V1/products', headers=query_headers, json=request)
                bulk_uuids_current_run.append(response.json()['bulk_uuid'])
                elapsed_current_run.append(response.elapsed.total_seconds())
                logger.info('RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(j) + ' Is sent')
            else:
                logger.info('Method: ' + method + ' is unexpected method')
                continue

            # Controll that async/bulk requests have been processed before new batch start
            some_uuid_open = True
            time_to_timeout = time.time() + TIMEOUT_S
            while some_uuid_open:
                if time.time() > time_to_timeout:
                    logger.info(
                        'RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(
                            j) + ' ' + TIMEOUT_MESSAGE_ON_PRODUCT_CREATION)
                    break
                some_uuid_open = False
                for uuid in bulk_uuids_current_run:
                    curent_butch_progress = requests.get(host + '/rest/V1/bulk/' + uuid + '/status',
                                                         headers=query_headers)
                    # Check that no of sent requests have status code 4 (Open)
                    if 4 in [curent_butch_progress.json()["operations_list"][k]["status"] for k in
                             [0, len(curent_butch_progress.json()["operations_list"]) - 1]]:
                        logger.info('RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(
                            j) + ' ' + WARNING_PRODUCTS_IN_PROGRESS)
                        some_uuid_open = True
                        time.sleep(3)
                        break
                    else:
                        # In case some request already done (not 4) it shouldn't be checked next time
                        bulk_uuids_current_run.remove(uuid)
            # Elapsed time for whole batch calculation
            elapsed_sum_per_method_per_run[method][j] = sum(elapsed_current_run)
            # Save start timestamp as id of run
            start_timestamps[method][j] = start_time
            logger.info(
                'RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(j) + ' Sending finished')

    # Create csv file with elapsed time
    with open(PATH_TO_SAVE_CSV + 'summary_response_time.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + methods)
        for i in batch_size_per_run:
            w.writerow([i] + [elapsed_sum_per_method_per_run[j].get(i, 'NaN') for j in methods])

    # Create graph with elapsed time
    plt.figure(1, figsize=(12, 7))
    plt.title('Summary response time for every batch')
    for method_to_show in methods:
        plt.plot(elapsed_sum_per_method_per_run[method_to_show].keys(),
                 [elapsed_sum_per_method_per_run[method_to_show][j]
                  for j in elapsed_sum_per_method_per_run[method_to_show].keys()],
                 label=method_to_show, color=colors[methods.index(method_to_show)])
    plt.ylabel('Summary response time for batch, s')
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(PATH_TO_SAVE_IMAGES + 'Summary response time.png')

    # Total time calculation
    for method in start_timestamps.keys():
        for batch_size in start_timestamps[method].keys():  # For every batch
            start_timestamp = start_timestamps[method][batch_size]  # Extract start time
            endpoint = host + '/rest/V1/products?searchCriteria[pageSize]=' + str(batch_size) + \
                       '&searchCriteria[filterGroups][0][filters][0][field]=sku&searchCriteria[filterGroups][0][filters][0][value]=' + \
                       method + '_' + str(
                start_timestamp) + '%25&searchCriteria[filterGroups][0][filters][0][condition_type]=like'
            # Request created products by run id
            request = requests.get(endpoint, headers=query_headers)
            created_items_per_batch = request.json()
            created_items_count = int(created_items_per_batch['total_count'])
            success_created_percentage[method][batch_size] = created_items_count * 100 / batch_size
            # If some items were created save max time and calculate total time, else save 0 as total time
            if created_items_count > 0:
                max_timestamp_per_run = max([datetime.timestamp(
                    datetime.strptime(created_items_per_batch['items'][k]['created_at'], '%Y-%m-%d %H:%M:%S'))
                    for k in range(0, created_items_count)])
                total_time[method][batch_size] = int(max_timestamp_per_run - start_timestamp)
            else:
                logger.info(
                    'RunID: ' + str(start_time) + ' Method: ' + method + ' Batch size: ' + str(
                        batch_size) + ' There\'s no item was created. ')
                total_time[method][batch_size] = 0

    # Create csv file with total time
    with open(PATH_TO_SAVE_CSV + 'total_time.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + methods)
        for i in batch_size_per_run:
            w.writerow([i] + [total_time[j].get(i, 'NaN') for j in methods])

    # Create graph with total time
    plt.figure(2, figsize=(12, 7))
    plt.title('Total time')
    for method_to_show in methods:
        plt.plot(total_time[method_to_show].keys(),
                 [total_time[method_to_show][j] for j in total_time[method_to_show].keys()],
                 label=method_to_show, color=colors[methods.index(method_to_show)])
    plt.ylabel('Total time for batch creation, s')
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(PATH_TO_SAVE_IMAGES + 'Total time.png')

    # Create csv file with success percentage
    with open(PATH_TO_SAVE_CSV + 'total_success_percentage.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + methods)
        for i in batch_size_per_run:
            w.writerow([i] + [success_created_percentage[j].get(i, 'NaN') for j in methods])

    # Create graph with success percentage
    plt.figure(3, figsize=(12, 7))
    plt.title('Total success created items percentage')
    for method_to_show in methods:
        plt.plot(success_created_percentage[method_to_show].keys(),
                 [success_created_percentage[method_to_show][j] for j in
                  success_created_percentage[method_to_show].keys()],
                 label=method_to_show, color=colors[methods.index(method_to_show)])
    plt.ylabel('Total success created items, %')
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(PATH_TO_SAVE_IMAGES + 'Total success created items percentage.png')
