# signinBackend
Backend for the signin iOS and Android apps

# Requirements

- PostgreSQL
- ImageMagick
- Nginx or some other web server
- An SSL certificate

# Terse Production Installation Instructions (for those of you who've done this sort of thing before)

1. Clone this repo and cd into it
1. Create a python virtual env by running `pip3 install -r requirements.txt`
1. (Optional) Replace the 320x320 `site/app/static/logo.png`
1. (Optional) Replace the 64x64 `site/app/qrcode/logo.png`
1. Edit `config.py`
1. Change the text in `covidForm.html` as needed
1. Change the text in `views.py` as needed 
2. Change the secret key in `passwords.json`
3. Change the db key in `passwords.json`
4. `chmod 600 passwords.json`
5. Make sure `passwords.json` is owned by the user running the web server
1. Initialize the database by running: `psql -f createdb.sql`
1. Save the password guid that the above command created
2. Configure your web server to run the Flask app in `wsgi.py`
1. Start the iOS app
1. Configure your server URL in the iOS app 
2. Reset the password using the iOS app. Use the guid from the previous step

# Setting up via Docker

Coming soon

# Detailed installation on Production

Coming soon

# How to contribute

Coming soon
