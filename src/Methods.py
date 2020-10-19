import time
from abc import ABC, abstractmethod

import requests

import src.Reporting as Reporting
from src.Reporting import log_record

TIMEOUT_S = 300


class Method(ABC):
    name: str

    @abstractmethod
    def send_batch(self, batch, host, query_headers, logger):
        pass

    def wait_until_all_requests_processed(self, batch, host, query_headers, logger):
        # Controll that async/bulk requests have been processed before new batch start
        some_uuid_open = True
        time_to_timeout = time.time() + TIMEOUT_S
        while some_uuid_open:
            if time.time() > time_to_timeout:
                log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                           Reporting.TIMEOUT_MESSAGE_ON_PRODUCT_CREATION)
                break
            some_uuid_open = False
            for uuid in batch.bulk_uuids:
                curent_butch_progress = requests.get(host + '/rest/V1/bulk/' + uuid + '/status',
                                                     headers=query_headers)
                # Check that no of sent requests have status code 4 (Open)
                if 4 in [k["status"] for k in curent_butch_progress.json()["operations_list"]]:
                    log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                               Reporting.WARNING_PRODUCTS_IN_PROGRESS)
                    some_uuid_open = True
                    time.sleep(10)
                    break
                else:
                    # In case some request already done (not 4) it shouldn't be checked next time
                    batch.bulk_uuids.remove(uuid)
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_FINISHED)


class Sync(Method):
    name = 'Sync'

    def send_batch(self, batch, host, query_headers, logger):
        ids = []
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_STARTED)
        for i in range(1, batch.size + 1):
            item_id = self.name + "_" + str(batch.start_timestamp) + "_" + str(i)
            ids.append(item_id)
            request = batch.entity.create_request_body(item_id)
            response = requests.post(host + '/rest/V1/' + batch.entity.create_endpoint_key,
                                     headers=query_headers, json=request)
            log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                       ' ItemID: ' + str(i) + ' ' + Reporting.MESSAGE_ITEM_SENT)
            batch.elapsed_sum += response.elapsed.total_seconds()
        Reporting.save_ids_list(Reporting.PATH_TO_SAVE_FOLDER + "/", batch.entity.name, self.name, batch.size, ids)

    def wait_until_all_requests_processed(self, batch, host, query_headers, logger):
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_FINISHED)


class Async(Method):
    name = 'Async'

    def send_batch(self, batch, host, query_headers, logger):
        ids = []
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_STARTED)
        for i in range(1, batch.size + 1):
            item_id = self.name + "_" + str(batch.start_timestamp) + "_" + str(i)
            ids.append(item_id)
            request = batch.entity.create_request_body(item_id)
            response = requests.post(host + '/rest/async/V1/' + batch.entity.create_endpoint_key,
                                     headers=query_headers, json=request)
            log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                       ' ItemID: ' + str(i) + ' ' + Reporting.MESSAGE_ITEM_SENT)
            batch.elapsed_sum += response.elapsed.total_seconds()
            batch.bulk_uuids.append(response.json()['bulk_uuid'])
        Reporting.save_ids_list(Reporting.PATH_TO_SAVE_FOLDER + "/", batch.entity.name, self.name, batch.size, ids)


class Bulk(Method):
    name = 'Bulk'

    def send_batch(self, batch, host, query_headers, logger):
        ids = []
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_STARTED)
        request = []
        for i in range(1, batch.size + 1):
            item_id = self.name + "_" + str(batch.start_timestamp) + "_" + str(i)
            ids.append(item_id)
            request.append(batch.entity.create_request_body(item_id))
        response = requests.post(host + '/rest/async/bulk/V1/' + batch.entity.create_endpoint_key,
                                 headers=query_headers,
                                 json=request)
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size, Reporting.MESSAGE_ITEM_SENT)
        batch.bulk_uuids.append(response.json()['bulk_uuid'])
        batch.elapsed_sum = response.elapsed.total_seconds()
        Reporting.save_ids_list(Reporting.PATH_TO_SAVE_FOLDER + "/", batch.entity.name, self.name, batch.size, ids)


class BulkUpdatePricesWithinOneDict(Method):
    name = 'Bulk update prices within one dict'
    run_id = None
    batch_size = 0

    def __init__(self, run_id, batch_size):
        self.run_id = run_id
        self.batch_size = batch_size

    def send_batch(self, batch, host, query_headers, logger):
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_STARTED)
        request = [{"prices": []}]
        item_ids = [str(self.run_id) + "_" + str(i) for i in range(1, self.batch_size + 1)]
        for item_id in item_ids:
            request[0]["prices"].append(batch.entity.create_request_body(item_id)["prices"][0])
        response = requests.post(host + '/rest/async/bulk/V1/' + batch.entity.create_endpoint_key,
                                 headers=query_headers,
                                 json=request)
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size, Reporting.MESSAGE_ITEM_SENT)
        batch.bulk_uuids.append(response.json()['bulk_uuid'])
        batch.elapsed_sum = response.elapsed.total_seconds()


class BulkUpdatePricesWithinListOfDicts(Method):
    name = 'Bulk update prices within list of dicts'
    run_id = None
    batch_size = 0

    def __init__(self, run_id, batch_size):
        self.run_id = run_id
        self.batch_size = batch_size

    def send_batch(self, batch, host, query_headers, logger):
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size,
                   Reporting.MESSAGE_SENDING_STARTED)
        request = []
        item_ids = [str(self.run_id) + "_" + str(i) for i in range(1, self.batch_size + 1)]
        for item_id in item_ids:
            request.append(batch.entity.create_request_body(item_id))
        response = requests.post(host + '/rest/async/bulk/V1/' + batch.entity.create_endpoint_key,
                                 headers=query_headers,
                                 json=request)
        log_record(logger, batch.entity.name, batch.start_timestamp, self.name, batch.size, Reporting.MESSAGE_ITEM_SENT)
        batch.bulk_uuids.append(response.json()['bulk_uuid'])
        batch.elapsed_sum = response.elapsed.total_seconds()
