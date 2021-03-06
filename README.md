# s3pac
S3pac is a pacman package repository server built on SimpleDB and S3.

Implemented as a Python WSGI server using Flask and Boto.

# Requirements
- Python 3
- Boto
- Dateutil
- Flask
- Werkzeug
- Docopt (CLI)
- Requests (CLI)

# Installation
    python setup.py build
    python setup.py install

# Configuration
### Server
The configuration file `s3pac.conf.py` is read from the current working directory. See the example configuration file for details.

### Pacman
The pacman repository endpoint is `$SERVERURL/r/$repo/$arch`:

    [myrepo]
    Server = http://127.0.0.1:9111/r/$repo/$arch

# Example setup with Gunicorn
Set up a configuration directory at e.g. `/etc/s3pac`:

    $ ls -l /etc/s3pac 
    total 8
    lrwxrwxrwx 1 root root  14 Apr 27 12:20 data -> /var/lib/s3pac
    -rw-r--r-- 1 root root  36 Apr 27 12:20 gunicorn.conf.py
    -rw------- 1 root root 403 Apr 26 21:10 s3pac.conf.py

Then start the app under Gunicorn using `/etc/s3pac` as the working directory:

    /usr/bin/gunicorn --chdir /etc/s3pac s3pac.wsgi:app

# License
Licensed under the MIT (Expat) license.
