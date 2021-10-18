import os

from datetime import date, datetime

import json
import requests
from colour import Color

from flask import Flask, render_template, request
from flask_babel import Babel, format_date, _


app = Flask(__name__)

app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = ['en', 'fr']

babel = Babel(app)

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])

app.jinja_env.globals['get_locale'] = get_locale

# top of the scale for wind, kph
MAX_WIND_ACCEPTABLE = 35
# top of the scale for rain, mm per hour
MAX_RAIN_ACCEPTABLE = 1.5

MIN_HOUR = 7
MAX_HOUR = 20


@app.route("/")
def index():
    data = None
    q = request.args.get("location", "Montreuil, France")
    api_key = os.getenv("WEATHER_API_KEY")
    r = requests.get(f"https://api.weatherapi.com/v1/forecast.json?key={api_key}&q={q}&days=10&aqi=no&alerts=yes")
    # probably location unknow
    if r.status_code != 400:
        r.raise_for_status()
        data = r.json()
    return render_template("index.html", data=data, max_rain=MAX_RAIN_ACCEPTABLE, max_wind=MAX_WIND_ACCEPTABLE)


@app.template_filter("valid_day")
def valid_day(value):
    """Only return valid day objects"""
    now = datetime.now()
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


@app.template_filter("gradient")
def gradient(value, max, end="red"):
    """With a value from 0 to max, generate the correct gradient"""
    value = int(value)
    c1 = Color(hsl=(0, 1, 1))
    c2 = Color(end)
    gradient = list(c1.range_to(c2, max + 1))
    value = value if value < max else value
    return gradient[int(value)].hex


@app.template_filter("precip_percent")
def precip_percent(precip_mm):
    """Handle vertical scale for precip_mm"""
    precip_mm = precip_mm + 1 if precip_mm > 0 else precip_mm
    precip_mm = min(precip_mm, 6)
    return (precip_mm / 6) * 100


@app.template_filter("gradient_temp")
def gradient_temp(temp, ideal_min, ideal_max):
    """Handle gradient for temp around ideal temp"""
    _max = 35
    temp = temp if temp > 0 else 0
    temp = temp if temp < _max else temp

    gradient = []

    for temperature in range(ideal_min):
        temp_luminance = 50 + (50 / ideal_min - 1) * temperature
        gradient.append("hsl(220,100%,{}%)".format(round(temp_luminance)))

    for temperature in range(ideal_max - ideal_min):
        gradient.append("hsl(220,100%,100%)")

    for temperature in range(_max - ideal_max + 1):
        temp_luminance = 100 - (50 / (_max - ideal_max + 1)) * temperature
        gradient.append("hsl(0,100%,{}%)".format(round(temp_luminance)))

    gradient.append("hsl(0,100%,50%)")

    return gradient[round(temp)]


@app.template_filter("day")
def day(value, format="%A %d %b"):
    """Use Babel to localize a date from ISO with language-specific format"""
    if value is None:
        return ""
    d = date.fromisoformat(value)
    
    localized_format = _('EEEE, MMMM d')

    return format_date(date=d, format=localized_format)


@app.template_filter("proba")
def proba(hour):
    """Compute a proba and output gradient color"""
    chance = int(hour["chance_of_rain"]) / 100
    precip = min(hour["precip_mm"], MAX_RAIN_ACCEPTABLE)
    wind = min(hour["wind_kph"], MAX_WIND_ACCEPTABLE)

    p_precip = (chance * precip) / MAX_RAIN_ACCEPTABLE
    p_wind = wind / MAX_WIND_ACCEPTABLE
    # wind is twice as annoying as rain
    p = (p_precip + p_wind * 2) / 3

    return gradient((1 - p) * 100, max=100, end="green")


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
