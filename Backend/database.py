import logging
import os.path
import sqlite3
from sqlite3 import Error

import config
import passenger_flow
import util

logger = logging.getLogger(__name__)


def create_connection(db_file):
    """create a database connection to a database that resides in the memory"""
    try:
        conn = sqlite3.connect(db_file)
        logger.info("Opened database successfully")
        return conn
    except Error as e:
        print(e)
    return None


# get the line by given routine_id
def get_rid_line(query_sql, rid):
    lines = []

    query_result = query_database(query_sql, rid)
    for row in query_result:
        section = util.convert_section(row[0], row[1])
        item = {'startpoint': section[0],
                'endpoint': section[1]}
        lines.append(item)
    return lines


# get all lines between startpoint and endpoint
def get_selected_line(query_sql, startpoint, endpoint):
    lines = []

    query_result = query_database(query_sql, {"startpoint": startpoint, "endpoint": endpoint})
    for row in query_result:
        item = {'d_time': row[0],
                'direction': row[1],
                'name': row[2],
                'routine_id': row[3]}
        lines.append(item)
    return lines


# get all route containing the startpoint and endpoint
def get_related_line(query_sql, startpoint, endpoint):
    lines = []

    query_result = query_database(query_sql, {"startpoint": startpoint, "endpoint": endpoint})

    for row in query_result:
        section = util.convert_section(row[0], row[1])

        item = {'startpoint': section[0],
                'endpoint': section[1]}

        lines.append(item)
    return lines


def get_line_width(query_sql):
    undirect_lines = {}

    query_result = query_database(query_sql)
    for row in query_result:
        startpoint = row[0]
        endpoint = row[1]
        count = row[2]

        section = util.convert_section(startpoint, endpoint)

        if section in undirect_lines:
            undirect_lines[section] += count
        else:
            undirect_lines[section] = count

    return undirect_lines


def get_amenity(query_sql, activity_type):
    points = []

    query_result = query_database(query_sql, activity_type)

    for row in query_result:
        points.append(row[0])
    return points


def query_database(query_sql, content=None, specific_database=None):
    if specific_database:
        database = os.path.join(config.PROJECT_ROOT, specific_database)
    else:
        database = os.path.join(config.PROJECT_ROOT, config.DATABASE_FILE)

    conn = create_connection(database)
    query_result = []

    if not conn:
        logger.error("Error! cannot create the database connection.")
    with conn:
        try:
            c = conn.cursor()
            if content:
                c.execute(query_sql, content)
            else:
                c.execute(query_sql)

            query_result = c.fetchall()

        except Error as e:
            print(e)
    return query_result


def change_index(sql):
    database = os.path.join(config.PROJECT_ROOT, config.DATABASE_FILE)
    conn = create_connection(database)

    if not conn:
        logger.error("Error! cannot create the database connection.")
    with conn:
        try:
            c = conn.cursor()
            c.executescript(sql)
        except Error as e:
            print(e)


def write_to_database(r, s):
    database = os.path.join(config.PROJECT_ROOT, config.DATABASE_FILE)
    conn = create_connection(database)

    if conn:
        # create table if not exists
        create_table(conn, config.CREATE_PERSON_TABLE_SQL)
        create_table(conn, config.CREATE_ROUTINE_TABLE_SQL)
        create_table(conn, config.CREATE_SECTION_TABLE_SQL)
    else:
        logger.error("Error! cannot create the database connection.")

    with conn:
        person = (s[config.STAT_PERSONTYPE], s[config.STAT_CHARACTER], s[config.STAT_CAR], s[config.STAT_BIKE],
                  s[config.STAT_OEPNV], s[config.STAT_TRANTOOL], s[config.STAT_DISTANCE],
                  str(s[config.STAT_ONROAD_DURATION]), s[config.STAT_OSRM], s[config.STAT_MOTIS],
                  str(s[config.STAT_OSRM_TIME]),
                  str(s[config.STAT_MOTIS_TIME]))
        # insert data into person table
        person_id = insert_record(conn, 'person', person)

        for route_or_activity in r:
            if isinstance(route_or_activity, passenger_flow.Route):
                route = route_or_activity

                routine = (
                    route.category,
                    person_id,
                    route.remark,
                    str(route.starttime),
                    str(route.endtime),
                    str(route.duration),
                    str(route.path)
                )
                # insert data(Route) into routine table
                routine_id = insert_record(conn, 'routine', routine)
                # insert data into section table
                insert_section(conn, route, routine_id)

            elif isinstance(route_or_activity, passenger_flow.Activity):
                activity = route_or_activity
                routine = (
                    activity.category,
                    person_id,
                    activity.remark,
                    str(activity.starttime),
                    str(activity.endtime),
                    str(activity.duration),
                    str(activity.location.coords[0])
                )
                # insert data(Activity) into routine table
                insert_record(conn, 'routine', routine)

        logger.info('Write to database finished.\n')


def create_table(conn, create_table_sql):
    """create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def insert_record(conn, record_type, content):
    if record_type == 'person':
        sql = config.INSERT_PERSON_SQL
    elif record_type == 'routine':
        sql = config.INSERT_ROUTINE_SQL
    elif record_type == 'section':
        sql = config.INSERT_SECTION_SQL
    else:
        sql = ''
    cur = conn.cursor()
    cur.execute(sql, content)
    return cur.lastrowid


def insert_section(conn, route, routine_id):
    # only draw public transport lines
    if route.category == config.MOTIS_WITH_BIKE or route.category == config.MOTIS_WITHOUT_BIKE:
        section_list = route.section

        for section_dict in section_list:
            if section_dict['name'] == 'Walk':
                pass
            else:
                section = (
                    str(section_dict['startpoint']),
                    str(section_dict['endpoint']),
                    str(section_dict['d_time']),
                    str(section_dict['direction']),
                    str(section_dict['name']),
                    str(section_dict['trip_id']),
                    routine_id
                )
                insert_record(conn, 'section', section)

    # elif route.category == config.ESTIMATE or route.category == config.OSRM:
    #     path = route.path
    #     for i in range(1, len(path)):
    #         startpoint = path[i - 1]
    #         endpoint = path[i]
    #         name = route.remark
    #         section = (str(startpoint), str(endpoint), '', '', str(name), routine_id)
    #         insert_record(conn, 'section', section)

    # route.category == config.STAY_STILL
    else:
        pass
