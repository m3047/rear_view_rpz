# Configuration for Rear View RPZ

# Dnstap unix domain socket on local host.
SOCKET_ADDRESS = '/tmp/dnstap'

# Explicitly set the logging level if desired.
#import logging
#LOG_LEVEL = logging.INFO
LOG_LEVEL = None

# This one is similar to LOG_LEVEL. It's really intended for internal / debugging
# use, but this way it doesn't get inadvertently left turned on when I commit
# code. Unlike LOG_LEVEL this isn't the logging level but the routine to call
# to actually print the message.
#PRINT_COROUTINE_ENTRY_EXIT = logging.info

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

# The agent can run a console which provides visibility into internal data
# structures. Set this to a dict with 'host' and 'port' keys.
CONSOLE = None
# CONSOLE = dict(host='127.0.0.1', port=3047)
