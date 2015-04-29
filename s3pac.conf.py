# Root directory for uploads and temporary files.
# Relative to the server working directory.
DATA_ROOT = "data"

# Maximum upload size.
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024

# AWS access credentials. Optional.
AWS_ACCESS_KEY_ID = None
AWS_SECRET_ACCESS_KEY = None

# Storage configuration.
AWS_REGION_NAME = 'eu-west-1'
AWS_SDB_DOMAIN_NAME = 's3pac'
AWS_S3_BUCKET_NAME = 'my-s3pac-bucket'
AWS_S3_PREFIX = 'packages'
