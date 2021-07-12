"""
Created on Tue Nov  8 10:33:49 2016

@author: martin
"""
import asyncio
import datetime
import logging
import ssl
from concurrent.futures import FIRST_COMPLETED
import time

import aiohttp
import numpy as np

import config
import database
import util
from person import Person


def print_result(routine, statistic, filenumber, show_on_console, geojson_file):
    routine.sort(key=lambda x: x.starttime)

    if show_on_console:
        print(statistic.items())
        # could output location by show_location=True
        util.print_routine_to_console(routine)

    if geojson_file:
        file = util.convert_routine_into_geojson(routine)
        util.store_geojson(file, 'Data_{}'.format(filenumber + 1))


def add_to_pending(client, start_id, person_num, generate_days, pending_set, football_event):
    for i in range(start_id, start_id + person_num):
        person_type = np.random.choice([config.STUDENT, config.EMPLOYEE])
        character = [
            np.random.choice([config.COMFORTABLE, config.ACTIVE]),
            np.random.choice([config.INTROVERTED, config.EXTROVERTRD]),
            np.random.choice([config.LONGSLEEPER, config.EARLYRISER])]

        p = Person(person_type, character)
        feature = p.generate_routine(generate_days, client, i, football_event)
        pending_set.add(feature)


async def divide_bignum(person_nums, generate_days, show_on_console=True, geojson_file=False, sqlite=True,
                        football_event=False):
    """
    :param person_nums: how many person generated
    :param generate_days: how many days generated for each person
    :param show_on_console: choose if print out final routine
    :param geojson_file: choose if generate geojson file for each person
    :param sqlite: choose if write result to the database
    :param football_event: choose if create football_event for each person
    :return:
    """
    max_count = person_nums
    has_finished = 0
    threshold = config.MAX_GENERATE_PERSON

    pending = set()

    sslcontext = ssl.create_default_context(cafile='student2015.motis-project.de.crt')
    conn = aiohttp.TCPConnector(ssl_context=sslcontext, limit=10)

    add_pending_len = threshold if person_nums > threshold else person_nums

    async with aiohttp.ClientSession(connector=conn) as client:
        add_to_pending(client, 0, add_pending_len, generate_days, pending, football_event)

        # drop index before change database
        database.change_index(config.DROP_INDEX_SQL)
        while pending:

            done, pending = await asyncio.wait(pending, return_when=FIRST_COMPLETED)

            for i, future in enumerate(done):
                # todo need to handle aiohttp.errors.ServerDisconnectedError
                routine, statistic = await future

                print_result(routine, statistic, i + has_finished, show_on_console, geojson_file)

                if sqlite:
                    database.write_to_database(routine, statistic)

            has_finished += len(done)

            if has_finished + len(pending) < max_count:
                to_be_done = max_count - has_finished
                pending_len = threshold if to_be_done > threshold else to_be_done
                add_pending_len = pending_len - len(pending)

                add_to_pending(client, has_finished, add_pending_len, generate_days, pending, football_event)
                # await asyncio.sleep(10)
        # add index after write all data
        database.change_index(config.CREATE_INDEX_SQL)


if __name__ == '__main__':
    start_time = datetime.datetime.now()
    logging.getLogger("requests").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(divide_bignum(300, 1, geojson_file=False, sqlite=True, football_event=True))
    logging.info('Duration: {}\n'.format(datetime.datetime.now() - start_time))
