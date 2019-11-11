import csv
import matplotlib.pyplot as plt

WARNING_PRODUCTS_IN_PROGRESS = 'Some products are still in progress'
TIMEOUT_MESSAGE_ON_PRODUCT_CREATION = 'Timeout on waiting for items creation'
MESSAGE_SENDING_STARTED = 'Sending started'
MESSAGE_SENDING_FINISHED = 'Sending finished'


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
        plt.plot(values[method_to_show].keys(),
                 [values[method_to_show][j] for j in values[method_to_show].keys()], label=method_to_show.name)
    plt.xlabel('Sent batch size')
    plt.legend(loc='upper left')
    plt.savefig(path_to_save + name + '.png')


def log_record(logger, entity_name, run_id, method_name, batch_size, message):
    logger.info('Entity: ' + entity_name + ' RunID: ' + str(run_id) + ' Method: ' + method_name + ' Batch size: ' + str(
        batch_size) + ' ' + message)
