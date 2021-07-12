import ast
import collections
import json
import math
import os.path
from datetime import timedelta
from functools import update_wrapper

import flask
from flask import make_response, request, current_app

import config
import database


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, str):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, str):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)

    return decorator


app = flask.Flask(__name__)


@app.route('/')
def hello_world():
    filename = flask.request.args.get("database")
    if filename == 'football':
        config.DATABASE_FILE = "output/transportation_football.sqlite"
    elif filename == 'normal':
        config.DATABASE_FILE = "output/transportation_normal.sqlite"
    elif filename == 'weekend':
        config.DATABASE_FILE = "output/transportation_weekend.sqlite"
    else:
        pass

    return flask.redirect(flask.url_for('static', filename='leaflet.html'))


@app.route("/draw_all_lines")
@crossdomain(origin="*")
def draw_all_lines():
    lines = database.get_line_width(config.QUERY_WIDTH_SQL)

    result = []
    for startpoint, endpoint in lines:
        lon_from, lat_from = ast.literal_eval(startpoint)
        lon_to, lat_to = ast.literal_eval(endpoint)

        count = lines[(startpoint, endpoint)]
        width = math.log2(count) if count > 1 else 1

        js_command = "draw_line([[{0}, {1}], [{2}, {3}]], {4}, '{5}', '{6}')".format(lat_from, lon_from, lat_to, lon_to,
                                                                                     width, startpoint, endpoint)
        result.append(js_command)

    return json.dumps(result)


@app.route("/get_related_lines")
@crossdomain(origin="*")
def get_related_lines():
    line_id = flask.request.args.get("id")
    split = line_id.split("_")

    # first_id(startpoint) second_id(endpoint) in leaflet.html
    startpoint = split[0]
    endpoint = split[1]
    lines = database.get_related_line(config.QUERY_RELATED_LINE_SQL, startpoint, endpoint)

    result = []

    for line in lines:
        js_command = "mark_line('{0}', '{1}', '{2}')".format(line['startpoint'], line['endpoint'], "#ff0000")
        result.append(js_command)

    js_command = "mark_line('{0}', '{1}', '{2}')".format(startpoint, endpoint, "#ffff00")
    result.append(js_command)

    return json.dumps(result)


@app.route("/get_line_info")
@crossdomain(origin="*")
def get_line_info():
    line_id = flask.request.args.get("id")
    split = line_id.split("_")

    # first_id(startpoint) second_id(endpoint) in leaflet.html
    startpoint = split[0]
    endpoint = split[1]

    lines = database.get_selected_line(config.QUERY_SELECTED_LINE_SQL, startpoint, endpoint)

    index_dict = collections.defaultdict(list)

    for line in lines:
        index_dict[(line['d_time'], line['direction'], line['name'])].append(line['routine_id'])

    result = []
    for key in index_dict:
        infotable_row = [item for item in key]
        infotable_row.append(index_dict[key])
        result.append(infotable_row)

    result.sort(key=lambda x: (x[2], x[1]))
    return json.dumps(result)


@app.route("/mark_passenger_lines")
@crossdomain(origin="*")
def mark_passenger_lines():
    r_id = flask.request.args.get("routine")
    lines = database.get_rid_line(config.QUERY_RID_LINE_SQL, (int(r_id),))

    result = []
    for line in lines:
        js_command = "mark_line('{0}', '{1}', '{2}')".format(line['startpoint'], line['endpoint'], "#ff0000")
        result.append(js_command)

    return json.dumps(result)


@app.route("/get_homes")
@crossdomain(origin="*")
def get_homes():
    result = []

    homes = database.get_amenity(config.QUERY_AMENITY_SQL, (config.SLEEP,))
    for home in homes:
        lon, lat = ast.literal_eval(home)
        js_command = "mark_home([{0}, {1}])".format(lat, lon)
        result.append(js_command)

    return flask.Response(json.dumps(result))


