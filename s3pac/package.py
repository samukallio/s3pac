import re, hashlib, tarfile
from io import BytesIO, SEEK_END
from base64 import b64encode, b64decode
from datetime import datetime
from stat import S_IFREG, S_IFDIR, S_IRWXU, \
                 S_IRUSR, S_IWUSR, S_IRGRP, \
                 S_IXGRP, S_IROTH, S_IXOTH

from s3pac.model import Model
from s3pac.model import LongProperty, StringProperty, DateTimeProperty

class Package(Model):
    """Package metadata."""
    repo = StringProperty()
    arch = StringProperty()
    name = StringProperty()
    base = StringProperty()
    version = StringProperty()
    groups = StringProperty(multiple=True)
    desc = StringProperty()
    licenses = StringProperty(multiple=True)
    url = StringProperty()
    builddate = DateTimeProperty()
    packager = StringProperty()
    size = LongProperty()
    replaces = StringProperty(multiple=True)
    conflicts = StringProperty(multiple=True)
    provides = StringProperty(multiple=True)
    depends = StringProperty(multiple=True)
    optdepends = StringProperty(multiple=True)
    makedepends = StringProperty(multiple=True)
    checkdepends = StringProperty(multiple=True)
    filename = StringProperty()
    filesize = LongProperty()
    pgpsig = StringProperty()
    md5sum = StringProperty()
    sha256sum = StringProperty()
    publishdate = DateTimeProperty()

def _checksum_file(_file, hashclass):
    """Compute the checksum of a file."""
    buf = bytearray(65536)
    mem = memoryview(buf)
    _hash = hashclass()
    _file.seek(0)
    while True:
        n = _file.readinto(buf)
        if n == 0:
            break
        _hash.update(mem[:n])
    return _hash.hexdigest()

_PKGINFO_LIST_KEYS = [
    'license', 'replaces', 'group', 'conflict', 'provides', 'backup', 'depend',
    'optdepend', 'makedepend', 'checkdepend', 'makepkgopt'
    ]

def _read_pkginfo_file(pkginfofile):
    """Extract key-value pairs from a .PKGINFO file."""
    pkginfo = { key: [] for key in _PKGINFO_LIST_KEYS }
    for line in pkginfofile:
        line = line.decode('utf8').strip()
        if line[0] == '#':
            continue
        key, value = re.split("\s*=\s*", line, 1)
        if key in _PKGINFO_LIST_KEYS:
            pkginfo[key].append(value)
        else:
            pkginfo[key] = value
    return pkginfo

def read_package_file(pkgfile, sigfile=None):
    """Read a package archive (and optionally a signature file)."""
    pkg = Package()

    # read .PKGINFO properties
    pkgfile.seek(0)
    with tarfile.open(fileobj=pkgfile, mode='r') as pkgtar:
        pkginfo = _read_pkginfo_file(pkgtar.extractfile(".PKGINFO"))

    # parse pkginfo properties
    pkg.arch = pkginfo.get('arch', 'any')
    pkg.name = pkginfo.get('pkgname', "")
    pkg.base = pkginfo.get('pkgbase', "")
    pkg.version = pkginfo.get('pkgver', "")
    pkg.desc = pkginfo.get('pkgdesc', "")
    pkg.groups = pkginfo.get('group', [])
    pkg.licenses = pkginfo.get('license', [])
    pkg.url = pkginfo.get('url', "")
    pkg.builddate = datetime.utcfromtimestamp(int(pkginfo.get('builddate', 0)))
    pkg.packager = pkginfo.get('packager', "")
    pkg.size = int(pkginfo.get('size', 0))
    pkg.replaces = pkginfo.get('replaces', [])
    pkg.conflicts = pkginfo.get('conflict', [])
    pkg.provides = pkginfo.get('provides', [])
    pkg.depends = pkginfo.get('depend', [])
    pkg.optdepends = pkginfo.get('optdepend', [])
    pkg.makedepends = pkginfo.get('makedepend', [])
    pkg.checkdepends = pkginfo.get('checkdepend', [])

    # determine file properties
    pkg.filename = "%s-%s-%s.pkg.tar.xz" % (pkg.name, pkg.version, pkg.arch)
    pkg.filesize = pkgfile.seek(0, SEEK_END)
    pkg.md5sum = _checksum_file(pkgfile, hashlib.md5)
    pkg.sha256sum = _checksum_file(pkgfile, hashlib.sha256)

    # add signature if it exists
    if sigfile:
        pkg.pgpsig = b64encode(sigfile.read())

    return pkg

def write_desc_file(_file, pkg):
    """Write a `desc` file for the package database."""
    fields = [
        ("%FILENAME%",  pkg.filename),
        ("%NAME%",      pkg.name),
        ("%BASE%",      pkg.base),
        ("%VERSION%",   pkg.version),
        ("%DESC%",      pkg.desc),
        ("%GROUPS%",    str.join("\n", pkg.groups)),
        ("%CSIZE%",     str(pkg.filesize)),
        ("%ISIZE%",     str(pkg.size)),
        ("%MD5SUM%",    pkg.md5sum),
        ("%SHA256SUM%", pkg.sha256sum),
        ("%PGPSIG%",    pkg.pgpsig),
        ("%URL%",       pkg.url),
        ("%LICENSE%",   str.join("\n", pkg.licenses)),
        ("%ARCH%",      pkg.arch),
        ("%BUILDDATE%", pkg.builddate.strftime("%s")),
        ("%PACKAGER%",  pkg.packager),
        ("%REPLACES%",  str.join("\n", pkg.replaces)),
    ]
    _file.seek(0)
    for block in ["%s\n%s\n\n" % (k,v) for k,v in fields if v]:
        _file.write(block.encode('utf-8'))

def write_depends_file(_file, pkg):
    """Write a `depends` file for the package database."""
    fields = [
        ("%DEPENDS%",      str.join("\n", pkg.depends)),
        ("%CONFLICTS%",    str.join("\n", pkg.conflicts)),
        ("%PROVIDES%",     str.join("\n", pkg.provides)),
        ("%OPTDEPENDS%",   str.join("\n", pkg.optdepends)),
        ("%MAKEDEPENDS%",  str.join("\n", pkg.makedepends)),
        ("%CHECKDEPENDS%", str.join("\n", pkg.checkdepends)),
    ]
    _file.seek(0)
    for block in ["%s\n%s\n\n" % (k,v) for k,v in fields if v]:
        _file.write(block.encode('utf-8'))

def write_signature_file(_file, pkg):
    """Write the signature file of a package."""
    _file.seek(0)
    _file.write(b64decode(pkg.pgpsig))

def write_database_file(_file, pkgs):
    """Write out a package database file."""
    _file.seek(0)
    tar = tarfile.open(fileobj=_file, mode='w:gz')

    REG = S_IFREG | S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH
    DIR = S_IFDIR | S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH

    def _add(path, mode, _file=None):
        info = tarfile.TarInfo(path)
        info.mode = mode
        info.uname = 'root'
        info.gname = 'root'
        if _file:
            info.size = _file.seek(0, SEEK_END)
            _file.seek(0)
        tar.addfile(info, _file)

    for pkg in pkgs:
        dirname = "%s-%s" % (pkg.name, pkg.version)
        _add(dirname + "/", DIR)

        descfile = BytesIO()
        write_desc_file(descfile, pkg)
        _add(dirname + "/desc", REG, descfile)

        dependsfile = BytesIO()
        write_depends_file(dependsfile, pkg)
        _add(dirname + "/depends", REG, dependsfile)

    tar.close()
