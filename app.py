import json
import math
import os
import re
import urllib
import warnings
from datetime import date
from datetime import datetime
from datetime import timedelta
from itertools import repeat

import pytz
import requests
from colour import Color
from flask import Flask
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask_assets import Bundle
from flask_assets import Environment
from flask_babel import _
from flask_babel import Babel
from flask_babel import format_date

app = Flask(__name__, static_url_path="")
assets = Environment(app)

js = Bundle(
    "scripts/active_hour_scroll.js",
    "scripts/location_autocomplete.js",
    "scripts/pull_to_refresh.js",
    # filters="jsmin",
    output="gen/packed.js",
)
css = Bundle(
    "fonts/plex.css",
    "styles/chota.min.css",
    "styles/velo-weather.css",
    # filters="cssmin",
    output="gen/packed.css",
)
assets.register("js_all", js)
assets.register("css_all", css)


app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"
app.config["LANGUAGES"] = {"en": "English", "fr": "Français"}

app.secret_key = os.getenv("SECRET_KEY")

babel = Babel(app)


# ----------
# APP CONFIG
# ----------

# top of the scale for wind, kph
MAX_WIND_ACCEPTABLE = 35

# top of the scale for rain, mm per hour
# 7.6mm per hour and more is "heavy rain"
MAX_RAIN_ACCEPTABLE = 7.6
# alert level for rain, mm per hour
PRECIP_ALERT = MAX_RAIN_ACCEPTABLE * 2

# top and bottom of the temp scale, in °C
MIN_TEMP_ACCEPTABLE = -5
MAX_TEMP_ACCEPTABLE = 35

# top probability score, the worst weather
MAX_PROBA_VALUE = 20

# wind character
WIND_CHAR = "💨"

# ideal temps
IDEAL_TEMPS = (13, 19)

# history days
HISTORY_DAYS = 5

# scale of hours of the day
MIN_HOUR = 7
MAX_HOUR = 20

azimuths = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]

azimuths_range = range(len(azimuths) + 1)

azimuth_angles = [i * 360 / len(azimuths) for i in azimuths_range]


# -----------
# PAGE RENDER
# -----------


@app.route("/", methods=["POST", "GET"])
def index():
    latitude = get_property_from_args_or_session("latitude", "48.86415")
    longitude = get_property_from_args_or_session("longitude", "2.44322")
    location = get_property_from_args_or_session(
        "location", "Montreuil, Île-de-France (France)"
    )
    use_relative_temps = get_property_from_args_or_session("use_relative_temps", 0)
    use_relative_temps = bool(int(use_relative_temps))

    weather_params = (
        ("latitude", latitude),
        ("longitude", longitude),
        (
            "hourly",
            "temperature_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,winddirection_10m,windgusts_10m",
        ),
        (
            "daily",
            "weathercode,sunrise,sunset,apparent_temperature_max,apparent_temperature_min",
        ),
        ("timezone", "auto"),
        ("current_weather", "true"),
    )

    air_quality_params = (
        ("latitude", latitude),
        ("longitude", longitude),
        (
            "hourly",
            "pm10,nitrogen_dioxide,sulphur_dioxide,ozone,alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen",
        ),
        ("timezone", "auto"),
    )

    weather_data = get_api_data("forecast", weather_params)
    aqi_data = get_api_data("air-quality", air_quality_params)

    ideal_temps = (
        get_relative_temps(weather_data) if use_relative_temps else IDEAL_TEMPS
    )

    if weather_data:
        (serialized_weather, current_weather) = serialize_data(
            weather_data, aqi_data, ideal_temps
        )
        timezone = weather_data["timezone"]
    else:
        (serialized_weather, current_weather, timezone) = ({}, {}, None)

    return render_template(
        "index.html",
        data=serialized_weather,
        timezone=timezone,
        location=location,
        current_weather=current_weather,
        max_rain=MAX_RAIN_ACCEPTABLE,
        max_wind=MAX_WIND_ACCEPTABLE,
        languages=app.config["LANGUAGES"],
        ideal_temps=ideal_temps,
        default_ideal_temps=IDEAL_TEMPS,
        extreme_temps=(MIN_TEMP_ACCEPTABLE, MAX_TEMP_ACCEPTABLE),
        use_relative_temps=use_relative_temps,
    )


