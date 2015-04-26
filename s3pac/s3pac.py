import os, io, json
from datetime import datetime
from dateutil import parser as dateparser
from flask import Flask, Response, request, redirect, url_for, abort, send_file
from werkzeug import secure_filename

from s3pac.model import DateTimeProperty
from s3pac.package import Package, write_database_file, write_signature_file
from s3pac.database import PackageDatabase

# -----------------------------------------------------------------------------

JSONPROPFMT = {
    DateTimeProperty: (datetime.isoformat, dateparser.parse),
}

def _json_from_pkg(pkg):
    return Package.to_dict(pkg, JSONPROPFMT)

# -----------------------------------------------------------------------------

app = Flask(__name__)
app.config.from_pyfile("config.py")

pkgdb = PackageDatabase(
    access_key_id = app.config.get('AWS_ACCESS_KEY_ID', None),
    secret_access_key = app.config.get('AWS_SECRET_ACCESS_KEY', None),
    region_name = app.config.get('AWS_REGION_NAME'),
    sdb_domain_name = app.config.get('AWS_SDB_DOMAIN_NAME'),
    s3_bucket_name = app.config.get('AWS_S3_BUCKET_NAME')
)

# -----------------------------------------------------------------------------

def _get_database_file(repo, sysarch):
    # collect packages with given system architecture or 'any'
    pkgs = []
    for arch in (sysarch, 'any'):
        pkgs.extend(pkgdb.find(repo=repo, arch=arch))

    # write package database file
    dbfilepath = os.path.join(app.config['DATA_ROOT'],
                              "%s.db.tar.gz" % repo)
    with open(dbfilepath, 'wb') as dbfile:
        write_database_file(dbfile, pkgs)

    # send the database file
    return send_file(dbfilepath, mimetype='application/octet-stream')

def _get_package_file(repo, filename):
    pkg = pkgdb.findone(repo=repo, filename=filename)
    if not pkg:
        abort(404)
    return redirect(pkgdb.url(pkg))

def _get_package_signature_file(repo, sigfilename):
    pkgfilename = sigfilename[:-4]
    pkg = pkgdb.findone(repo=repo, filename=pkgfilename)
    if not pkg or not pkg.pgpsig:
        abort(404)

    sigfile = io.BytesIO()
    write_signature_file(sigfile, pkg)
    sigfile.seek(0)

    return send_file(sigfile,
                     attachment_filename=sigfilename,
                     as_attachment=True)

@app.route("/r/<repo>/<arch>/<filename>", methods=['GET'])
def get_file(repo, arch, filename):
    """Pacman repository interface."""
    if filename.endswith(".pkg.tar.xz"):
        return _get_package_file(repo, filename)
    if filename.endswith(".pkg.tar.xz.sig"):
        return _get_package_signature_file(repo, filename)
    if filename.endswith(".db") or filename.endswith(".db.tar.gz"):
        return _get_database_file(repo, arch)
    abort(404)

@app.route("/p/<repo>/", methods=['GET'])
def get_package_list(repo):
    """Return all packages in a repository."""
    filters = {}
    filters['repo'] = repo
    pkgs = pkgdb.find(**filters)
    _json = list(map(_json_from_pkg, pkgs))
    return json.dumps(_json)

@app.route("/p/<repo>/<arch>/", methods=['GET'])
def get_package_list_arch(repo, arch):
    """Return all packages in a repository with given architecture."""
    filters = {}
    filters['repo'] = repo
    filters['arch'] = arch
    pkgs = pkgdb.find(**filters)
    _json = list(map(_json_from_pkg, pkgs))
    return json.dumps(_json)

@app.route("/p/<repo>/<arch>/<name>", methods=['GET'])
def get_package(repo, arch, name):
    """Return a specific package."""
    pkg = pkgdb.findone(repo=repo, arch=arch, name=name)
    if not pkg:
        abort(404)
    return json.dumps(_json_from_pkg(pkg))

@app.route("/p/<repo>/<arch>/<name>", methods=['DELETE'])
def delete_package(repo, arch, name):
    """Delete a package from a repository."""
    if not pkgdb.delete(repo=repo, arch=arch, name=name):
        abort(404)
    return ""

@app.route("/p/<repo>/", methods=['POST'])
def post_package_file(repo):
    """Upload and publish a package."""
    pkgupload = request.files.get('package', None)
    if not pkgupload or not pkgupload.filename.endswith(".pkg.tar.xz"):
        abort(401)

    sigupload = request.files.get('signature', None)
    if sigupload and not sigupload.filename.endswith(".pkg.tar.xz.sig"):
        abort(401)

    def _save_upload(upload):
        filename = secure_filename(upload.filename)
        filepath = os.path.join(app.config['DATA_ROOT'], filename)
        upload.save(filepath)
        return filepath

    pkgfilepath = _save_upload(pkgupload)
    sigfilepath = _save_upload(sigupload) if sigupload else None

    pkgfile = open(pkgfilepath, 'rb')
    sigfile = open(sigfilepath, 'rb') if sigfilepath else None

    pkg = pkgdb.publish(repo, pkgfile, sigfile)

    pkgurl = url_for('get_package', repo=repo, arch=pkg.arch, name=pkg.name)
    return redirect(pkgurl)
