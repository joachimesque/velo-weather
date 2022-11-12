# velo-weather

**Bike ride opportunity, according to rain and wind forecasts where you are.**

This uses https://www.open-meteo.com/ for weather forecast and geocoding API.

## Run

It's just a standard Flask app :-). It can be deployed on Dokku and Heroku.

```fish
$ source venv/bin/activate.fish
$ SECRET_KEY=set_me_up gunicorn app:app --reload
```


## Translations

Initialize a new language:

```bash
pybabel init -i translations/messages.pot -d translations -l fr
```

Update all translation files:

```bash
pybabel extract -F babel.cfg -k _l -o translations/messages.pot .
pybabel update -i translations/messages.pot -d translations
```

Compile translation files:

```bash
pybabel compile -d translations
```
