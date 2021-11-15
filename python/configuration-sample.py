# Configuration for Rear View RPZ

# Dnstap unix domain socket on local host.
SOCKET_ADDRESS = '/tmp/dnstap'

# Explicitly set the logging level if desired.
#import logging
#LOG_LEVEL = logging.INFO
LOG_LEVEL = None

# If statistics reporting is desired, set this to the number of seconds between
# reports.
# STATS = 600 # 10 minutes
STATS = None

# Address of the server. This is pretty much always going to be a
# flavor of localhost.
DNS_SERVER = '127.0.0.1'

# Name of the response policy zone.
RESPONSE_POLICY_ZONE = 'rpz.example.com'

# Size of the RPZ.
# CACHE_SIZE = 10000
CACHE_SIZE = None