@app.route("/location")
def location():
    """location query endpoint"""
    search_term = request.args.get("search", None)

    location_params = (("name", search_term), ("language", get_locale()))

    location_data = get_api_data("location", location_params)

    return location_data


# ----------------
# HELPERS
# ----------------


def get_api_data(api_name, params):
    """returns data from API"""

    api_endpoints = {
        "forecast": "api.open-meteo.com/v1/forecast",
        "history": "archive-api.open-meteo.com/v1/era5",
        "air-quality": "air-quality-api.open-meteo.com/v1/air-quality",
        "location": "geocoding-api.open-meteo.com/v1/search",
    }

    data = None

    encoded_params = urllib.parse.urlencode(params, safe=",")

    response = requests.get(f"https://{api_endpoints[api_name]}?{encoded_params}")

    # 400
    if response.status_code != 400:
        response.raise_for_status()
        data = response.json()

    return data


def get_property_from_args_or_session(prop_name, default):
    """set value from args to session or retrieve value from session
    if no args, then return value"""

    if request.method == "POST":
        prop_value = request.form.get(prop_name, None)
    else:
        prop_value = request.args.get(prop_name, None)

    if prop_value:
        session[prop_name] = prop_value
    else:
        if session.get(prop_name, None):
            prop_value = session.get(prop_name)
        else:
            prop_value = default

    return prop_value


def serialize_data(weather_data, air_quality_data, ideal_temps):
    """Switches the dimension of the table and populate with goodies"""

    tz = pytz.timezone(weather_data["timezone"])
    now = datetime.now(tz)

    serialized = []
    current_weather = {}

    daily_properties = list(weather_data["daily"].keys())
    daily_properties.remove("time")

    hourly_properties = list(weather_data["hourly"].keys())
    hourly_properties.remove("time")

    aqi_properties = list(air_quality_data["hourly"].keys())
    aqi_properties.remove("time")

    # Day loop
    for (day_index, day) in enumerate(weather_data["daily"]["time"]):
        day_object = date.fromisoformat(day)

        serialized_day = {}

        for day_prop in daily_properties:
            serialized_day[day_prop] = weather_data["daily"][day_prop][day_index]

        serialized_day["feelslike_emoji"] = feelslike_emoji(serialized_day)

        try:
            sunrise_object = datetime.fromisoformat(
                weather_data["daily"]["sunrise"][day_index]
            )
        except:
            sunrise_object = 0
            warnings.warn("Wrong date format for sunrise data.")

        try:
            sunset_object = datetime.fromisoformat(
                weather_data["daily"]["sunset"][day_index]
            )
        except:
            sunset_object = 0
            warnings.warn("Wrong date format for sunset data.")

        serialized_day = serialized_day | get_condition_properties(serialized_day)

        serialized_day["date"] = get_day(day_object)
        serialized_day["hour"] = []

        # Hour loop
        for (hour_index, hour) in enumerate(weather_data["hourly"]["time"]):

            # Early return check if "2022-11-04" in "2022-11-04T05:43"
            if not hour.startswith(day):
                continue

            hour_object = datetime.fromisoformat(hour)

            serialized_hour = {}
            serialized_aqi = {}

            for hour_prop in hourly_properties:
                serialized_hour[hour_prop] = weather_data["hourly"][hour_prop][
                    hour_index
                ]

            for aqi_prop in aqi_properties:
                if not hour in air_quality_data["hourly"]["time"]:
                    continue

                serialized_aqi[aqi_prop] = air_quality_data["hourly"][aqi_prop][
                    hour_index
                ]

            serialized_hour = serialized_hour | get_aqi_properties(serialized_aqi)

            serialized_hour["is_day"] = False
            if sunrise_object != 0 and sunset_object != 0:
                if sunrise_object <= hour_object <= sunset_object:
                    serialized_hour["is_day"] = True
            else:
                serialized_hour["is_day"] = True

            serialized_hour = serialized_hour | get_condition_properties(
                serialized_hour
            )
            serialized_hour = serialized_hour | get_proba_properties(serialized_hour)
            serialized_hour = serialized_hour | get_wind_azimuth_properties(
                serialized_hour["winddirection_10m"]
            )
            serialized_hour = serialized_hour | get_precipitation_properties(
                serialized_hour["precipitation"]
            )

            temperature_color_properties = {
                "temperature_2m_color": temperature_color(
                    serialized_hour["temperature_2m"], ideal_temps
                ),
                "apparent_temperature_color": temperature_color(
                    serialized_hour["apparent_temperature"], ideal_temps
                ),
            }
            serialized_hour = serialized_hour | temperature_color_properties

            wind_properties = {
                "windgusts_notice": wind_notice(serialized_hour["windgusts_10m"]),
                "windspeed_notice": wind_notice(serialized_hour["windspeed_10m"]),
            }
            serialized_hour = serialized_hour | wind_properties

            if weather_data["current_weather"]["time"] == hour:
                current_weather = serialized_hour

            if MIN_HOUR <= hour_object.hour <= MAX_HOUR:
                serialized_hour["hour"] = hour_object.hour

                serialized_hour["past"] = False
                if hour_object.hour < now.hour and hour_object.day == now.day:
                    serialized_hour["past"] = True

                serialized_hour["classes"] = get_classes(
                    serialized_hour, weather_data["timezone"]
                )

                serialized_day["hour"].append(serialized_hour)

        if now.hour <= MAX_HOUR or day_object != now.date():
            serialized.append(serialized_day)

    return (serialized, current_weather)