@app.route("/get_companies")
@crossdomain(origin="*")
def get_companies():
    company_type = flask.request.args.get("type")
    result = []

    if company_type == 'all':
        companyfile = os.path.join(config.PROJECT_ROOT, config.COMPANY_FILE)
        companies = json.load(open(companyfile, 'r'))

        for company in companies["features"]:
            name = company["properties"]["name"].replace("'", r"\'")
            lon, lat = company["geometry"]["coordinates"]
            worker = int(company["properties"]["population"])
            js_command = "mark_company('{0}', [{1}, {2}], {3}, '{4}')".format(name, lat, lon, worker, 'all')
            result.append(js_command)
    else:
        companies = database.get_amenity(config.QUERY_AMENITY_SQL, (config.WORK,))
        for company in companies:
            lon, lat = ast.literal_eval(company)
            js_command = "mark_company('{0}', [{1}, {2}], {3}, '{4}')".format('', lat, lon, 0, 'ralated')
            result.append(js_command)
    return flask.Response(json.dumps(result))


@app.route("/get_unis")
@crossdomain(origin="*")
def get_unis():
    uni_type = flask.request.args.get("type")
    result = []

    if uni_type == 'all':
        unifile = os.path.join(config.PROJECT_ROOT, config.UNI_FILE)
        unis = json.load(open(unifile, 'r'))

        for uni in unis["features"]:
            name = uni["properties"]["name"].replace("'", r"\'")
            lon, lat = uni["geometry"]["coordinates"]
            js_command = "mark_uni('{0}', [{1}, {2}], '{3}')".format(name, lat, lon, 'all')
            result.append(js_command)
    else:
        unis = database.get_amenity(config.QUERY_AMENITY_SQL, (config.ATTEND_CLASS,))
        for uni in unis:
            lon, lat = ast.literal_eval(uni)
            js_command = "mark_uni('{0}', [{1}, {2}], '{3}')".format('', lat, lon, 'related')
            result.append(js_command)
    return json.dumps(result)


@app.route("/get_parks")
@crossdomain(origin="*")
def get_parks():
    park_type = flask.request.args.get("type")
    result = []

    if park_type == 'all':
        leisurefile = os.path.join(config.PROJECT_ROOT, config.LEISURE_FILE)
        parks = json.load(open(leisurefile, 'r'))

        for park in parks["features"]:
            name = park["properties"]["name"].replace("'", r"\'")
            lon, lat = park["geometry"]["coordinates"]
            js_command = "mark_park('{0}', [{1}, {2}], '{3}')".format(name, lat, lon, 'all')
            result.append(js_command)
    else:
        parks = database.get_amenity(config.QUERY_AMENITY_SQL, (config.RECREATION,))
        for park in parks:
            lon, lat = ast.literal_eval(park)
            js_command = "mark_park('{0}', [{1}, {2}], '{3}')".format('', lat, lon, 'related')
            result.append(js_command)

    return json.dumps(result)


@app.route("/get_shops")
@crossdomain(origin="*")
def get_shops():
    shop_type = flask.request.args.get("type")
    result = []

    if shop_type == 'all':
        shopfile = os.path.join(config.PROJECT_ROOT, config.SHOP_FILE)
        shops = json.load(open(shopfile, 'r'))

        for shop in shops["features"]:
            name = shop["properties"]["name"].replace("'", r"\'")
            lon, lat = shop["geometry"]["coordinates"]
            js_command = "mark_shop('{0}', [{1}, {2}], '{3}')".format(name, lat, lon, 'all')
            result.append(js_command)
    else:
        shops = database.get_amenity(config.QUERY_AMENITY_SQL, (config.COMMERCIAL,))
        for shop in shops:
            lon, lat = ast.literal_eval(shop)
            js_command = "mark_shop('{0}', [{1}, {2}], '{3}')".format('', lat, lon, 'related')
            result.append(js_command)

    return json.dumps(result)


app.run("0.0.0.0", debug=True)
