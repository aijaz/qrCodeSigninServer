# QR Code Signin Server

Backend for the COVID-19 contact tracing signin iOS and Android apps

# What _is_ this repo?

As Director of Security at my local masjid (mosque), I wanted a quick, secure, and reliable way to sign people in as they enter the building. I wanted their name, phone number, and optionally their email address. This is so that if anyone attending services tested positive for COVID-19 and informed us, we can let everyone else who attended around that time know about it (by phone and email) so that they can get themselves tested. 

This repo allows people to visit a website before attending. They can enter their name, phone number, and email on a form. When they submit the form, the website will generate an image containing a QR Code that contains that information. Then they can save that image on their phone. 

There's a companion [iOS app][iosApp] and an Android app that's currently in development. The people at the masjid signing folks in can scan the QR code using those apps. Once a QR code is signed, the mobile client will contact the REST web server described and this repo, and the web server will save the data into the database. More information on how to use the apps will be available soon.

# Requirements

- PostgreSQL
- ImageMagick
- Nginx or some other web server
- An SSL certificate

# Installation Instructions

First, install an SSL-enabled [Flask][] web server. If you don't know how to do this, you can find several good tutorials online. The one that I found most beneficial is [this one from Digital Ocean][flaskTutorial]. 

Next, make sure you have [ImageMagick][] installed. On systems that have `apt-get`, you can run the following command to install ImageMagick:

```bash
apt-get --yes install imagemagick
```

You will need ImageMagick to construct the QR Code image. The Flask app will call the `convert` and `compose` commands. Find out where these commands are installed by using the `which` command as shown below:

```bash
$ which convert
/usr/bin/convert
$ 
```

This shows us that `convert` is installed at `/usr/bin`. `compose` is most likely installed in the same location. Note this location, because you'll need to refer to it later. 

Clone this repo. Assuming you're following the Digital Ocean tutorial, start your python virtual environment, and install all the required python modules by running: 

```bash
pip3 install -r requirements.txt
```

Now. Time to customize the look and feel of the website and QR codes. This repo ships with two files name `logo.png`. The first is a 320x320 image at `site/app/static/logo.png` and the other is a 64x64 image at `site/app/qrcode/logo.png`. Replace those with your own logo. If you do not wish to have a logo, just replace them with white or transparent PNGs of the appropriate sizes. There's also some text in `covidForm.html` and `views.py` that you can change as needed. 

Edit `config.py`. You may need to change the value of `BIN_DIR`, which is the location where `convert` and `compose` are installed. Remember you noted that earlier. Also, if your database is not hosted on the same server make sure you set the database host name by changing the value of `DB_HOST_NAME`.

Like any well-behaved Flask app, this one uses a secret key to keep client-side sessions secure. Each installation should have its own secret key. The way I do this is I store the secret key in a file named `passwords.json` and make sure that that file is only readable by the user running the web server. So, if your flask user name is `flask`, make sure you type in the following (as root) in the appropriate directory: 

```bash
$ chmod 600 passwords.json
$ chown flask passwords.json
```

There is one more value that you need to set in `passwords.json`: the database key. For privacy purposes, any column that contains personally-identifiable information (PII) of your attendees is encrypted. Sure, this slows down performance considerably, but let's face it, this is not an app that needs to server thousands of requests a day. It'll be fine! I'm using the `PGP_SYM_ENCRYPT` and `PGP_SYM_DECRYPT` commands to encrypt and decrypt the data. These commands require an encryption key. This is the `db_key` in `passwords.json`. Please change the value of this key. These keys should not be checked into your repo, especially if your repo is public. Guard these keys and make sure that no one other than you has access to them.

We're almost done! When you're logged as the PostgreSQL root user (usually `postgres`) run the following command from the `db` directory to create and initialize the database:

```bash
$ psql -f createdb.sql
```

This command will drop the database named `signindb`, and drop the user named `signin`, so remember the following two things:

1. If you already have a user named `signin` or a database named `signindb`, change the names in `createdb.sql` to something else, and then change the values of `DB_DB_NAME` and `DB_DB_NAME` in `config.py` accordingly.
2. Don't run this command when you have production data in your database, otherwise you'll have to recover from backups. You _do_ have backups, don't you?

`createdb.sql` will create one admin account for you, and will prompt you for your full name, and your email address. When it finishes creating the datbase it will print something out that looks like this:

```postgres
$ psql -f createdb.sql
Time: 0.226 ms
What is your full name?: Aijaz Ansari
What is your email address?: user@example.com
                     Installation Message
══════════════════════════════════════════════════════════════
                                                             ↵
                                                             ↵
 This is your password recovery code: C8wNhsbC               ↵
                                                             ↵
 Please save this so that you can set your password.         ↵
                                                             ↵
                                                             ↵

(1 row)

$
```

You see that password recovery code? That's a random code that's different every time you invoke `createdb.sql`. This is the code that you will use to set your password. Save that code and don't share it with anyone. You will use the iOS or Android app to set your password using this code. 

"But Aijaz, why don't you just prompt me for my password?" you might ask. "Good question," I might say. I already have code in the REST API to change the password, and I don't want to duplicate the code, or ask you to enter your cleartext password in a terminal where someone shoulder-surfing could have access to it. 

Okay, now that everything's set up, it's time to start the Flask app. Make sure your setup starts the app that's in `site/wsgi.py`. In my gunicorn file it's referred to as `wsgi:app` (the `app` object in the module named `wsgi`).

Launch the iOS or Android app. Configure your server URL the mobile app. Navigate to the appropriate screen to reset your password, and enter the password recovery code (remember, your's will be different from the one above) and your new password. And then you should be good to go. 

Really. That's it. If you have any questions, contact me on Twitter, where I'm `\_aijaz\_` or open an issue against this repo. 

Let me know what you think about this suite of apps. 

Thanks!

Aijaz.

# Installation Docker

Coming soon

[Flask]: https://palletsprojects.com/p/flask/
[flaskTutorial]: https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04
[ImageMagick]: https://imagemagick.org
[iosApp]: https://github.com/aijaz/masjidSignin


