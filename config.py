"""
Created on Sat Dec 10 11:09:31 2016

@author: martin
"""
import datetime
import os.path
from datetime import timedelta

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# random activity type
RECREATION = 'hangout'
COMMERCIAL = 'shopping'
SELFSTUDY = 'selfstudy'
STANDBY = 'standby'

# essential activity type
SLEEP = 'sleep'
WORK = 'work'
ATTEND_CLASS = 'attend_class'
SPECIAL_EVENT = 'special_event'
LOCATION = 'location'

# activity attribute
STARTTIME = 'starttime'
DURATION = 'duration'
REPEATABILITY = 'repeatability'
OPENING_TIME = 'opening_time'

# person type
STUDENT = 'student'
EMPLOYEE = 'employee'

# person character
COMFORTABLE = 'comfortable'
ACTIVE = 'active'
INTROVERTED = 'introverted'
EXTROVERTRD = 'extroverted'
LONGSLEEPER = 'longsleeper'
EARLYRISER = 'earlyriser'

# transport tool
CAR = 'car'
FOOT = 'foot'
BUS = 'bus'
BIKE = 'bike'

# commit type
OSRM = 'osrm'
MOTIS_WITH_BIKE = 'motis_with_bike'
MOTIS_WITHOUT_BIKE = 'motis'
ESTIMATE = 'estimate'
STAY_STILL = 'stay still'

STAT_PERSONTYPE = 'person type'
STAT_CHARACTER = 'character'
STAT_TRANTOOL = 'transportation tool'
STAT_DISTANCE = 'distance'
STAT_ONROAD_DURATION = 'on load duration'
STAT_BIKE = 'bike usage'
STAT_CAR = 'car usage'
STAT_OEPNV = 'public transport usage'
STAT_MOTIS = 'motis usage'
STAT_OSRM = 'osrm usage'
STAT_MOTIS_TIME = 'motis query time'
STAT_OSRM_TIME = 'osrm usage time'

# weekend setting
WEEKEND = 'weekend'
WORKDAY = 'workday'

# the default database to write in and visualize
DATABASE_FILE = "output/transportation_football.sqlite"

DATABASE_NORMAL = "output/transportation_normal.sqlite"
DATABASE_WEEKEND = "output/transportation_weekend.sqlite"
DATABASE_FOOTBALL = "output/transportation_football.sqlite"

CREATE_PERSON_TABLE_SQL = """ CREATE TABLE IF NOT EXISTS persons (
                                        id integer PRIMARY KEY,
                                        person_type text NOT NULL,
                                        characteristic text NOT NULL,
                                        car_usage text NOT NULL,
                                        bicycle_usage text NOT NULL,
                                        public_transport_usage text NOT NULL,
                                        transportation_tool text NOT NULL,
                                        distance text NOT NULL,
                                        onroad_duration text NOT NULL,
                                        osrm_usage text NOT NULL,
                                        motis_usage text NOT NULL,
                                        osrm_query_time text NOT NULL,
                                        motis_query_time text NOT NULL
                                        ); """
CREATE_ROUTINE_TABLE_SQL = """ CREATE TABLE IF NOT EXISTS routines(
                                        id integer PRIMARY KEY,
                                        activity_type text NOT NULL,
                                        person_id integer NOT NULL,
                                        remark text,
                                        start_time text NOT NULL,
                                        finish_time text NOT NULL,
                                        duration text NOT NULL,
                                        list_of_coordinate text NOT NULL,
                                        FOREIGN KEY (person_id) REFERENCES persons (id)
                                        );"""
CREATE_SECTION_TABLE_SQL = """CREATE TABLE IF NOT EXISTS sections (
                                        id integer PRIMARY KEY,
                                        startpoint text NOT NULL,
                                        endpoint text NOT NULL,
                                        d_time text,
                                        direction text,
                                        name text NOT NULL,
                                        trip_id text NOT NULL,
                                        routine_id integer NOT NULL,
                                        FOREIGN KEY (routine_id) REFERENCES routines(id)
                                        );"""
INSERT_PERSON_SQL = """ INSERT INTO persons(person_type, characteristic, car_usage, bicycle_usage,
                        public_transport_usage, transportation_tool, distance, onroad_duration,
                        osrm_usage, motis_usage, osrm_query_time, motis_query_time)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"""

INSERT_ROUTINE_SQL = """ INSERT INTO routines(activity_type, person_id, remark, start_time,
                         finish_time, duration, list_of_coordinate)
                         VALUES(?,?,?,?,?,?,?) """

