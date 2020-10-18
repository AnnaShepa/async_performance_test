import csv
from datetime import datetime

import matplotlib.pyplot as plt

PATH_TO_SAVE_FOLDER = 'Results/' + datetime.strftime(datetime.now(), '%d-%m-%Y %H-%M')
PATH_TO_SAVE_IMAGES = PATH_TO_SAVE_FOLDER + "/images/"
PATH_TO_SAVE_CSV = PATH_TO_SAVE_FOLDER + "/csvs/"

WARNING_PRODUCTS_IN_PROGRESS = 'Some items are still in progress'
TIMEOUT_MESSAGE_ON_PRODUCT_CREATION = 'Timeout on waiting for items creation'
MESSAGE_SENDING_STARTED = 'Sending started'
MESSAGE_SENDING_FINISHED = 'Sending finished'
MESSAGE_ITEM_SENT = 'Item sent'


def create_csv(path_to_save, name, methods, column_headers, values):
    with open(path_to_save + name + '.csv', 'w') as f:
        w = csv.writer(f)
        w.writerow(['Batch size'] + [method.name for method in methods])
        for i in column_headers:
            w.writerow([i] + [values[j].get(i, 'NaN') for j in methods])


def create_png(path_to_save, name, methods, values):
    plt.figure(figsize=(12, 7))
    plt.title(name)
    for method_to_show in methods:
        xline = list(values[method_to_show].keys())
        plt.plot(xline, [values[method_to_show][j] for j in xline], label=method_to_show.name)
    plt.xlabel('Batch size')
    plt.legend(loc='upper left')
    plt.savefig(path_to_save + name + '.png')


def log_record(logger, entity_name, run_id, method_name, batch_size, message):
    logger.info('Entity: ' + str(entity_name) + ' RunID: ' + str(run_id) + ' Method: ' + str(
        method_name) + ' Batch size: ' + str(batch_size) + ' ' + str(message))


def save_ids_list(path_to_save,  method, ids):
    with open(path_to_save + method + '_ids.txt', 'w') as f:
        for item in ids:
            f.write("%s\n" % item)
