"""
Created on Wed Jan 11 19:51:34 2017

@author: Asuka
"""
import copy
import datetime
import json
import logging
import time
from operator import attrgetter

import numpy as np
from shapely.geometry import Point

import config
import util
from passenger_flow import Activity
from passenger_flow import AreaPoint
from passenger_flow import Route
from passenger_flow import TransportationTool

logger = logging.getLogger(__name__)


# logger.setLevel(logging.WARNING)


class Person:
    def __init__(self, person_type, character):
        self.person_type = person_type
        self.character = character
        self.current_location = None
        self.current_time = None
        self.home = None
        self.uni = None
        self.workplace = None
        self.tran_tool = None
        self.activities_preference = None
        self.routine = []
        self.statistics = dict()
        self.generate_essential_place()
        self.set_initial_time_and_loc()
        self.generate_transportation_tool()
        self.calculate_activities_probability()
        self.initialize_statistics()

    def initialize_statistics(self):
        self.statistics[config.STAT_PERSONTYPE] = ''
        self.statistics[config.STAT_CHARACTER] = ''
        self.statistics[config.STAT_TRANTOOL] = ''
        self.statistics[config.STAT_DISTANCE] = 0.0
        self.statistics[config.STAT_ONROAD_DURATION] = datetime.timedelta(0)
        self.statistics[config.STAT_BIKE] = 0
        self.statistics[config.STAT_CAR] = 0
        self.statistics[config.STAT_OEPNV] = 0
        self.statistics[config.STAT_MOTIS] = 0
        self.statistics[config.STAT_OSRM] = 0
        self.statistics[config.STAT_MOTIS_TIME] = datetime.timedelta(0)
        self.statistics[config.STAT_OSRM_TIME] = datetime.timedelta(0)

    def set_initial_time_and_loc(self):
        """
        the current self.location is home and datetime is wake up time
        the type of self.current_time is datatime.datetime
        """
        # the initial time will be set as wake up time
        self.current_location = self.home.location
        current_datetime = config.START_DATETIME

        active_fea = self.character[0]
        sleep_fea = self.character[2]

        weekend_par = util.get_weekday(current_datetime)

        if config.ACTIVE == active_fea or config.COMFORTABLE == active_fea:
            mu, sigma = config.ESSENTIAL_ACTIVITY_CONFIG[config.SLEEP][weekend_par][
                config.STARTTIME][active_fea][self.person_type]
            sleep_starttime = datetime.timedelta(
                hours=np.random.normal(mu, sigma))
        else:
            raise RuntimeError('Wrong Person Character Format')

        if config.LONGSLEEPER == sleep_fea or config.EARLYRISER == sleep_fea:
            mu, sigma = config.ESSENTIAL_ACTIVITY_CONFIG[config.SLEEP][weekend_par][
                config.DURATION][sleep_fea]
            sleep_duration = datetime.timedelta(
                hours=np.random.normal(mu, sigma))
        else:
            raise RuntimeError('Wrong Person Character Format')

        sleep_startdatetime = current_datetime + sleep_starttime
        self.current_time = (sleep_startdatetime +
                             sleep_duration).replace(microsecond=0)

    def generate_essential_place(self):
        self.home = AreaPoint(config.SLEEP)

        if self.person_type == config.STUDENT:
            self.uni = AreaPoint(config.ATTEND_CLASS, current_point=self.home.location)

        elif self.person_type == config.EMPLOYEE:
            self.workplace = AreaPoint(config.WORK, current_point=self.home.location)

    def generate_transportation_tool(self):
        """
        probability of having the certain tran_tool based on person type
        add the attribute <dict> self.tran_tool
        """
        car_temp = TransportationTool(config.CAR, self.home.location)
        bike_temp = TransportationTool(config.BIKE, self.home.location)

        car = None
        bike = None
        if self.person_type == config.STUDENT:
            car = np.random.choice(
                [car_temp, None],
                p=config.TOOL_PROBABILITY_CONFIG
                [config.STUDENT][config.CAR])
            bike = np.random.choice(
                [bike_temp, None],
                p=config.TOOL_PROBABILITY_CONFIG
                [config.STUDENT][config.BIKE])
        elif self.person_type == config.EMPLOYEE:
            car = np.random.choice(
                [car_temp, None],
                p=config.TOOL_PROBABILITY_CONFIG
                [config.EMPLOYEE][config.CAR])
            bike = np.random.choice(
                [bike_temp, None],
                p=config.TOOL_PROBABILITY_CONFIG
                [config.EMPLOYEE][config.BIKE])

        self.tran_tool = {config.CAR: car, config.BIKE: bike}

    def calculate_activities_probability(self):
        """calculate the probability of random activitie"""
        self.activities_preference = config.PERSONTYPE_ACTIVITY_CONFIG[
            self.person_type]
        for individual_character in self.character:
            for key in self.activities_preference.keys():
                self.activities_preference[key] *= config. \
                    CHARACTER_ACTIVITY_CONFIG[individual_character][key]

        sum_of_activity = sum(self.activities_preference.values())
        for key in self.activities_preference.keys():
            self.activities_preference[key] /= sum_of_activity

    async def set_essential_activities(self, client, i, add_football):
        """add first all the essential activities to the routine"""

        weekend_par = util.get_weekday(self.current_time)
        # add attend_class activity only from Monday to Friday
        if self.person_type == config.STUDENT:

            if weekend_par == config.WORKDAY:
                goingout_datetime = self.current_time
                current_location = self.current_location
                for vorlesung in config.ESSENTIAL_ACTIVITY_CONFIG[config.ATTEND_CLASS]:
                    optimal_commute = await self.get_optimal_commute(
                        current_location, self.uni.location,
                        goingout_datetime, client, i)

                    earliest_starttime = optimal_commute.duration + goingout_datetime
                    earliest_starttimestamp = int(time.mktime(
                        earliest_starttime.timetuple()))

                    mushift, sigma = vorlesung[config.STARTTIME]
                    mutimestamp = int(np.random.normal(0, sigma))
                    if mutimestamp < 0:
                        mutimestamp = -mutimestamp
                    shifttimestamp = mushift + mutimestamp
                    starttimestamp = earliest_starttimestamp + shifttimestamp

                    duration = vorlesung[config.DURATION]
                    attend_class = Activity(self.uni.location,
                                            datetime.datetime.fromtimestamp(starttimestamp),
                                            duration, config.ATTEND_CLASS)

                    self.routine.append(attend_class)
                    logger.info('{} *add attend_class\n{}'.format(i, attend_class.output_list(True)))
                    goingout_datetime = datetime.datetime.fromtimestamp(
                        starttimestamp) + duration
                    current_location = self.uni.location

        # add work activity only from Monday to Friday
        if self.person_type == config.EMPLOYEE:

            if weekend_par == config.WORKDAY:
                optimal_commute = await self.get_optimal_commute(
                    self.current_location,
                    self.workplace.location,
                    self.current_time, client, i)
                earliest_starttime = optimal_commute.duration + self.current_time
                earliest_starttimestamp = int(time.mktime(
                    earliest_starttime.timetuple()))

                mushift, sigma = config.ESSENTIAL_ACTIVITY_CONFIG[config.WORK][
                    config.STARTTIME]
                mutimestamp = int(np.random.normal(0, sigma))
                if mutimestamp < 0:
                    mutimestamp = -mutimestamp
                shifttimestamp = mushift + mutimestamp
                starttimestamp = earliest_starttimestamp + shifttimestamp

                duration = config.ESSENTIAL_ACTIVITY_CONFIG[config.WORK][
                    config.DURATION]
                work = Activity(self.workplace.location,
                                datetime.datetime.fromtimestamp(starttimestamp),
                                duration, config.WORK)

                self.routine.append(work)
                logger.info('{} *add work\n{}'.format(i, work.output_list(True)))

        active_fea = self.character[0]
        sleep_fea = self.character[2]

        # set the sleep activity
        if config.ACTIVE == active_fea or config.COMFORTABLE == active_fea:
            mu, sigma = config.ESSENTIAL_ACTIVITY_CONFIG[config.SLEEP][weekend_par][
                config.STARTTIME][active_fea][self.person_type]
            sleep_starttime = datetime.timedelta(
                hours=np.random.normal(mu, sigma))
        else:
            raise RuntimeError('Wrong Person Character Format')

        if config.LONGSLEEPER == sleep_fea or config.EARLYRISER == sleep_fea:
            mu, sigma = config.ESSENTIAL_ACTIVITY_CONFIG[config.SLEEP][weekend_par][
                config.DURATION][sleep_fea]
            sleep_duration = datetime.timedelta(
                hours=np.random.normal(mu, sigma))
        else:
            raise RuntimeError('Wrong Person Character Format')

        sleep_startdatetime = self.current_time.replace(
            hour=0, minute=0,
            second=0, microsecond=0) + util.chop_microseconds(sleep_starttime)
        location = self.home.location

        sleep = Activity(location, sleep_startdatetime,
                         util.chop_microseconds(sleep_duration),
                         config.SLEEP)
        self.routine.append(sleep)
        logger.info('{} *add sleep\n{}'.format(i, sleep.output_list(True)))

        # add football event
        if add_football:
            football_event = config.FOOTBALL_EVENT
            location = Point(football_event[config.LOCATION])
            startdatetime = football_event[config.STARTTIME]
            duration = football_event[config.DURATION]

            event = Activity(location, startdatetime, duration, config.SPECIAL_EVENT)
            self.routine.append(event)
            logger.info('{} *add special event\n{}'.format(i, event.output_list(True)))

    def get_nearest_essential_activity(self):
        """get the ealiest essential activity that haven't been finished"""
        list_of_essential_activity = []
        for activity in self.routine:
            if activity.starttime > self.current_time:
                list_of_essential_activity.append(activity)

        ealiest = None
        if list_of_essential_activity:
            ealiest = min(list_of_essential_activity, key=attrgetter('starttime'))

        return ealiest

    def get_last_ract_or_tran_index(self):
        list_of_ract_or_tran = []
        for activity in self.routine:
            if activity.starttime < self.current_time:
                list_of_ract_or_tran.append(activity)
        if list_of_ract_or_tran:
            return self.routine.index(
                max(list_of_ract_or_tran, key=attrgetter('starttime')))
        else:
            return None

    async def get_optimal_activity_with_tran(self, starttime, endtime, endlocation, client, i):
        """
        pick a suitable(time and location) activity then
        return activity and corresponding trans to the routine attribute
        """

        # pick only allowable(repeatable or unrepeatable but haven't done yet) activity
        activities_preference_copy = copy.deepcopy(self.activities_preference)
        # check the random activity opening time,
        # if closed then delete from the activities_preference_copy
        for key in list(activities_preference_copy):
            # print(activities_preference_copy)
            if not util.is_opening(key, starttime, endtime):
                del activities_preference_copy[key]
        while activities_preference_copy:
            item = activities_preference_copy.items()
            activity_list, corresponding_prob = zip(*item)

            sum_probability = sum(corresponding_prob)
            corresponding_prob = [i / sum_probability for i
                                  in corresponding_prob]

            activity_category = np.random.choice(activity_list, p=corresponding_prob)

            want_duration = config.RANDOM_ACTIVITY_CONFIG[config.DURATION][activity_category]

            # random samplied from k neariest points
            normalized_probs, neighbors = util.k_nearest_point(
                activity_category, self.current_location, self.character[0])

            most_likely_point = neighbors[
                np.random.choice(range(len(neighbors)), p=normalized_probs)]

            to_ract_route = await self.get_optimal_commute(
                self.current_location, most_likely_point,
                self.current_time, client, i)

            duration_to_ract = to_ract_route.duration

            allow_duration = util.max_duration(activity_category, starttime + duration_to_ract)
            # print(allow_duration)

            if allow_duration < datetime.timedelta(0):
                del activities_preference_copy[activity_category]
                continue

            activity_duration = min(want_duration, allow_duration)

            route_to_ess = await self.get_optimal_commute(
                most_likely_point, endlocation,
                self.current_time +
                duration_to_ract +
                activity_duration, client, i)
            duration_to_ess = route_to_ess.duration

            # the random activity fits in, if endtime is bigger
            if endtime > (starttime + duration_to_ract + activity_duration + duration_to_ess):
                activity_starttime = starttime + duration_to_ract
                return Activity(
                    most_likely_point, activity_starttime,
                    activity_duration, activity_category), to_ract_route
            # the activity location is too far, choose other activity
            else:
                del activities_preference_copy[activity_category]

        return None

    async def get_optimal_commute(self, startpoint, endpoint, current_time, client, i):
        """
        def get_optimal_commute(self, Point, Point, datetime.datetime)
        return the Route object
        """
        list_of_commute = []
        if self.tran_tool[config.BIKE] and \
                self.tran_tool[config.BIKE].is_available(startpoint):
            route = await self.get_route_from_motis(startpoint, endpoint,
                                                    current_time, True, client, i)
        else:
            route = await self.get_route_from_motis(startpoint, endpoint,
                                                    current_time, False, client, i)

        if route:
            list_of_commute.append(route)

        avail_tran_tool = [config.FOOT]
        unavail_tran_tool = []
        for key, val in self.tran_tool.items():
            # search only tool the person owns
            if val:
                if val.is_available(startpoint):
                    avail_tran_tool.append(key)
                else:
                    unavail_tran_tool.append(key)
        # unavail_tran_tool unfinished
        for tool in avail_tran_tool:
            route = await self.get_route_from_osrm(tool, startpoint,
                                                   endpoint, current_time, client, i)
            list_of_commute.append(route)
        for tool in unavail_tran_tool:
            route_to_tool = await self.get_route_from_osrm(
                config.FOOT, startpoint,
                self.tran_tool[tool].location, current_time, client, i)
            route_to_endpoint = await self.get_route_from_osrm(
                tool, self.tran_tool[tool].location,
                endpoint, current_time + route_to_tool.duration, client, i)

            # route_to_tool.path add element of route_to_endpoint.path
            route_to_tool.path.extend(route_to_endpoint.path)
            route_combine = Route(
                route_to_tool.path, current_time,
                route_to_tool.duration + route_to_endpoint.duration,
                config.OSRM, tool)
            list_of_commute.append(route_combine)
        return min(list_of_commute, key=attrgetter('duration'))

    async def get_route_from_motis(self, startpoint, endpoint, current_time, has_bike, client, i):
        """
        def get_route_from_motis(self, Point, Point,
                                 datetime.datetime, boolean)
        """
        if startpoint.coords[:] == endpoint.coords[:]:
            route = [list(startpoint.coords[0]), list(endpoint.coords[0])]
            return Route(route, current_time,
                         datetime.timedelta(seconds=5), config.STAY_STILL, '')
        elif util.calculate_distance(startpoint, endpoint) < 0.2:
            route = [list(startpoint.coords[0]), list(endpoint.coords[0])]
            distance = util.calculate_distance(startpoint, endpoint)
            # add one second to avoid stay still problem
            duration = datetime.timedelta(hours=distance / config.TRANSPORTATION_SPEED[config.FOOT]) + \
                       datetime.timedelta(seconds=1)
            return Route(route, current_time, util.chop_microseconds(duration),
                         config.ESTIMATE, config.FOOT)
        else:
            # the server only has a schedule for 7 days starting 29-11-2015
            shiftdays = datetime.timedelta(current_time.isoweekday() % 7)
            requesttime = datetime.datetime.combine(
                datetime.date(2015, 11, 29) + shiftdays,
                current_time.time())
            requesttime_timestamp = int(time.mktime(requesttime.timetuple()))

            # get the motis query result
            motis_request = util.gen_intermodal_routing_request(
                startpoint.y, startpoint.x, requesttime_timestamp,
                endpoint.y, endpoint.x, has_bike)

            query_starttime = datetime.datetime.now()
            result_str = await util.query_motis(motis_request, client, i)

            if not result_str:
                result_str = await util.query_motis(motis_request, client, i)

            query_endtime = datetime.datetime.now()
            self.statistics[config.STAT_MOTIS_TIME] = query_endtime - query_starttime
            self.statistics[config.STAT_MOTIS] += 1

            result_dict = json.loads(result_str)

            return self.handle_motis_result(result_dict, current_time, requesttime_timestamp, has_bike)

    def handle_motis_result(self, result_dict, current_time, requesttime_timestamp, has_bike):
        if 'connections' in result_dict['content'] and result_dict['content']['connections']:
            connections = result_dict['content']['connections']
        else:
            return None

        pseudo_arrivetime_list = []

        for connect in connections:
            pseudo_arrivetime_list.append(
                connect['stops'][-1]['arrival']['time'])
        # get the earliest connection by minimal arrival time
        ealiest_connection = connections[pseudo_arrivetime_list.index(min(pseudo_arrivetime_list))]

        stops = ealiest_connection['stops']
        transports = ealiest_connection['transports']
        trips = ealiest_connection['trips']

        pseudo_arrivetimestamp = stops[-1]['arrival']['time']

        path = []
        section = []

        for stop in stops:
            path.append([stop['station']['pos']['lng'],
                         stop['station']['pos']['lat']])

        for transport in transports:
            move = transport['move']
            move_type = transport['move_type']
            start = move['range']['from']
            end = move['range']['to']

            if move_type != 'Walk':
                name = move['name']
                trip_id = self.get_trip_id(trips, start)
            else:
                name = move_type
                trip_id = ''

            for i in range(start, end):
                lat_from = stops[i]["station"]["pos"]["lat"]
                lon_from = stops[i]["station"]["pos"]["lng"]
                startpoint = [lon_from, lat_from]

                lat_to = stops[i + 1]["station"]["pos"]["lat"]
                lon_to = stops[i + 1]["station"]["pos"]["lng"]
                direction = stops[i + 1]["station"]["name"]
                endpoint = [lon_to, lat_to]

                pseudo_depature_time = stops[i]['departure']['time']
                depature_time = current_time + \
                                datetime.timedelta(seconds=pseudo_depature_time - requesttime_timestamp)

                section.append({'startpoint': startpoint, 'endpoint': endpoint, 'd_time': depature_time, 'name': name,
                                'direction': direction, 'trip_id': trip_id})

        duration = datetime.timedelta(seconds=pseudo_arrivetimestamp - requesttime_timestamp)

        return Route(path, current_time, duration,
                     config.MOTIS_WITH_BIKE if has_bike else
                     config.MOTIS_WITHOUT_BIKE, '', section)

    async def get_route_from_osrm(self, tool, startpoint, endpoint, current_time, client, i):
        """
        def get_route_from_osrm(self, str, Point, Point, datetime.datetime)
        """
        if startpoint.coords[:] == endpoint.coords[:]:

            route = [list(startpoint.coords[0]), list(endpoint.coords[0])]
            return Route(route, current_time,
                         datetime.timedelta(seconds=5), config.STAY_STILL, '')

        elif util.calculate_distance(startpoint, endpoint) < 0.2:

            route = [list(startpoint.coords[0]), list(endpoint.coords[0])]
            # add one second to avoid stay still problem
            duration = datetime.timedelta(
                hours=util.calculate_distance(startpoint, endpoint) /
                      config.TRANSPORTATION_SPEED[config.FOOT]) + datetime.timedelta(seconds=1)

            return Route(route, current_time,
                         util.chop_microseconds(duration),
                         config.ESTIMATE, config.FOOT)
        else:
            osrm_request = util.gen_osrm_request(tool, startpoint.y,
                                                 startpoint.x, endpoint.y,
                                                 endpoint.x)
            query_starttime = datetime.datetime.now()
            result_str = await util.query_motis(osrm_request, client, i)

            if not result_str:
                result_str = await util.query_motis(osrm_request, client, i)

            query_endtime = datetime.datetime.now()
            self.statistics[config.STAT_OSRM_TIME] = query_endtime - query_starttime
            self.statistics[config.STAT_OSRM] += 1
            result_dict = json.loads(result_str)

            return self.handle_osrm_result(result_dict, osrm_request, tool, startpoint, endpoint, current_time)

    def handle_osrm_result(self, result_dict, osrm_request, tool, startpoint, endpoint, current_time):

        if 'distance' not in result_dict['content'].keys():
            logger.error(osrm_request)

        if 'time' not in result_dict['content'].keys():
            if 'distance' in result_dict['content'].keys():
                duration = datetime.timedelta(
                    hours=result_dict['content']['distance'] / 1000 /
                          config.TRANSPORTATION_SPEED[tool])
            else:
                duration = datetime.timedelta(
                    hours=util.calculate_distance(startpoint, endpoint) /
                          config.TRANSPORTATION_SPEED[tool])
        else:
            duration = datetime.timedelta(
                seconds=result_dict['content']['time'])

        path = []
        if 'polyline' not in result_dict['content'].keys():
            path.append(list(startpoint.coords[0]))
            path.append(list(endpoint.coords[0]))
        else:
            osrm_route = result_dict['content']['polyline']['coordinates']

            for i in range(len(osrm_route)):
                if i % 2 == 0:
                    path.append([osrm_route[i + 1], osrm_route[i]])
            # adding the startpoint and endpoint to the path
            path.insert(0, list(startpoint.coords[0]))
            path.append(list(endpoint.coords[0]))

        return Route(path, current_time, duration, config.OSRM, tool)

    def execute_commute_and_act(self, commute, activity, is_essential_act, i):
        """def execute_commute_and_act(Route, Activity, boolean)"""
        # execute the commute, change the current time and location
        self.current_time += commute.duration
        weekend_par = util.get_weekday(self.current_time)
        self.current_location = activity.location
        self.routine.append(commute)
        logger.info('{} *add commute\n{}'.format(i, commute.output_list(False)))

        # change location of personal transportation tool
        if commute.category == config.OSRM:
            if commute.remark in self.tran_tool.keys():
                self.tran_tool[commute.remark].location = self.current_location
                logger.info("{} change {} location\n".format(i, commute.remark))
        if commute.category == config.MOTIS_WITH_BIKE:
            self.tran_tool[config.BIKE].location = self.current_location
            logger.info("{} change {} location\n".format(i, commute.remark))

        if is_essential_act:

            # execute the essential activity
            # in advance config.WAIT_TIME minutes
            activity.execute_activity_in_advance(self.current_time)
        else:
            # execute the random activity
            # delete the random activity if not repetable and sum the prob to 1
            if activity.category != config.STANDBY and not \
                    config.RANDOM_ACTIVITY_CONFIG[config.REPEATABILITY][weekend_par][activity.category]:
                del self.activities_preference[activity.category]
            self.routine.append(activity)
            logger.info('{} *add activity\n{}'.format(i, activity.output_list(True)))
        self.current_time += activity.duration

    async def generate_routine(self, generate_days, client, i, football_event=False):
        activities_preference_copy = copy.deepcopy(self.activities_preference)

        for _ in range(generate_days):
            await self.set_essential_activities(client, i, football_event)
            # initialize the activities_preference again
            self.activities_preference = copy.deepcopy(activities_preference_copy)
            next_essential_act = self.get_nearest_essential_activity()
            repeat_routine_num = 0
            while next_essential_act:
                # function get_optimal_commute return Route from current location
                # to the location of next essential activity
                optimal_commute = await self.get_optimal_commute(
                    self.current_location,
                    next_essential_act.location,
                    self.current_time, client, i)
                # decide if direct go to do the ess_act (only remaining WAIT_TIME left)
                # or add the ract in between the essential avitivity is not reachable
                remaining_time = next_essential_act.starttime - self.current_time - optimal_commute.duration

                if remaining_time < datetime.timedelta(0):

                    if repeat_routine_num == 0 or repeat_routine_num != len(self.routine):
                        repeat_routine_num = len(self.routine)
                        logger.info('{} Try to undo1'.format(i))
                        if self.undo(i):
                            logger.info('{} optimal_coummte {}'.format(i, optimal_commute.output_list(False)))
                            pass
                        else:
                            # execute the commute and next essential activity lately
                            # next_essential_act.starttime -= remaining_time
                            logger.info('{} --execute the ess-act lately--'.format(i))
                            self.execute_commute_and_act(optimal_commute, next_essential_act, True, i)
                            next_essential_act = self.get_nearest_essential_activity()
                    else:
                        logger.info('{} Try to undo2'.format(i))
                        self.undo(i)
                        optimal_commute = await self.get_optimal_commute(
                            self.current_location,
                            next_essential_act.location,
                            self.current_time, client, i)
                        # execute the commute and next essential activity
                        logger.info('{} --execute the ess-act in advance--'.format(i))
                        self.execute_commute_and_act(optimal_commute, next_essential_act, True, i)
                        next_essential_act = self.get_nearest_essential_activity()

                # if essential activity could be executed in advance
                elif remaining_time < datetime.timedelta(seconds=config.WAIT_TIME):
                    # execute the commute and next essential activity
                    logger.info('{} --execute the ess-act in advance--'.format(i))
                    self.execute_commute_and_act(optimal_commute, next_essential_act, True, i)
                    next_essential_act = self.get_nearest_essential_activity()
                else:
                    # choose a random activity and execute
                    # get_optimal_activity_with_tran may return None if not get random activity
                    activity_and_tran = await self.get_optimal_activity_with_tran(
                        self.current_time,
                        next_essential_act.starttime,
                        next_essential_act.location, client, i)
                    # has found one ract to fit in
                    if activity_and_tran:
                        activity, route = activity_and_tran
                        # execute the commute and picked random activity
                        logger.info("{} --execute the ract--".format(i))
                        self.execute_commute_and_act(route, activity, False, i)
                        logger.info("{} num of routine:{}\n".format(i, len(self.routine)))
                    else:
                        standby_duration = min(util.chop_microseconds(remaining_time * 0.8),
                                               config.MAX_STANDBY_DURATION)

                        current_loc_list = list(self.current_location.coords[0])
                        route = Route([current_loc_list, current_loc_list], self.current_time,
                                      datetime.timedelta(seconds=5), config.STAY_STILL, '')
                        activity = Activity(self.current_location, self.current_time + datetime.timedelta(seconds=5),
                                            standby_duration, config.STANDBY)

                        # execute filled in standby activity
                        logger.info("{} --execute the ract--".format(i))
                        self.execute_commute_and_act(route, activity, False, i)
                        logger.info("{} num of routine:{}\n".format(i, len(self.routine)))
        self.cal_stat_data()
        return self.routine, self.statistics

    def cal_stat_data(self):
        self.statistics[config.STAT_PERSONTYPE] = self.person_type
        self.statistics[config.STAT_CHARACTER] = str(self.character)
        self.statistics[config.STAT_TRANTOOL] = str([k for k in self.tran_tool if self.tran_tool[k]])
        for route_or_activity in self.routine:
            if isinstance(route_or_activity, Route):
                distance = util.calculate_distance_from_path(route_or_activity.path)
                self.statistics[config.STAT_DISTANCE] = distance
                self.statistics[config.STAT_ONROAD_DURATION] += route_or_activity.duration
                if route_or_activity.category == config.MOTIS_WITH_BIKE:
                    self.statistics[config.STAT_BIKE] += 1
                    self.statistics[config.STAT_OEPNV] += 1
                elif route_or_activity.category == config.MOTIS_WITHOUT_BIKE:
                    self.statistics[config.STAT_OEPNV] += 1
                elif route_or_activity.category == config.OSRM:
                    if route_or_activity.remark == config.CAR:
                        self.statistics[config.STAT_CAR] += 1
                    elif route_or_activity.remark == config.BIKE:
                        self.statistics[config.STAT_BIKE] += 1
                    else:
                        pass
                else:
                    pass

    def undo(self, i):
        last_activity_index = self.get_last_ract_or_tran_index()
        if (not last_activity_index or self.routine[last_activity_index].category in
            [config.SLEEP, config.WORK, config.ATTEND_CLASS]):
            return False
        elif not isinstance(self.routine[last_activity_index], Activity):
            raise Exception("No last activity index\n{}".format(self.routine[last_activity_index].output_list(False)))
        else:
            # delete the last activity
            self.current_time -= self.routine[last_activity_index].duration
            logger.info('{} del {}'.format(i, self.routine[last_activity_index].output_list(True)))
            del self.routine[last_activity_index]
            # delete the last route
            last_route_index = self.get_last_ract_or_tran_index()
            last_route = self.routine[last_route_index]

            if not isinstance(last_route, Route):
                raise Exception("No last route index\n{}".format(last_route.output_list(False)))
            else:
                # undo the car or bike location
                if last_route.category == config.MOTIS_WITH_BIKE:
                    self.tran_tool[config.BIKE].location = Point(
                        last_route.path[0])
                if last_route.category == config.OSRM and last_route.remark != config.FOOT:
                    if last_route.remark == config.CAR:
                        self.tran_tool[config.CAR].location = Point(
                            last_route.path[0])
                    else:
                        self.tran_tool[config.BIKE].location = Point(
                            last_route.path[0])
                self.current_time -= last_route.duration
                # set the person location to the second last activity location
                self.current_location = Point(last_route.path[0])
                logger.info('{} last_loc:{}'.format(i, last_route.path[0]))
                logger.info('{} del {}'.format(i, self.routine[last_route_index].output_list(False)))
                del self.routine[last_route_index]
            logger.info("{} undo one step".format(i))
            logger.info("{} num of routine:{}\n".format(i, len(self.routine)))
            return True

    @staticmethod
    def get_trip_id(trips, range_from):

        trip_id = None
        for trip in trips:
            if trip["range"]["from"] == range_from:
                trip_id = trip["id"]

        return trip_id