INSERT_SECTION_SQL = """ INSERT INTO sections(startpoint, endpoint, d_time, direction, name, trip_id, routine_id)
                         VALUES(?,?,?,?,?,?,?) """

QUERY_WIDTH_SQL = """SELECT startpoint, endpoint, COUNT(id)
                     FROM sections
                     GROUP BY startpoint, endpoint"""

QUERY_RELATED_LINE_SQL = """SELECT startpoint, endpoint
                            FROM sections
                            where routine_id IN
                                (SELECT routine_id
                                FROM sections
                                WHERE (startpoint=:startpoint and endpoint=:endpoint) or
                                (endpoint=:startpoint and startpoint=:endpoint))
                            GROUP BY startpoint, endpoint"""

QUERY_SELECTED_LINE_SQL = """SELECT d_time, direction, name, routine_id
                             FROM sections
                             WHERE (startpoint=:startpoint and endpoint=:endpoint) or
                             (endpoint=:startpoint and startpoint=:endpoint)
                             ORDER BY name"""

QUERY_RID_LINE_SQL = """SELECT startpoint, endpoint
                        FROM sections
                        WHERE routine_id =?
                        GROUP BY startpoint, endpoint"""

QUERY_AMENITY_SQL = """SELECT list_of_coordinate
                       FROM routines
                       WHERE activity_type = ?
                       GROUP BY list_of_coordinate"""

CREATE_INDEX_SQL = """CREATE INDEX routine_index ON sections (routine_id);
                      CREATE INDEX startend_index ON sections (startpoint, endpoint);
                      CREATE INDEX routinetype_index ON routines (activity_type)"""

DROP_INDEX_SQL = """DROP INDEX IF EXISTS routine_index;
                    DROP INDEX IF EXISTS startend_index;
                    DROP INDEX IF EXISTS routinetype_index"""

EVALUATION_SQL = """SELECT motis_query_time, osrm_query_time, motis_usage, osrm_usage, onroad_duration,
                    distance, car_usage, bicycle_usage, public_transport_usage
                    FROM persons"""

# no need to sum to 1
PERSONTYPE_ACTIVITY_CONFIG = {
    STUDENT: {
        RECREATION: 1.3,
        COMMERCIAL: 0.3,
        SELFSTUDY: 3.0
    },
    EMPLOYEE: {
        RECREATION: 1.5,
        COMMERCIAL: 1.5,
        SELFSTUDY: 0.5
    }
}

CHARACTER_ACTIVITY_CONFIG = {
    COMFORTABLE: {
        RECREATION: 0.8,
        COMMERCIAL: 0.2,
        SELFSTUDY: 1
    },
    ACTIVE: {
        RECREATION: 1.4,
        COMMERCIAL: 1.3,
        SELFSTUDY: 1
    },
    INTROVERTED: {
        RECREATION: 0.2,
        COMMERCIAL: 0.4,
        SELFSTUDY: 1.3
    },
    EXTROVERTRD: {
        RECREATION: 2.0,
        COMMERCIAL: 1.5,
        SELFSTUDY: 1
    },
    LONGSLEEPER: {
        RECREATION: 1.6,
        COMMERCIAL: 1.1,
        SELFSTUDY: 0.4
    },
    EARLYRISER: {
        RECREATION: 1.2,
        COMMERCIAL: 1.4,
        SELFSTUDY: 1.5
    }
}

TOOL_PROBABILITY_CONFIG = {
    STUDENT: {
        CAR: [0.1, 0.9],
        BIKE: [0.7, 0.3]
    },
    EMPLOYEE: {
        CAR: [0.8, 0.2],
        BIKE: [0.4, 0.6]
    }
}
RANDOM_ACTIVITY_CONFIG = {
    DURATION: {
        RECREATION: timedelta(hours=1, minutes=30),
        COMMERCIAL: timedelta(minutes=20),
        SELFSTUDY: timedelta(hours=2)
    },
    REPEATABILITY: {
        WORKDAY: {
            RECREATION: False,
            COMMERCIAL: True,
            SELFSTUDY: True
        },
        WEEKEND: {
            RECREATION: True,
            COMMERCIAL: True,
            SELFSTUDY: True
        }
    },
    OPENING_TIME: {
        RECREATION: {
            1: [timedelta(hours=9), timedelta(hours=22)],
            2: [timedelta(hours=9), timedelta(hours=22)],
            3: [timedelta(hours=9), timedelta(hours=22)],
            4: [timedelta(hours=9), timedelta(hours=22)],
            5: [timedelta(hours=9), timedelta(hours=22)],
            6: [timedelta(hours=10), timedelta(hours=20)],
            7: [timedelta(hours=10), timedelta(hours=20)]
        },
        COMMERCIAL: {
            1: [timedelta(hours=8), timedelta(hours=21)],
            2: [timedelta(hours=8), timedelta(hours=21)],
            3: [timedelta(hours=8), timedelta(hours=21)],
            4: [timedelta(hours=8), timedelta(hours=21)],
            5: [timedelta(hours=8), timedelta(hours=21)],
            6: [timedelta(hours=8), timedelta(hours=21)],
            7: [timedelta(hours=0), timedelta(hours=0)]
        },
        SELFSTUDY: {
            1: [timedelta(hours=8), timedelta(hours=22)],
            2: [timedelta(hours=8), timedelta(hours=22)],
            3: [timedelta(hours=8), timedelta(hours=22)],
            4: [timedelta(hours=8), timedelta(hours=22)],
            5: [timedelta(hours=8), timedelta(hours=22)],
            6: [timedelta(hours=8), timedelta(hours=22)],
            7: [timedelta(hours=0), timedelta(hours=0)]
        }
    }
}

