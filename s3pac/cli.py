"""S3pac command line tool.

Usage:
  s3pac [--server=<url>] publish <repo> <pkgfile> [<sigfile>]
  s3pac [--server=<url>] remove <repo> <arch> <name>
  s3pac [--server=<url>] show <repo> <arch> <name>
  s3pac [--server=<url>] list <repo> [--full]

Options:
  -h --help         Show this screen.
  --version         Show version.
  -s --server=<url> Use URL a base server (default http://127.0.0.1:9111/).
  --full            Display full metadata for each package.
"""
import os, sys
import json
import requests
from docopt import docopt
from urllib import parse as urlparse

DEFAULT_SERVER = "http://127.0.0.1:9111/"

UNITS = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')

def _human_readable_size(size):
    unit = 0
    while size > 2048.0 and unit+1 < len(UNITS):
        size /= 1024.0
        unit += 1
    return "%.2f %s" % (size, UNITS[unit])

def _make_url(opts, urlpath):
    server = opts.get('server', DEFAULT_SERVER)
    return urlparse.urljoin(server, urlpath)

def _print_package(pkg):
    NEWLINE = "\n" + " " * 17
    validations = []
    if pkg['md5sum']:
        validations.append("MD5 Sum")
    if pkg['sha256sum']:
        validations.append("SHA256 Sum")
    if pkg['pgpsig']:
        validations.append("Signature")
    print("Repository     : %s" % pkg['repo'])
    print("Name           : %s" % pkg['name'])
    print("Version        : %s" % pkg['version'])
    print("Description    : %s" % (pkg['desc'] or "None"))
    print("Architecture   : %s" % (pkg['arch'] or "None"))
    print("URL            : %s" % (pkg['url'] or "None"))
    print("Licenses       : %s" % ("  ".join(pkg['licenses']) or "None"))
    print("Groups         : %s" % ("  ".join(pkg['groups']) or "None"))
    print("Provides       : %s" % ("  ".join(pkg['provides']) or "None"))
    print("Depends On     : %s" % ("  ".join(pkg['depends']) or "None"))
    print("Optional Deps  : %s" % (NEWLINE.join(pkg['optdepends']) or "None"))
    print("Conflicts With : %s" % ("  ".join(pkg['conflicts']) or "None"))
    print("Replaces       : %s" % ("  ".join(pkg['replaces']) or "None"))
    print("Download Size  : %s" % _human_readable_size(pkg['filesize']))
    print("Installed Size : %s" % _human_readable_size(pkg['size']))
    print("Packager       : %s" % pkg['packager'])
    print("Build Date     : %s" % pkg['builddate'])
    print("Validated By   : %s" % ("  ".join(validations) or "None"))
    print()

def _print_package_oneline(pkg):
    print("%s %s (%s)" % (pkg['name'], pkg['version'], pkg['arch']))

class CommandException(Exception):
    def __init__(self, msg):
        self.msg = msg

def do_publish(opts):
    pkgfilepath = opts['<pkgfile>']
    sigfilepath = opts['<sigfile>'] or (pkgfilepath + ".sig")

    files = { 'package': open(pkgfilepath, 'rb') }
    if os.path.isfile(sigfilepath):
        files['signature'] = open(sigfilepath, 'rb')

    url = _make_url(opts, "/p/%s/" % opts['<repo>'])
    response = requests.post(url, files=files)

    if not response.ok:
        raise CommandException("server error: %d" % response.status_code)

def do_remove(opts):
    urlpath = "/p/%s/%s/%s" % (opts['<repo>'], opts['<arch>'], opts['<name>'])
    url = _make_url(opts, urlpath)
    response = requests.delete(url)

    if response.status_code == 404:
        raise CommandException("package not found: %s" % opts['<name>'])

    if not response.ok:
        raise CommandException("server error: %d" % response.status_code)

def do_show(opts):
    urlpath = "/p/%s/%s/%s" % (opts['<repo>'], opts['<arch>'], opts['<name>'])
    url = _make_url(opts, urlpath)
    response = requests.get(url)

    if response.status_code == 404:
        raise CommandException("package not found: %s" % opts['<name>'])

    if not response.ok:
        raise CommandException("server error: %d" % response.status_code)

    _print_package(response.json())

def do_list(opts):
    urlpath = "/p/%s/" % opts['<repo>']
    url = _make_url(opts, urlpath)
    response = requests.get(url)

    if not response.ok:
        raise CommandException("server error: %d" % response.status_code)

    for pkg in response.json():
        if opts['--full']:
            _print_package(pkg)
        else:
            _print_package_oneline(pkg)


def main(opts):
    try:
        if opts['publish']:
            return do_publish(opts)
        elif opts['remove']:
            return do_remove(opts)
        elif opts['show']:
            return do_show(opts)
        elif opts['list']:
            return do_list(opts)
    except CommandException as ex:
        print("s3pac:", ex.msg)
        return 255

if __name__ == '__main__':
    opts = docopt(__doc__, version="s3pac 0.1")
    sys.exit(main(opts) or 0)
