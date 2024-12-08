#!/usr/bin/python3
# Copyright (c) 2019-2024 by Fred Morris Tacoma WA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""RearView Agent.

This script takes no arguments.

REQUIRES PYTHON 3.6 OR BETTER

Uses shodohflo/agents/dnstap_agent.py telemetry events to
maintain PTR records in a DNS Response Policy Zone (RPZ). You'll get better
performance if you configure your DNS server to only send such messages. The
expected specification for BIND in named.conf is:

    dnstap { client response; };
    
Please see the documentation for dnstap_agent.py. The telemetry is in a
JSON format, and as long as you mimic what dnstap_agent.py sends you can
use whatever source of telemetry you care to devise.

The PRINT_ Constants
--------------------

The PRINT_... constants control various debugging output. They can be
set to a print function which accepts a string, for example:

    PRINT_THIS = logging.debug
    PRINT_THAT = print
    
Origins, Futures, Credits
-------------------------

This is adapted from the DNS agent which ships with ShoDoHFlo:

  https://github.com/m3047/shodohflo
  
Originally it used the ShoDoHFlo libraries to read the Dnstap unix socket
directly, but that code (and the dependency) has been removed. Reading
datagrams allows multiple sources of events (multiple nameservers) to send
events. Multicast allows multiple recipients of those multiple event sources
to subscribe to the same stream(s) of events.