"""
sleep duration seen as normal distribution containing (mu, sigma)
references:
https://www.freelapusa.com/sleep-and-the-athlete-time-to-wake-up-to-the-need-for-sleep/
http://www.bls.gov/tus/charts/students.html
http://www.bls.gov/tus/charts/

sleep starttime seen as normal distribution
references:
http://www.sleepcouncil.org.uk/wp-content/uploads/2013/02/The-Great-British-Bedtime-Report.pdf
https://jawbone.com/blog/university-students-sleep/
"""
ESSENTIAL_ACTIVITY_CONFIG = {
    SLEEP: {
        WEEKEND: {
            STARTTIME: {
                ACTIVE: {
                    STUDENT: [24, 0.5],
                    EMPLOYEE: [24, 0.5]
                },
                COMFORTABLE: {
                    STUDENT: [25, 1.2],
                    EMPLOYEE: [25, 1.2]
                }
            },
            DURATION: {
                LONGSLEEPER: [10, 0.8],
                EARLYRISER: [9, 0.6]
            }
        },
        WORKDAY: {
            STARTTIME: {
                ACTIVE: {
                    STUDENT: [24, 0.5],
                    EMPLOYEE: [22, 0.5]
                },
                COMFORTABLE: {
                    STUDENT: [25, 1.2],
                    EMPLOYEE: [23, 1.2]
                }
            },
            DURATION: {
                LONGSLEEPER: [9, 0.8],
                EARLYRISER: [6.7, 0.6]
            }
        }

    },
    WORK: {  # STARTTIME:[mushift, sigma]
        STARTTIME: [1800, 1800],
        DURATION: timedelta(hours=8)
    },
    ATTEND_CLASS: [
        {  # STARTTIME:[mushift, sigma]
            STARTTIME: [1800, 2700],
            DURATION: timedelta(hours=1, minutes=40)
        },
        {  # STARTTIME:[mushift, sigma]
            STARTTIME: [600, 1000],
            DURATION: timedelta(hours=1, minutes=40)
        }]
}

# unit is km/h
TRANSPORTATION_SPEED = {
    CAR: 70,
    FOOT: 5,
    BUS: 50,
    BIKE: 15
}

SHOP_FILE = 'output/shops.geojson'
LEISURE_FILE = 'output/leisure.geojson'
UNI_FILE = 'output/uni.geojson'
COMPANY_FILE = 'output/company.geojson'
CSV_COMPANY_FILE = "data/companies.hessen.csv"

# zensus file config
MIN_POPULATION = 30
ZENSUS_FILE = "data/Zensus_Bevoelkerung_100m-Gitter.csv"

# bounding box for residential area (50km from darmstadt)
DARMSTADT_BOUND_LEFT_DOWN = [7.945366, 49.415996]
DARMSTADT_BOUND_RIGHT_UP = [9.348364, 50.319179]

QUERY_TIME = 0
NUM_OF_NEXT_RACT_SAMPLED_LOCATIONS = 20

# unit is second
WAIT_TIME = 30 * 60
MAX_STANDBY_DURATION = timedelta(hours=3)

EARTH_RADIUS = 6378137.0

# actual routine day starts one day after
START_DATETIME = datetime.datetime(2017, 3, 31, 0, 0, 0)

# maximum person in the aio queue
MAX_GENERATE_PERSON = 15

FOOTBALL_EVENT = {
    STARTTIME: datetime.datetime(2017, 4, 1, 15, 30, 0),
    DURATION: timedelta(minutes=105),
    LOCATION: [8.672375, 49.857705]
}
