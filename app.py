import os

from datetime import date, datetime, timedelta
import pytz

import json
import requests
from colour import Color
from itertools import repeat

from flask import Flask, render_template, request, session, url_for
from flask_babel import Babel, format_date, _

from flask_assets import Environment, Bundle

app = Flask(__name__, static_url_path='')
assets = Environment(app)

js = Bundle('scripts/active_hour_scroll.js', 'scripts/location_autocomplete.js',
            filters='jsmin', output='gen/packed.js')
css = Bundle('styles/chota.min.css', 'styles/velo-weather.css', 'fonts/plex.css',
            filters='cssmin', output='gen/packed.css')
assets.register('js_all', js)
assets.register('css_all', css)


app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = {'en': 'English', 'fr': 'Français'}

app.secret_key = os.getenv('SECRET_KEY')

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

# scale of hours of the day
MIN_HOUR = 7
MAX_HOUR = 20


# -----------
# PAGE RENDER
# -----------

@app.route("/")
def index():
    data = None
    q = request.args.get("location", None)

    if q:
        session['location'] = q
    else:
        if session.get("location", None):
            q = session.get("location")
        else:
            q = "Montreuil, France"

    api_key = os.getenv("WEATHER_API_KEY")
    r = requests.get(f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={q}&days=10&aqi=yes&alerts=no")
    # probably location unknow
    if r.status_code != 400:
        r.raise_for_status()
        data = r.json()
    return render_template("index.html",
                            data=data,
                            max_rain=MAX_RAIN_ACCEPTABLE,
                            max_wind=MAX_WIND_ACCEPTABLE,
                            languages=app.config['LANGUAGES'])


# ----------------
# TEMPLATE FILTERS
# ----------------

@app.template_filter("valid_day")
def valid_day(value, timezone="Europe/Paris"):
    """Only return valid day objects"""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    if value:
        for item in value:
            d = date.fromisoformat(item["date"])
            if now.day != d.day:
                yield item
            else:
                if now.hour < MAX_HOUR:
                    yield item


@app.template_filter("valid_hour")
def valid_hour(value):
    """Only return valid hour objects"""
    if value:
        for item in value:
            hour = int(item["time"].split(' ')[-1].split(':')[0])
            if hour <= MAX_HOUR and hour >= MIN_HOUR:
                yield item


@app.template_filter("get_classes")
def get_classes(hour, timezone):
    """Return CSS classes for the cell, based on the current hour"""
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    cell_datetime = datetime.fromtimestamp(hour["time_epoch"], tz=tz)

    classes = ["cell_day"] if hour["is_day"] else ["cell_night"]

    if cell_datetime < now - timedelta(hours=1):
        classes.append("cell_past")

    return " ".join(classes)


@app.template_filter("gradient")
def gradient(value, max, start=(0, .8, 1), end=(0,.8,.5)):
    """With a value from 0 to max, generate the correct gradient"""
    value = int(value)
    c1 = Color(hsl=start)
    c2 = Color(hsl=end)
    gradient = list(c1.range_to(c2, max + 1))
    value = value if value < max else max
    return gradient[int(value)].hex


@app.template_filter("air_quality_index")
def air_quality_index(air_quality):
    """
    Returns an index for the air quality based on PM10, NO2, SO2, O3
    Based on http://www.atmo-alsace.net/site/Explications-sur-le-calcul-des-indices-22.html
    """
    scales = {
        'pm10': [0, 10, 20, 30, 40, 50, 65, 80, 100, 125],
        'so2': [0, 40, 80, 120, 160, 200, 250, 300, 400, 500],
        'no2': [0, 30, 55, 85, 110, 135, 165, 200, 275, 400],
        'o3': [0, 30, 55, 80, 105, 130, 150, 180, 210, 240],
    }

    aq_indexes = []
    for scale in scales.keys():
        scale_index = min([v for v in scales[scale] if v >= air_quality[scale]] or [0])
        aq_indexes.append(scales[scale].index(scale_index) + 1)

    return max(aq_indexes) if len(aq_indexes) > 0 else 0


@app.template_filter("air_quality_translation")
def air_quality_translation(air_quality):
    terms = [
        _('No data'),
        _('Very good'),
        _('Very good'),
        _('Good'),
        _('Good'),
        _('Average'),
        _('Below average'),
        _('Below average'),
        _('Bad'),
        _('Bad'),
        _('Very bad'),
    ]
    index = air_quality_index(air_quality)
    return terms[index]


@app.template_filter("air_quality_gradient")
def air_quality_gradient(air_quality):
    index = air_quality_index(air_quality)

    return gradient(index, 10, start=(.4,.8,.5)) if index > 0 else '#fff'


@app.template_filter("wind_repeat")
def wind_repeat(speed_kph, character):
    """Repeats a character depending on the force of the wind"""
    return "".join(repeat(character, (round(speed_kph / 10)) if speed_kph < MAX_WIND_ACCEPTABLE else 4))


@app.template_filter("precip_percent")
def precip_percent(precip_mm):
    """Handle vertical scale for precip_mm"""
    precip_mm = precip_mm + 1 if precip_mm > 0 else precip_mm
    precip_mm = min(precip_mm, MAX_RAIN_ACCEPTABLE)
    return (precip_mm / MAX_RAIN_ACCEPTABLE) * 100


@app.template_filter("precip_gradient")
def precip_gradient(precip_mm):
    """Handle gradient for precip_mm"""
    if precip_mm >= PRECIP_ALERT:
        return '#000'
    
    return "hsl(210, 80%, 50%)"


@app.template_filter("gradient_temp")
def gradient_temp(temp, ideal_min, ideal_max):
    """Handle gradient for temp around ideal temp"""
    _max = 35
    temp = temp if temp > 0 else 0
    temp = temp if temp < _max else _max

    gradient = []

    for temperature in range(ideal_min):
        temp_luminance = 50 + (50 / ideal_min - 1) * temperature
        gradient.append("hsl(220,100%,{}%)".format(round(temp_luminance)))

    for temperature in range(ideal_max - ideal_min):
        gradient.append("hsl(220,100%,100%)")

    for temperature in range(_max - ideal_max + 1):
        temp_luminance = 100 - (50 / (_max - ideal_max + 1)) * temperature
        gradient.append("hsl(22,100%,{}%)".format(round(temp_luminance)))

    gradient.append("hsl(22,100%,50%)")

    return gradient[round(temp)]


@app.template_filter("day")
def day(value, format="%A %d %b"):
    """Use Babel to localize a date from ISO with language-specific format"""
    if value is None:
        return ""
    d = date.fromisoformat(value)
    
    localized_format = _('EEEE, MMMM d')

    return format_date(date=d, format=localized_format)


@app.template_filter("proba_value")
def proba_value(hour):
    """Compute a probability and output percentage"""
    chance = round(int(hour["chance_of_rain"]) / (100 / 3))
    precip = min(hour["precip_mm"], MAX_RAIN_ACCEPTABLE)
    wind = min(hour["wind_kph"], MAX_WIND_ACCEPTABLE)
    temp = hour["temp_c"]
    feelslike = hour["feelslike_c"]

    proba = 0

    # rain is annoying (0-3 chance + 0-10 precip mm)
    proba += chance
    proba += 10 * precip / MAX_RAIN_ACCEPTABLE
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

    return round(proba)


@app.template_filter("proba_gradient")
def proba_gradient(hour):
    """Output gradient color"""
    max_val = 30
    probability = min(proba_value(hour), max_val)

    start_color = (.4,.8,.5)
    end_color = (0,.8,.6)

    return gradient(probability, max=max_val, start=start_color, end=end_color)


@app.template_filter("localized_condition")
def localized_condition(code):
    """Translate weather condition from code"""
    
    # conditions list from https://www.weatherapi.com/docs/#weather-icons
    c_file = open('translations/conditions.json')
    c_data = json.loads(c_file.read())

    condition = next((item for item in c_data if item['code'] == code), None)

    for lang in condition['languages']:
        if lang['lang_iso'] == get_locale():
            localized_condition_text = lang['day_text']
            break
    else:
        localized_condition_text = condition['day']

    return localized_condition_text


@app.template_filter("localized_azimuth")
def localized_azimuth(code):
    """Translate azimuth from code"""
    
    # conditions list from https://www.weatherapi.com/docs/#weather-icons
    a_file = open('translations/azimuths.json')
    a_data = json.loads(a_file.read())

    azimuth = a_data[code][get_locale()]

    return azimuth


# -------------
# TEMPLATE TAGS
# -------------

@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    else:
        if not 'lang' in session:
            session['lang'] = request.accept_languages.best_match(app.config['LANGUAGES'].keys())
    return session.get('lang', 'en')

app.jinja_env.globals['get_locale'] = get_locale


def asset_url(asset_path):
    """Returns a full asset URL from path"""

    domain = request.host_url
    domain = domain[:-1] if domain[:-1] == "/" else domain

    return "%s%s" % (domain, url_for('static', filename=asset_path))

app.jinja_env.globals['asset_url'] = asset_url

