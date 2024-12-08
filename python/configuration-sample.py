# Configuration for Rear View RPZ

# The agent listens for telemetry on a UDP socket. You MUST define UDP_LISTENER!
# 
# Multicast Support
# -----------------
# Multicast addresses / groups are supported, but optional; you can use either a
# unicast or a multicast host. If you do use multicast, you also have to specify the
# interface to listen on. You can only listen on a single interface.
#
# MULTICAST IS ONLY TESTED WITH IPv4 AND NO (UNPAID) SUPPORT IS PROVIDED.
#
# Dictionary Keys
# ---------------
#
# recipient:    The receiving unicast address or multicast group.
# port:         The port to listen to.
# interface     The interface to listen on if recipient is a multicast address.
#
# Multicast is not bound or configured at the system level, it is configured on the
# application socket: the application registers the socket to receive multicast
# datagrams. As part of this it supplies not only the receiving group (which looks like
# an address) but also specifies an address to identify the interface on which to
# listen for multicast traffic.
#
# This listens for datagrams addressed to (unicast) address 10.0.1.253, port 3053.
# UDP_LISTENER = dict(recipient='10.0.1.253', port=3053, interface=None)
# Assuming that 10.0.3.55 is bound to the eth1 network interface, the following will
# listen on eth1 for datagrams addressed to group 233.252.0.229, port 3053.
# UDP_LISTENER = dict(recipient='233.252.0.229', port=3053, interface=10.0.3.55)

# It is possible to track a sequence number in the UDP datagrams. The id number emitted
# by shodohflo/agents/dnstap_agent.py uses the tag "id". You can set this to None
# to get the old behavior of not tracking a sequence number.
#TELEMETRY_ID = 'id'

# Explicitly set the logging level if desired.
#import logging
#LOG_LEVEL = logging.INFO
LOG_LEVEL = None

# This one is similar to LOG_LEVEL. It's really intended for internal / debugging
# use, but this way it doesn't get inadvertently left turned on when I commit
# code. Unlike LOG_LEVEL this isn't the logging level but the routine to call
# to actually print the message:
# PRINT_COROUTINE_ENTRY_EXIT = logging.info
#PRINT_COROUTINE_ENTRY_EXIT = None

# If statistics reporting is desired, set this to the number of seconds between
# reports.
# STATS = 600 # 10 minutes
#STATS = None

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

# The default is to include IPv4 and IPv6.
#import dns.rdatatype as rdatatype
#ADDRESS_CLASSES = { rdatatype.A, rdatatype.AAAA }

# This controls what happens to garbage records in the actual zone. The
# default is logging.warning.
# GARBAGE_LOGGER = logging.warning
# GARBAGE_LOGGER = None
