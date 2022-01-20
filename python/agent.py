#!/usr/bin/python3
# Copyright (c) 2019-2022 by Fred Morris Tacoma WA
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

"""DNS Agent.

This script takes no arguments.

REQUIRES PYTHON 3.6 OR BETTER

Uses Dnstap to capture A and AAAA responses to specific addresses and send
them to Redis. By default only Client Response type messages are processed
and you'll get better performance if you configure your DNS server to only
send such messages. The expected specification for BIND in named.conf is:

    dnstap { client response; };
    dnstap-output unix "/tmp/dnstap";

If you don't restrict the message type to client responses, a warning message
will be printed for every new connection established.

The PRINT_ Constants
--------------------

The PRINT_... constants control various debugging output. They can be
set to a print function which accepts a string, for example:

    PRINT_THIS = logging.debug
    PRINT_THAT = print
    
Origins, Futures, Credits
-------------------------

This is adapted from the DNS agent which ships with ShoDoHFlo:

  https://github.com/m3047/shodohflo/blob/master/agents/dns_agent.py

In my production environment I actually deploy a hybrid agent which performs
the tasks of both. I hope you can "line up the dials", I've strived not to
make it difficult.
"""

import sys
from os import path
import logging

import asyncio

import dns.rdatatype as rdatatype
import dns.rcode as rcode

from shodohflo.fstrm import Consumer, Server, AsyncUnixSocket
import shodohflo.protobuf.dnstap as dnstap
from shodohflo.statistics import StatisticsFactory

from rearview.db import RearView

PRINT_COROUTINE_ENTRY_EXIT = None
MAX_READ_SIZE = 1024
CONTENT_TYPE = 'protobuf:dnstap.Dnstap'
ADDRESS_CLASSES = { rdatatype.A, rdatatype.AAAA }
GARBAGE_LOGGER = logging.warning

if __name__ == "__main__":
    from configuration import *
else:
    SOCKET_ADDRESS = '/tmp/dnstap'
    LOG_LEVEL = None
    STATS = None
    DNS_SERVER = '127.0.0.1'
    RESPONSE_POLICY_ZONE = 'rpz.example.com'
    CACHE_SIZE = None
    CONSOLE = None
    
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

def hexify(data):
    return ''.join(('{:02x} '.format(b) for b in data))

class DnsTap(Consumer):
    
    def __init__(self, event_loop, statistics, message_type=dnstap.Message.TYPE_CLIENT_RESPONSE):
        """Dnstap consumer.

        Parameters:
        
            message_type: This agent is intended to consume client response
                          messages. You can have it process all messages by
                          setting this to None, but then you'll get potentially
                          strange client addresses logged to Redis.
        """
        self.rear_view = RearView(event_loop, DNS_SERVER, RESPONSE_POLICY_ZONE, statistics, CACHE_SIZE, ADDRESS_CLASSES, GARBAGE_LOGGER)
        self.message_type = message_type
        if STATS:
            self.consume_stats = statistics.Collector("consume")
        return

    def accepted(self, data_type):
        logging.info('Accepting: {}'.format(data_type))
        if data_type != CONTENT_TYPE:
            logging.warn('Unexpected content type "{}", continuing...'.format(data_type))
        # NOTE: This isn't technically correct in the async case, since DnsTap context is
        # the same for all connections. However, we're only ever expecting one connection
        # at a time and this is intended to provide a friendly hint to the user about their
        # nameserver configuration, so the impact of the race condition is minor.
        self.performance_hint = True
        return True
    
    def post_to_rear_view(self, message):
        """Analyze and post to the Rear View database."""
        
        if self.message_type and message.field('type')[1] != self.message_type:
            if self.performance_hint:
                logging.warn('PERFORMANCE HINT: Change your Dnstap config to restrict it to client response only.')
                self.performance_hint = False
            return

        # NOTE: Do these lookups AFTER verifying that we have the correct message type!
        response = message.field('response_message')[1]

        if response.rcode() != rcode.NOERROR:
            return

        self.rear_view.process_answer(response)
        
        return
    
    def process_message(self, message):
        """This can be subclassed to add/remove message processing.
        
        Arguments:
            message: DNS wire format message.
        """
        self.post_to_rear_view(message)
        return

    def consume(self, frame):
        """Consume Dnstap data.
        
        By default the type is restricted to dnstap.Message.TYPE_CLIENT_RESPONSE.
        """
        # NOTE: This function is called in coroutine context, but is not the coroutine itself.
        # Enable PRINT_COROUTINE_ENTRY_EXIT in shodohflo.fstrm if needed.
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> Dnstap.consume()')
        if STATS:
            timer = self.consume_stats.start_timer()

        message = dnstap.Dnstap(frame).field('message')[1]
        self.process_message(message)

        if STATS:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< Dnstap.consume()')
        return True
    
    def finished(self, partial_frame):
        logging.warn('Finished. Partial data: "{}"'.format(hexify(partial_frame)))
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

def main():
    logging.info('DNS Agent starting. Socket: {}  RPZ: {}'.format(SOCKET_ADDRESS, RESPONSE_POLICY_ZONE))

    event_loop = asyncio.get_event_loop()

    if CONSOLE:
        console_ctxt = console.Context()
        console_service = event_loop.run_until_complete(
                asyncio.start_server(
                    console_ctxt.handle_requests,
                    CONSOLE['host'], CONSOLE['port'], 
                    loop=event_loop, limit=MAX_READ_SIZE
                )
            )

    if STATS:
        statistics = StatisticsFactory()
        asyncio.run_coroutine_threadsafe(statistics_report(statistics), event_loop)
    else:
        statistics = None

    dnstap = DnsTap(event_loop, statistics)
    if CONSOLE:
        console_ctxt.dnstap = dnstap

    Server(AsyncUnixSocket(SOCKET_ADDRESS),
           dnstap, event_loop
          ).listen_asyncio()

    return

if __name__ == '__main__':
    main()
    
