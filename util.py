"""
Created on Sat Dec 10 12:00:17 2016

@author: Asuka
"""
import ast
import csv
import datetime
import json
import logging
import math
import os.path
import pickle
import ssl

import aiohttp
import numpy as np
import pyproj
from scipy import spatial
from shapely.geometry import Point
from tabulate import tabulate
import asyncio

import config
import passenger_flow

logger = logging.getLogger(__name__)


def is_opening(random_act, starttime, endtime):
    """is_opening(string, datetime.datetime, datetime.datetime)
    validate if the random_act location is opening during starttime-endtime
    """
    weekday = starttime.isoweekday()

    opening_time_interval = config.RANDOM_ACTIVITY_CONFIG[
        config.OPENING_TIME][random_act][weekday]
    open_time = starttime.replace(
        hour=0, minute=0,
        second=0, microsecond=0) + opening_time_interval[0]
    close_time = starttime.replace(
        hour=0, minute=0,
        second=0, microsecond=0) + opening_time_interval[1]
    # print(open_time, starttime, close_time)
    if open_time <= starttime < close_time:
        return True
    else:
        return False


# return the maximum duation of random activity
def max_duration(random_act, starttime):
    weekday = starttime.isoweekday()

    opening_time_interval = config.RANDOM_ACTIVITY_CONFIG[
        config.OPENING_TIME][random_act][weekday]

    close_time = starttime.replace(
        hour=0, minute=0,
        second=0, microsecond=0) + opening_time_interval[1]

    return close_time - starttime


def chop_microseconds(delta):
    return delta - datetime.timedelta(microseconds=delta.microseconds)


def calculate_distance_from_path(coordinate_list):
    pairs = zip(coordinate_list[:-1], coordinate_list[1:])
    total_distance = 0
    for (point1, point2) in pairs:
        lon1, lat1 = point1
        lon2, lat2 = point2
        distance = calculate_distance(Point(lon1, lat1), Point(lon2, lat2))
        total_distance += distance
    return total_distance


