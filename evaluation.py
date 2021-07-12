from datetime import datetime

import numpy as np
from tabulate import tabulate

import config
import database

category_dict = {
    'NORMAL': config.DATABASE_NORMAL,
    'WEEKEND': config.DATABASE_WEEKEND,
    'FOOTBALL': config.DATABASE_FOOTBALL
}


def validate_format(date_text):
    try:
        datetime.strptime(date_text, "%H:%M:%S")
        return True
    except ValueError:
        return False


def print_evaluation_result(tabulate_content):
    headers = ['Category', 'Motis Query Time (hh:mm:ss)', 'Osrm query time (hh:mm:ss)', 'Motis usage', 'Osrm usage',
               'Onroad Duration (hh:mm:ss)',
               'Distance (km)', 'Car Usage', 'Bike Usage', 'Public Transport Usage']
    print(tabulate(tabulate_content, headers=headers, tablefmt='orgtbl', numalign="left"))
    print('\n')


def evaluation():
    result = []
    for category in category_dict:
        query_result = database.query_database(config.EVALUATION_SQL, specific_database=category_dict[category])

        mqt = [datetime.strptime(row[0], "%H:%M:%S.%f") - datetime(1900, 1, 1) for row in query_result if
               row[0] != '0:00:00']
        oqt = [datetime.strptime(row[1], "%H:%M:%S.%f") - datetime(1900, 1, 1) for row in query_result if
               row[1] != '0:00:00']
        mu = [int(row[2]) for row in query_result if int(row[2]) != 0]
        ou = [int(row[3]) for row in query_result if int(row[3]) != 0]
        ord = [datetime.strptime(row[4], "%H:%M:%S") - datetime(1900, 1, 1) for row in query_result if
               validate_format(row[4])]
        dis = [float(row[5]) for row in query_result if float(row[5]) != 0]
        car = [int(row[6]) for row in query_result if int(row[6]) != 0]
        bike = [int(row[7]) for row in query_result if int(row[7]) != 0]
        pub = [int(row[8]) for row in query_result if int(row[8]) != 0]

        row = [category, np.mean(mqt), np.mean(oqt), np.mean(mu), np.mean(ou), np.mean(ord), np.mean(dis), np.mean(car),
               np.mean(bike), np.mean(pub)]
        result.append(row)
    return result


if __name__ == '__main__':
    results = evaluation()
    print_evaluation_result(results)