"""

import sys
from os import path
import logging

import socket
import asyncio

import struct
import rearview.mcast_structs as structs

import dns.rdatatype as rdatatype
import dns.rcode as rcode

from ipaddress import ip_address

from rearview.statistics import StatisticsFactory
from rearview.db import RearView

import sysconfig

PYTHON_IS_311 = int( sysconfig.get_python_version().split('.')[1] ) >= 11

if PYTHON_IS_311:
    from asyncio import CancelledError
else:
    from concurrent.futures import CancelledError

PRINT_COROUTINE_ENTRY_EXIT = None
MAX_READ_SIZE = 1024
ADDRESS_CLASSES = { rdatatype.A, rdatatype.AAAA }
GARBAGE_LOGGER = logging.warning
UDP_LISTENER = None
TELEMETRY_ID = 'id'
LOG_LEVEL = None
STATS = None
CACHE_SIZE = None
CONSOLE = None

if __name__ == "__main__":
    from configuration import *
else:
    STATS = None
    DNS_SERVER = '127.0.0.1'
    RESPONSE_POLICY_ZONE = 'rpz.example.com'
    
if CONSOLE:
    import rearview.console as console

if LOG_LEVEL is not None:
    logging.basicConfig(level=LOG_LEVEL)

# Start/end of coroutines. You will probably also want to enable it in shodohflo.fstrm.
if PRINT_COROUTINE_ENTRY_EXIT:
    import rearview.db
    import rearview.rpz
    rearview.db.PRINT_COROUTINE_ENTRY_EXIT = rearview.rpz.PRINT_COROUTINE_ENTRY_EXIT = PRINT_COROUTINE_ENTRY_EXIT

# Similar to the foregoing, but always set to something valid.
STATISTICS_PRINTER = logging.info

BIG_ENDIAN = ( 4, 'big' )   # Used for packing addresses when setting socket options.
ALL_INTERFACES = ''

class UDPListener(asyncio.DatagramProtocol):
    """UDP Listener.
    
    Properties
    
        rear_view   Set via code after the object is instantiated.
    """
    def __init__(self, *args, **kwargs):
        asyncio.DatagramProtocol.__init__(self, *args, **kwargs)
        self.rear_view = None
        return
    
    def connection_made(self, transport):
        self.transport = transport
        return
    
    def datagram_received(self, datagram, addr):
        if self.rear_view:
            self.rear_view.process_telemetry( datagram, addr )
        return

async def statistics_report(statistics):
    while True:
        await asyncio.sleep(STATS)
        for stat in sorted(statistics.stats(), key=lambda x:x['name']):
            STATISTICS_PRINTER(
                '{}: emin={:.4f} emax={:.4f} e1={:.4f} e10={:.4f} e60={:.4f} dmin={} dmax={} d1={:.4f} d10={:.4f} d60={:.4f} nmin={} nmax={} n1={:.4f} n10={:.4f} n60={:.4f}'.format(
                    stat['name'],
                    stat['elapsed']['minimum'], stat['elapsed']['maximum'], stat['elapsed']['one'], stat['elapsed']['ten'], stat['elapsed']['sixty'],
                    stat['depth']['minimum'], stat['depth']['maximum'], stat['depth']['one'], stat['depth']['ten'], stat['depth']['sixty'],
                    stat['n_per_sec']['minimum'], stat['n_per_sec']['maximum'], stat['n_per_sec']['one'], stat['n_per_sec']['ten'], stat['n_per_sec']['sixty'])
                )
    return

async def close_tasks(tasks):
    all_tasks = asyncio.gather(*tasks)
    all_tasks.cancel()
    try:
        await all_tasks
    except CancelledError:
        pass
    return

def main():
    if 'interface' in UDP_LISTENER:
        logging.info('Rearview Agent starting. Multicast Group: {}:{}  Listening on: {}  RPZ: {}'.format(
                        str(UDP_LISTENER['recipient']), UDP_LISTENER['port'], UDP_LISTENER['interface'],
                        RESPONSE_POLICY_ZONE
                    ) )
    else:
        logging.info('Rearview Agent starting. Listening on: {}:{}  RPZ: {}'.format(
                        str(UDP_LISTENER['recipient']), UDP_LISTENER['port'], RESPONSE_POLICY_ZONE
                    ) )
    
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    
    if CONSOLE:
        console_ctxt = console.Context()
        console_service = event_loop.run_until_complete(
                asyncio.start_server(
                    console_ctxt.handle_requests,
                    CONSOLE['host'], CONSOLE['port'], 
                    limit=MAX_READ_SIZE
                )
            )
    
    if STATS:
        statistics = StatisticsFactory()
        stats_routine = event_loop.create_task(statistics_report(statistics))
    else:
        statistics = None
    
    try:
        if 'interface' in UDP_LISTENER:
            sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM | socket.SOCK_NONBLOCK )
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(( ALL_INTERFACES, UDP_LISTENER['port'] ))
            multicast_interfaces = struct.pack( structs.ip_mreq.item.format,
                                                int(ip_address(UDP_LISTENER['recipient'])).to_bytes(*BIG_ENDIAN),
                                                int(ip_address(UDP_LISTENER['interface'])).to_bytes(*BIG_ENDIAN)
                                                )
            sock.setsockopt( socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, multicast_interfaces )
            listener = event_loop.create_datagram_endpoint( UDPListener, sock=sock )
        else:
            listener = event_loop.create_datagram_endpoint( UDPListener,
                                            local_addr=( str(UDP_LISTENER['recipient']), UDP_LISTENER['port'] )
                                                            )
        transport,service = event_loop.run_until_complete(listener)
        service.rear_view = RearView(event_loop, DNS_SERVER, RESPONSE_POLICY_ZONE, statistics, CACHE_SIZE,
                                        ADDRESS_CLASSES, GARBAGE_LOGGER, TELEMETRY_ID
                                    )
    except PermissionError:
        print('Permission Denied! (do you need root?)', file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print('{} (did you supply a local address and port?)'.format(e), file=sys.stderr)
        sys.exit(1)
    
    if CONSOLE:
        console_ctxt.service = service

    try:
        event_loop.run_forever()
    except (KeyboardInterrupt, CancelledError):
        pass

    transport.close()

    if PYTHON_IS_311:
        tasks = asyncio.all_tasks(event_loop)
    else:
        tasks = asyncio.Task.all_tasks(event_loop)

    if tasks:
        event_loop.run_until_complete(close_tasks(tasks))
    
    event_loop.close()
    
    return

if __name__ == '__main__':

    if UDP_LISTENER is None:
        print('You MUST define UDP_LISTENER!', file=sys.stderr)
        sys.exit(1)
        
    try:
        UDP_LISTENER['recipient'] = ip_address(UDP_LISTENER['recipient'])
        UDP_LISTENER['port'] = int(UDP_LISTENER['port'])
        if UDP_LISTENER['recipient'].is_multicast:
            UDP_LISTENER['interface'] = UDP_LISTENER['interface']
        else:
            if 'interface' in UDP_LISTENER:
                print('interface specified, but recipient is not multicast', file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        print('UDP_LISTENER error: {}'.format(e), file=sys.stderr)
        sys.exit(1)
            
    main()
    