def gradient(value, max, start=(0, 0.8, 1), end=(0, 0.8, 0.5)):
    """With a value from 0 to max, generate the correct gradient"""
    value = int(value)
    c1 = Color(hsl=start)
    c2 = Color(hsl=end)
    gradient = list(c1.range_to(c2, max + 1))
    value = value if value < max else max
    return gradient[int(value)].hex


def wind_notice(windspeed):
    """Repeats a character depending on the force of the wind"""
    return "".join(
        repeat(
            WIND_CHAR, (round(windspeed / 10)) if windspeed < MAX_WIND_ACCEPTABLE else 4
        )
    )


def feelslike_emoji(day):
    """Display emoji depending on the average day temperature"""
    emoji = ["🥶", "😨", "🙂", "😊", "🥵"]

    day_average = (
        day["apparent_temperature_max"] + day["apparent_temperature_min"]
    ) / 2
    if day_average <= MIN_TEMP_ACCEPTABLE:
        return emoji[0]

    if day_average > MAX_TEMP_ACCEPTABLE:
        return emoji[-1]

    temps_range = MAX_TEMP_ACCEPTABLE - MIN_TEMP_ACCEPTABLE
    d = temps_range / (len(emoji) + 1)

    emojo = emoji[math.floor(abs(day_average) / d)]

    return emojo


def temperature_color(temp, ideal_temps):
    """Handle gradient for temp around ideal temp"""

    # keep temp between acceptable range
    temp = min(max(temp, MIN_TEMP_ACCEPTABLE), MAX_TEMP_ACCEPTABLE)

    gradient = []

    ideal_min, ideal_max = ideal_temps

    if ideal_min < MIN_TEMP_ACCEPTABLE:
        ideal_min = MIN_TEMP_ACCEPTABLE

    if ideal_max > MAX_TEMP_ACCEPTABLE:
        ideal_max = MAX_TEMP_ACCEPTABLE

    for temperature in range(ideal_min - MIN_TEMP_ACCEPTABLE):
        temp_luminance = 50 + (50 / (ideal_min - MIN_TEMP_ACCEPTABLE)) * temperature
        gradient.append("hsl(220,100%,{}%)".format(round(temp_luminance)))

    for temperature in range(ideal_max - ideal_min):
        gradient.append("hsl(220,100%,100%)")

    for temperature in range(MAX_TEMP_ACCEPTABLE - ideal_max + 1):
        temp_luminance = (
            100 - (50 / (MAX_TEMP_ACCEPTABLE - ideal_max + 1)) * temperature
        )
        gradient.append("hsl(22,100%,{}%)".format(round(temp_luminance)))

    gradient.append("hsl(22,100%,50%)")

    return gradient[round(temp) - MIN_TEMP_ACCEPTABLE]


