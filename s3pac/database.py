import os
from datetime import datetime
from dateutil import parser as dateparser
import boto.sdb
import boto.s3

from s3pac.model import LongProperty, StringProperty, DateTimeProperty
from s3pac.package import Package, read_package_file

# -----------------------------------------------------------------------------

_FROM_SIMPLEDB = {
    LongProperty: lambda v: int(v) - 2**63,
    DateTimeProperty: dateparser.parse,
    }

_TO_SIMPLEDB = {
    LongProperty: lambda v: "%020d" % (v + 2**63),
    DateTimeProperty: datetime.isoformat,
    }

def _pkg_from_sdb(_dict):
    return Package.load(_FROM_SIMPLEDB, _dict)

def _sdb_from_pkg(pkg):
    return Package.store(_TO_SIMPLEDB, pkg)

# -----------------------------------------------------------------------------

class PackageDatabase:
    """Package repository interface to SimpleDB and S3."""
    def __init__(self, access_key_id, secret_access_key, region_name,
                 sdb_domain_name, s3_bucket_name, s3_prefix):
        # connect to simpledb
        self.sdb = boto.sdb.connect_to_region(region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
        self.sdb_domain = self.sdb.get_domain(sdb_domain_name)
        self.sdb_domain_name = sdb_domain_name

        # connect to s3
        self.s3 = boto.s3.connect_to_region(region_name,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key)
        self.s3_bucket = self.s3.get_bucket(s3_bucket_name)
        self.s3_bucket_name = s3_bucket_name
        self.s3_prefix = s3_prefix

    def _pkgitemname(self, pkg):
        return os.path.join(pkg.repo, pkg.arch, pkg.name)

    def _pkgkeyname(self, pkg):
        return os.path.join(self.s3_prefix, pkg.repo, pkg.filename)

    def publish(self, repo, pkgfile, sigfile):
        """Read package archive from `pkgfile` and publish to `repo`."""
        pkg = read_package_file(pkgfile, sigfile)

        pkg.repo = repo
        pkg.publishdate = datetime.utcnow()

        # upload package file to s3
        pkgkey = boto.s3.key.Key(self.s3_bucket, self._pkgkeyname(pkg))
        pkgfile.seek(0)
        pkgkey.set_contents_from_file(pkgfile)

        # insert metadata
        self.sdb_domain.put_attributes(self._pkgitemname(pkg),
                                       _sdb_from_pkg(pkg))

        # remove previous versions if they exist
        for ppkg in self.find(repo=pkg.repo, arch=pkg.arch, name=pkg.name):
            if ppkg.version != pkg.version:
                self.delete(repo=repo, arch=ppkg.arch, name=ppkg.name,
                            version=ppkg.version)

        return pkg

    def find(self, **kwargs):
        """Find matching packages."""
        parts = []
        conds = Package.convertdict(_TO_SIMPLEDB, kwargs)
        for name, values in conds.items():
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if value.startswith('%') or value.endswith('%'):
                    escaped = value[1:-1].replace('%', '\%')
                    parts.append('`%s` LIKE "%s%s%s"' % \
                        (name, value[0], escaped, value[-1]))
                else:
                    parts.append('`%s`="%s"' % (name, value))
        query = "SELECT * FROM `%s` WHERE %s" % \
            (self.sdb_domain_name, " AND ".join(parts))
        print(query)
        results = self.sdb_domain.select(query, consistent_read=True)
        return list(map(_pkg_from_sdb, results))

    def findone(self, **kwargs):
        """Find first matching package."""
        pkgs = self.find(**kwargs)
        return pkgs[0] if pkgs else None

    def url(self, pkg):
        """Return a HTTP download URL for `pkg`."""
        pkgkey = self.s3_bucket.get_key(self._pkgkeyname(pkg))
        return pkgkey.generate_url(3600)

    def delete(self, **kwargs):
        """Delete all matching packages."""
        pkgs = self.find(**kwargs)
        for pkg in pkgs:
            pkgkey = self.s3_bucket.get_key(self._pkgkeyname(pkg))
            if pkgkey is not None:
                pkgkey.delete()
            self.sdb_domain.delete_attributes(self._pkgitemname(pkg))
        return pkgs