def calculate_distance(startpoint, endpoint):
    """
    distance unit defined as km
    calculate_distance<Point, Point>
    """

    """
    #http://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    lon1, lat1 = startpoint.x, startpoint.y
    lon2, lat2 = endpoint.x, endpoint.y

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * \
                                  math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    km = config.EARTH_RADIUS / 1000.0 * c

    return km


def store_geojson(geojson, filename, append=False):
    if append:
        arg = 'aw'
    else:
        arg = 'w'

    output_filename = 'output/' + filename + ".geojson"
    with open(output_filename, arg) as output_filename:
        json.dump(geojson, output_filename, indent=2)


def store_pickle_file(filename, result_list):
    # store the result into file with binary format
    with open('output/' + filename + '.pkl', 'wb') as f:
        pickle.dump(result_list, f, pickle.HIGHEST_PROTOCOL)


def read_pickle_file(filename):
    # read the result from file with binary format
    with open('output/' + filename + '.pkl', 'rb') as f:
        result = pickle.load(f)
    return result


def print_routine_to_console(routine, show_location=False):
    tabulate_content = []
    now_date = config.START_DATETIME.date()
    for i, act in enumerate(routine):
        if act.starttime.date() != now_date:
            now_date = act.starttime.date()
            tabulate_content.append([now_date])
        act_list = act.output_list(show_location)
        act_list.insert(0, i)
        tabulate_content.append(act_list)
    headers = ['No.', 'Category', 'Remark',
               'Starttime', 'Endtime', 'Location']
    print(tabulate(tabulate_content, headers=headers, tablefmt='orgtbl'))
    print('\n')


def convert_routine_into_geojson(routine_list):
    geojson = {"type": "FeatureCollection", "features": []}
    counter = 0
    for Route_or_Activity in routine_list:
        if isinstance(Route_or_Activity, passenger_flow.Route):
            feature_route = {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "LineString",
                             "coordinates": []}
            }
            feature_route["geometry"]["coordinates"] = Route_or_Activity.path
            if Route_or_Activity.category == config.MOTIS_WITH_BIKE or \
                            Route_or_Activity.category == config.MOTIS_WITHOUT_BIKE:
                # blue color for motis
                feature_route["properties"]["stroke"] = "#0000ff"
            if Route_or_Activity.category == config.OSRM:
                # red color or osrm
                feature_route["properties"]["stroke"] = "#ff0000"
            if Route_or_Activity.category == config.ESTIMATE:
                # green color or self estimate
                feature_route["properties"]["stroke"] = "#008000"
            feature_route["properties"]["category"] = Route_or_Activity.category
            feature_route["properties"]["stroke-width"] = 6
            feature_route["properties"]["stroke-opacity"] = 0.5
            feature_route["properties"]["end time"] = str(Route_or_Activity.endtime)
            feature_route["properties"]["start time"] = str(Route_or_Activity.starttime)
            feature_route["properties"]["remark"] = Route_or_Activity.remark
            feature_route["properties"]["duration"] = str(Route_or_Activity.duration)
            feature_route["properties"]["order"] = counter
            counter += 1
            geojson["features"].append(feature_route)
        if isinstance(Route_or_Activity, passenger_flow.Activity):
            feature = {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Point",
                             "coordinates": []}
            }
            feature["geometry"]["coordinates"] = list(
                Route_or_Activity.location.coords[0])
            if Route_or_Activity.category == config.SLEEP:
                # green color for sleep
                feature["properties"]["marker-color"] = "#008000"
                feature["properties"]["marker-symbol"] = "star"
            if Route_or_Activity.category == config.WORK:
                # orange for work
                feature["properties"]["marker-color"] = "#ff8040"
            if Route_or_Activity.category == config.COMMERCIAL:
                # yellow for shopping
                feature["properties"]["marker-color"] = "#ffff00"
            if Route_or_Activity.category == config.SELFSTUDY:
                # red for selfstudy
                feature["properties"]["marker-color"] = "#ff0000"
            if Route_or_Activity.category == config.RECREATION:
                # blue for hangout
                feature["properties"]["marker-color"] = "#0000ff"
            if Route_or_Activity.category == config.ATTEND_CLASS:
                # red for having lecture
                feature["properties"]["marker-color"] = "#ff0000"

            feature["properties"]["category"] = Route_or_Activity.category
            feature["properties"]["remark"] = Route_or_Activity.remark
            feature["properties"]["end time"] = str(Route_or_Activity.endtime)
            feature["properties"]["start time"] = str(Route_or_Activity.starttime)
            feature["properties"]["duration"] = str(Route_or_Activity.duration)
            feature["properties"]["order"] = counter
            counter += 1
            geojson["features"].append(feature)
    return geojson


def convert_amenity_into_geojson(amenity_list):
    geojson = {"type": "FeatureCollection", "features": []}
    for amenity in amenity_list:
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Point",
                         "coordinates": []}
        }
        feature["geometry"]["coordinates"] = amenity[:2]
        feature["properties"]["category"] = amenity[2]
        feature["properties"]["name"] = amenity[3]
        geojson["features"].append(feature)
    return geojson


def convert_csv_into_geojson(squares, filename):
    geojson = {"type": "FeatureCollection", "features": []}
    for square in squares:
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {"type": "Point",
                         "coordinates": []}
        }
        feature["geometry"]["coordinates"] = square[:2]
        feature["properties"]["marker-color"] = "#ff8040"  # orange
        feature["properties"]["category"] = square[2]
        feature["properties"]["name"] = square[3]
        feature["properties"]["population"] = square[4]
        geojson["features"].append(feature)

    store_geojson(geojson, filename)


async def query_motis(req, client, i, retry=False):
    config.QUERY_TIME += 1
    if retry:
        sslcontext = ssl.create_default_context(cafile='student2015.motis-project.de.crt')
        conn = aiohttp.TCPConnector(ssl_context=sslcontext, limit=3)
        # await asyncio.sleep(20)
        oldclient = client
        client = aiohttp.ClientSession(connector=conn)
        logger.info('{} Client same? {}'.format(i, oldclient is client))
        logger.info('{} OldClient closed? {}'.format(i, oldclient.closed))
        logger.info('{} Client closed? {}'.format(i, client.closed))
    try:
        if client.closed:
            logger.error('{} ***Client closed!***'.format(i))
            await asyncio.sleep(120)
            return None
        async with client.post(
                "https://student2015.motis-project.de",
                data=req,
                auth=aiohttp.BasicAuth(
                    "mobilitysim",
                    "b52b15a9205bbfdb3faa1c0e57bf183643779f86172ee4b16e38b591151cbdc8"),
                headers={"Content-Type": "application/json"}) as resp:
            response_text = await resp.text()

        return response_text
    except aiohttp.client_exceptions.ServerDisconnectedError as exc:
        logger.error('{} Server Disconnected!'.format(i))
        client.close()
        await query_motis(req, client, i, True)


def gen_intermodal_routing_request(startpoint_lat, startpoint_lng, requesttime,
                                   endpoint_lat, endpoint_lng, has_bike):
    """
    gen_intermodal_routing_request(startpoint.y, startpoint.x,
    requesttime_timestamp,endpoint.y, endpoint.x)
    """
    if has_bike:
        mode_type = "Bike"
    else:
        mode_type = "Foot"
    return """
    {{
      "destination": {{
        "type": "Module",
        "target": "/intermodal"
      }},
      "content_type": "IntermodalRoutingRequest",
      "content": {{
        "start_type": "IntermodalOntripStart",
        "start": {{
          "position": {{ "lat": {}, "lng": {}}},
          "departure_time": {}
        }},
        "start_modes": [{{
          "mode_type": "{}",
          "mode": {{ "max_duration": 900 }}
        }}],
        "destination_type": "InputPosition",
        "destination": {{ "lat": {}, "lng": {}}},
        "destination_modes":  [{{
          "mode_type": "{}",
          "mode": {{ "max_duration": 900 }}
        }}],
        "search_type": "SingleCriterionNoIntercity"
      }}
    }}
    """.format(startpoint_lat, startpoint_lng, requesttime,
               mode_type, endpoint_lat, endpoint_lng, mode_type)


# gen_osrm_request(tool, startpoint.y, startpoint.x, endpoint.y, endpoint.x)
def gen_osrm_request(tool, startpoint_lat, startpoint_lng,
                     endpoint_lat, endpoint_lng):
    return """
    {{
      "destination": {{
        "type": "Module",
        "target": "/osrm/via"
      }},
      "content_type": "OSRMViaRouteRequest",
      "content": {{
        "profile": "{}",
        "waypoints": [
          {{ "lat": {}, "lng": {} }},
          {{ "lat": {}, "lng": {} }}
         ]
      }}
    }}
    """.format(tool, startpoint_lat, startpoint_lng,
               endpoint_lat, endpoint_lng)


def k_nearest_point(activity_category, current_point, person_character=None):
    """
    read all points from geojson and convert to Mercator
    build Kdtree, find the k nearest points and convert to latlon
    return the prob list and neighbors list
    :rtype: tuple
    """
    if person_character == config.ACTIVE:
        k = 10
    elif person_character == config.COMFORTABLE:
        k = 5
    elif not person_character:
        k = 5
    else:
        raise RuntimeError('Wrong Person Character Format')

    if activity_category == config.RECREATION:
        with open(config.LEISURE_FILE, 'r') as f:
            leisuredata = json.load(f)
        data_dict = leisuredata

    elif activity_category == config.COMMERCIAL:
        with open(config.SHOP_FILE, 'r') as f:
            shopdata = json.load(f)
        data_dict = shopdata

    elif activity_category == config.SELFSTUDY or \
                    activity_category == config.ATTEND_CLASS:
        with open(config.UNI_FILE, 'r') as f:
            unidata = json.load(f)
        data_dict = unidata

    elif activity_category == config.WORK:

        if not os.path.exists(config.COMPANY_FILE):
            basename = os.path.basename(config.COMPANY_FILE)
            filename = os.path.splitext(basename)[0]
            get_company_population(filename)

        with open(config.COMPANY_FILE, 'r') as f:
            companydata = json.load(f)
        data_dict = companydata

    data = []
    populations = []
    # convert points to WebMercator
    for feature in data_dict['features']:
        if activity_category == config.WORK:
            populations.append(feature["properties"]["population"])

        lon, lat = feature["geometry"]["coordinates"]
        data.append([lon2x(lon), lat2y(lat)])

    tree = spatial.cKDTree(data)
    # convert query point to WebMercator
    query_point = lon2x(current_point.x), lat2y(current_point.y)
    dd, ii = tree.query(query_point, k=k)

    # ignore all zero distance point
    nonzero_list = [i for i, d in enumerate(dd) if d != 0]
    dd = [dd[i] for i in nonzero_list]
    ii = [ii[i] for i in nonzero_list]

    # working place probability based on population
    # other place probability based on 1/distance
    if activity_category == config.WORK:
        probabilties = [populations[i] for i in ii]
    else:
        probabilties = [1 / d for d in dd]

    sum_of_prob = sum(probabilties)
    normalized_probs = [p / sum_of_prob for p in probabilties]

    neighbors = []
    # recover points to WGS84
    for i in ii:
        x, y = data[i][:2]
        neighbors.append(Point(x2lon(x), y2lat(y)))

    return normalized_probs, neighbors


def get_residence_population(filename):
    # return the middle point of the cell 100m*100m and its population
    squares = []
    if not os.path.exists('output/' + filename + '.pkl'):
        min_lon, min_lat = config.DARMSTADT_BOUND_LEFT_DOWN
        max_lon, max_lat = config.DARMSTADT_BOUND_RIGHT_UP

        min_x, min_y = wgs84_to_etrs(min_lon, min_lat)
        max_x, max_y = wgs84_to_etrs(max_lon, max_lat)

        with open(config.ZENSUS_FILE, 'r') as zensus_file:
            reader = csv.DictReader(zensus_file, delimiter=';')
            for row in reader:
                population = ast.literal_eval(row['Einwohner'])

                if population >= config.MIN_POPULATION:
                    x, y = ast.literal_eval(row['x_mp_100m']), ast.literal_eval(row['y_mp_100m'])
                    if min_x < x < max_x and min_y < y < max_y:
                        squares.append([x, y, population])

        logger.info("Finish reading zensus data")
        store_pickle_file(filename, squares)
        squares = np.array(squares)
    else:
        squares = np.array(read_pickle_file(filename))
    return squares


def get_company_population(filename):
    squares = []

    with open(config.CSV_COMPANY_FILE, 'r', encoding='utf-8') as company_file:
        reader = csv.DictReader(company_file)
        for row in reader:
            x, y = float(row['lng']), float(row['lat'])
            population = float(row['workers'])
            name = row['name']
            squares.append([x, y, 'company', name, population])

        convert_csv_into_geojson(squares, filename)

    logger.info("Finish converting company data")


def get_weekday(current_datetime):
    weekday = current_datetime.isoweekday()
    if 1 <= weekday <= 5:
        weekend_par = config.WORKDAY
    else:
        weekend_par = config.WEEKEND

    return weekend_par


# WebMercator to WGS84
def x2lon(a):
    return math.degrees(a / config.EARTH_RADIUS)


def y2lat(a):
    return math.degrees(
        2 * math.atan(math.exp(a / config.EARTH_RADIUS)) - math.pi / 2.0)


# WGS84 to WebMercator
def lon2x(a):
    return math.radians(a) * config.EARTH_RADIUS


def lat2y(a):
    return math.log(
        math.tan(math.pi / 4.0 + math.radians(a) / 2.0)) * config.EARTH_RADIUS


# change the section direction when pointing below x axis
def convert_section(startpoint, endpoint):
    lon_from, lat_from = ast.literal_eval(startpoint)
    lon_to, lat_to = ast.literal_eval(endpoint)

    if lat_to < lat_from:
        return endpoint, startpoint
    elif lat_to == lat_from and lon_to > lon_from:
        return endpoint, startpoint
    else:
        return startpoint, endpoint


# Converts wgs84 coords into metric (ETRS, EPSG:3035) coords
def wgs84_to_etrs(lon, lat):
    etrs_coord = pyproj.Proj("+init=EPSG:3035")
    return etrs_coord(lon, lat, inverse=False)


# Converts metric (ETRS, EPSG:3035) coords into wgs84 coords
def etrs_to_wgs84(x, y):
    etrs_coord = pyproj.Proj("+init=EPSG:3035")
    return etrs_coord(x, y, inverse=True)