def air_quality_translation(index):
    """Returns a translated term, from an index / 10"""

    terms = [
        _("No data"),
        _("Very good"),
        _("Very good"),
        _("Good"),
        _("Good"),
        _("Average"),
        _("Below average"),
        _("Below average"),
        _("Bad"),
        _("Bad"),
        _("Very bad"),
    ]

    return terms[index]


def air_quality_gradient(index):
    """Returns a hex color on a gradient, from an index / 10"""
    return gradient(index, 10, start=(0.4, 0.8, 0.5)) if index > 0 else "#fff"


def get_relative_temps(data):
    """return a (min, max) tuple of last week's daily temp average"""

    if data is None:
        return IDEAL_TEMPS

    timezone = data["timezone"]
    tz = pytz.timezone(timezone)
    yesterday = datetime.now(tz) - timedelta(days=1)

    temps = []

    date = yesterday - timedelta(days=HISTORY_DAYS)
    params = (
        ("latitude", data["latitude"]),
        ("longitude", data["longitude"]),
        ("daily", "temperature_2m_max,temperature_2m_min"),
        ("start_date", date.strftime("%Y-%m-%d")),
        ("end_date", yesterday.strftime("%Y-%m-%d")),
        ("timezone", "auto"),
    )
    history_data = get_api_data("forecast", params)

    for i in range(HISTORY_DAYS):
        temps.append(
            (
                history_data["daily"]["temperature_2m_max"][i]
                + history_data["daily"]["temperature_2m_min"][i]
            )
            / 2
        )

    ideal_min, ideal_max = IDEAL_TEMPS

    ideal = (
        max(MIN_TEMP_ACCEPTABLE, min(ideal_min, math.floor(max(temps)))),
        min(MAX_TEMP_ACCEPTABLE, max(ideal_max, math.ceil(min(temps)))),
    )

    return ideal


def get_day(d, format="%A %d %b"):
    """Use Babel to localize a date from date object with language-specific format"""
    localized_format = _("EEEE, MMMM d")

    return format_date(date=d, format=localized_format)


def get_aqi_properties(air_quality):
    """
    Returns an index for the air quality based on PM10, NO2, SO2, O3
    Based on http://www.atmo-alsace.net/site/Explications-sur-le-calcul-des-indices-22.html
    """
    scales = {
        "pm10": [0, 10, 20, 30, 40, 50, 65, 80, 100, 125],
        "sulphur_dioxide": [0, 40, 80, 120, 160, 200, 250, 300, 400, 500],
        "nitrogen_dioxide": [0, 30, 55, 85, 110, 135, 165, 200, 275, 400],
        "ozone": [0, 30, 55, 80, 105, 130, 150, 180, 210, 240],
    }

    aq_indexes = []
    for scale in scales.keys():
        if scale not in air_quality or not air_quality[scale]:
            continue
        scale_index = min([v for v in scales[scale] if v >= air_quality[scale]] or [0])
        aq_indexes.append(scales[scale].index(scale_index) + 1)

    if len(aq_indexes) > 0:
        index = max(aq_indexes)
    else:
        return {}

    return {
        "air_quality_index": index,
        "air_quality_translation": air_quality_translation(index),
        "air_quality_gradient": air_quality_gradient(index),
    }


def get_closest_azimuth(angle):
    """Converts an angle to an azimuth code"""

    closest_azimuth = min(azimuths_range, key=lambda i: abs(azimuth_angles[i] - angle))

    return closest_azimuth % len(azimuths)


def get_classes(hour, timezone):
    """Return CSS classes for the cell, based on the current hour"""
    classes = ["cell_day"] if hour["is_day"] else ["cell_night"]

    if hour["past"]:
        classes.append("cell_past")

    return " ".join(classes)


def get_proba_properties(hour):
    """Compute a probability and output percentage"""
    # chance = round(int(hour["chance_of_rain"]) / (100 / 3))
    precip = min(hour["precipitation"], MAX_RAIN_ACCEPTABLE)
    wind = min(hour["windspeed_10m"], MAX_WIND_ACCEPTABLE)
    temp = hour["temperature_2m"]
    feelslike = hour["apparent_temperature"]
    aqi = hour.get("air_quality_index", 0)

    proba = 0

    # rain is annoying (0-3 chance + 0-10 precip mm)
    # proba += chance
    proba += aqi / 2
    proba += 12 * precip / MAX_RAIN_ACCEPTABLE
    # wind is twice as annoying (0-20)
    proba += 20 * wind / MAX_WIND_ACCEPTABLE

    if temp < 0 and precip > 0:
        # precipitations and cold cause ice on the road
        proba += 10

    if feelslike <= MIN_TEMP_ACCEPTABLE:
        # temperatures below -5 feel worse (5-10)
        proba += abs(max(MIN_TEMP_ACCEPTABLE - 5, feelslike))

    if feelslike >= MAX_TEMP_ACCEPTABLE:
        # temperatures above 35 feel worse (5-10)
        proba += min(MAX_TEMP_ACCEPTABLE + 5, feelslike) - (MAX_TEMP_ACCEPTABLE - 5)

    if not hour["is_day"]:
        # rain is more dangerous by night (0-5)
        proba += 5 * precip / MAX_RAIN_ACCEPTABLE

    proba = round(proba)

    # Probability gradient color
    start_color = (0.4, 0.8, 0.5)
    end_color = (0, 0.8, 0.6)

    proba_gradient = gradient(
        min(proba, MAX_PROBA_VALUE),
        max=MAX_PROBA_VALUE,
        start=start_color,
        end=end_color,
    )

    return {"proba_value": proba, "proba_gradient": proba_gradient}


def get_condition_properties(hour_object):
    """Translate weather condition from code"""

    # conditions list from https://www.weatherapi.com/docs/#weather-icons
    c_file = open("translations/conditions.json")
    c_data = json.loads(c_file.read())

    condition = c_data[str(hour_object["weathercode"])]

    period = "day"
    if "is_day" in hour_object and not hour_object["is_day"]:
        period = "night"

    if get_locale() in condition["languages"]:
        localized_condition_text = condition["languages"][get_locale()][
            f"{period}_text"
        ]
    else:
        localized_condition_text = condition[period]

    return {
        "condition_text": localized_condition_text,
        "condition_icon": f"images/icons/{period}/{condition['icon']}.png",
    }


def get_wind_azimuth_properties(angle):
    """Translate azimuth from angle"""

    code = azimuths[get_closest_azimuth(angle)]

    a_file = open("translations/azimuths.json")
    a_data = json.loads(a_file.read())

    azimuth = a_data[code].get(get_locale(), code)

    return {
        "wind_azimuth_abbr": azimuth[0],
        "wind_azimuth_full": azimuth[1],
    }


def get_precipitation_properties(precipitation):
    """Handle color and percentage properties for precipitation_mm"""
    precipitation = precipitation + 1 if precipitation > 0 else precipitation
    precipitation = min(precipitation, MAX_RAIN_ACCEPTABLE)
    percentage = (precipitation / MAX_RAIN_ACCEPTABLE) * 100

    color = "#000" if precipitation >= PRECIP_ALERT else "hsl(210, 80%, 50%)"

    return {
        "precip_percent": percentage,
        "precip_gradient": color,
    }


# -------------
# TEMPLATE TAGS
# -------------


@babel.localeselector
def get_locale():
    if request.args.get("lang"):
        session["lang"] = request.args.get("lang")
    else:
        if not "lang" in session:
            session["lang"] = request.accept_languages.best_match(
                app.config["LANGUAGES"].keys()
            )
    return session.get("lang", "en")


app.jinja_env.globals["get_locale"] = get_locale


def get_asset_url(asset_path):
    """Returns a full asset URL from path"""

    domain = request.host_url
    domain = domain[:-1] if domain[:-1] == "/" else domain

    return "%s%s" % (domain, url_for("static", filename=asset_path))


app.jinja_env.globals["get_asset_url"] = get_asset_url
