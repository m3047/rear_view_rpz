#!/usr/bin/python3
# Copyright (c) 2021-2022 by Fred Morris Tacoma WA
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

"""An interactive console.

This console is enabled by setting for example

    CONSOLE = { 'host':'127.0.0.1', 'port':3047 }

in the configuration file.

The purpose of the console is to allow interactive examination of in-memory
data structures and caches.

The commands are synchronous with respect to the operation of the server, which
is to say the server isn't doing anything else until the underlying operation
has completed. This provides a better snapshot of the state at any given moment,
but can negatively impact data collection from a busy server.

IPv6 addresses are expected to be in the compressed rather than expanded format.

The following commands are supported:

Address to zone correlation
---------------------------

    a2z
    
Perform a crosscheck of the addresses in db.RearView.associations and
rpz.RPZ.contents. Technically the former are addresses (1.2.3.4), while the
latter are PTR FQDNs (4.3.2.1.in-addr.arpa).

Address details
---------------

    addr{ess} <some-address>
    
Get details regarding an address' resolutions and best resolution, and
whether this is reflected in the zone construct. The final line has a bunch
of cryptic legends and numbers. Those are:

* fs first seen delta from now (seconds)
* ls last seen delta from now (seconds)
* qc query count
* qt query trend
* h  heuristic or score


Zone details
------------

    entry <some-address>

Compares what is in the in-memory zone view to what is actually present in
the zone-as-served. NOTE THAT THE ACTUAL DNS REQUEST IS SYNCHRONOUS. This
command causes a separate DNS request to be issued outside of the TCP
connection, which negatively impacts performance of the agent.

Queue depth
-----------

    qd
    
The depths of various processing queues.

Cache eviction queue
--------------------

    cache [<|>] <number>

Display information about the entries (addresses) at the beginning (<)
or end (>) of the queue. The specified number of entries is displayed.

Cache Evictions
---------------

    evict{ions} <number>
    
Displays a logic readout of the most recent "n" cache evictions. There is
an internal limit on the number of evictions which are retained for
review.

Zone Data Refresh
-----------------

    refr{esh} <number>

Displays a logic readout of the most recent "n" zone refresh batches. Resolutions
which survive "sheep shearing" (cache eviction) are scheduled for having updated
information written back to the zone file in batches to minimize performance impacts;
if things are really busy everything may not get refreshed.

Batches go through three phases, at least for logging purposes:

1) The batch is created.
2) The batch is accumulating addresses to update with fresh information.
3) The batch is written to the zone as an update.

Quit
----

    quit
    
Ends the console session; no other response occurs.

Response Codes
--------------

Each response line is prepended by one of these codes and an ASCII space.

    200 Success, single line output.
    210 Success, beginning of multi-line output.
    212 Success, continuation line.
    400 User error / bad request.
    500 Not found or internal error.
"""
import time
import logging
import asyncio
from dns.resolver import Resolver
from .rpz import reverse_to_address, address_to_reverse
from .heuristic import heuristic_func

class Request(object):
    """Everything to do with processing a request.
    
    The idiom is generally Request(message).response and then do whatever is sensible
    with response. Response can be nothing, in which case there is nothing further
    to do.
    """

    COMMANDS = dict(a2z=1, address=2, entry=2, qd=1, cache=3, evictions=2, refresh=2, quit=1)
    ABBREVIATED = { k for k in COMMANDS.keys() if len(k) > 4 }

    def __init__(self, message, dnstap):
        self.rear_view = dnstap.rear_view
        self.response = ""
        self.quit_session = False
        request = message.strip().split()
        if not request:
            return
        self.dispatch_request(request)
        return
    
    def validate_request(self, request):
        verb = request[0].lower()
        if len(verb) >= 4:
            for v in self.ABBREVIATED:
                if v.startswith(verb):
                    verb = request[0] = v
        if verb not in self.COMMANDS:
            return 'unrecognized command'
        if len(request) != self.COMMANDS[verb]:
            return 'improperly formed request'
        return ''

    def dispatch_request(self, request):
        """Called by __init__() to dispatch the request."""
        failed = self.validate_request(request)
        if failed:
            code,response = self.bad_request(failed)
        else:
            verb = request[0].lower()
            code,response = getattr(self, verb)(request)
            if self.quit_session:
                response = ''
                return
        
        if len(response) == 1:
            self.response = '{} {}\n'.format(code, response[0])
        else:
            self.response = '\n'.join(
                    ( '{} {}'.format( line and 212 or 210, text )
                      for line,text in enumerate(response)
                    )
                ) + '\n'
        return
    
    def a2z(self, request):
        """a2z"""
        addresses = sorted(self.rear_view.associations.addresses.keys())
        zonekeys = sorted(
                [
                    ( reverse_to_address( zk ), zk )
                    for zk in self.rear_view.rpz.contents.keys()
                ]
        )

        response = []
        addrs = 0
        zks = 0
        while addresses or zonekeys:
            if   addresses[0] < zonekeys[0][0]:
                response.append('< {}'.format(addresses.pop(0)))
                addrs += 1
            elif addresses[0] > zonekeys[0][0]:
                response.append('> {}'.format(zonekeys.pop(0)[1]))
                zks += 1
            else:
                del addresses[0]
                del zonekeys[0]
                
        return 200, response

    def address(self, request):
        """addr{ess} <some-address>
        
        Kind of a hot mess, but here's what's going on:
        
        * If there's no best resolution it could be that's because it was loaded
          from the actual zone file, which we can tell if it has a depth > 1 and
          the first entry is None.
          
        * Other things.
        """
        addr = request[1]
        addresses = self.rear_view.associations.addresses
        if addr not in addresses:
            return 500, ['not found']
        
        addr_rec = addresses[addr]
        best = addr_rec.best_resolution

        zone_key = address_to_reverse(addr)
        if zone_key in self.rear_view.rpz.contents:
            ptr = self.rear_view.rpz.contents[zone_key].ptr
            ptr_chain = addr_rec.match(ptr)
        else:
            ptr = ptr_chain = None

        if best is None:
            best_chain = None
        else:
            best_chain = best.chain

        response = []
        
        if best is None:
            if not (ptr_chain and ptr_chain[0] == None):
                response.append('! no best resolution')
        else:
            if best.chain not in addr_rec.resolutions:
                response.append('! best resolution not in chains')
        
        for resolution in sorted(addr_rec.resolutions.values()):
            response.append(
                '{} {}'.format(
                    (best is not None and best == resolution) and '***' or '   ',
                    resolution.chain
                )
            )
            now = time.time()
            response.append(
                '        fs:{:0.1f} ls:{:0.1f} qc:{:d} qt:{:0.1f} h:{:0.1f}'.format(
                    resolution.first_seen-now, resolution.last_seen-now, resolution.query_count, resolution.query_trend,
                    heuristic_func(resolution)
                )
            )
        
        zone_key = address_to_reverse(addr)
        if zone_key in self.rear_view.rpz.contents:
            response.append('-> {}'.format(self.rear_view.rpz.contents[zone_key].ptr))
        else:
            response.append('-> MISSING FROM ZONE CONTENTS')

        return 200, response

    def entry(self, request):
        """entry <some-address>"""
        addr = request[1]
        zone_key = address_to_reverse(addr)
        rpz = self.rear_view.rpz
        contents = rpz.contents
        
        if zone_key not in contents:
            memory_value = '** MISSING **'
        else:
            memory_value = contents[zone_key].ptr
        
        try:
            resolver = Resolver()
            resolver.nameservers = [rpz.server]
            answer = resolver.query(zone_key + '.' + rpz.rpz, 'PTR', source=rpz.server)
            server_value = answer[0].target.to_text().rstrip('.')
        except Exception as e:
            server_value = '** ' + type(e).__name__ + ' **'

        return 200, ['{} {}'.format(memory_value, server_value)]

    def qd(self, request):
        """qd"""
        response = []
        response.append(
            'association: {}'.format(self.rear_view.association_queue.qsize())
        )
        response.append(
            'solver: {}'.format(self.rear_view.solver_queue.qsize())
        )
        response.append(
            'eviction: {}'.format(self.rear_view.cache_eviction_scheduled)
        )
        response.append(
            'zone updates: {}'.format(self.rear_view.rpz.task_queue.qsize())
        )
        return 200, response
    
    def cache(self, request):
        """cache [<|>] <number>"""
        which_end = request[1]
        if which_end not in '<>':
            return self.bad_request('expected "<" or ">"')

        try:
            n_addrs = int(request[2])
            if n_addrs < 1:
                raise ValueError
        except:
            return self.bad_request('expected a positive integer value')

        associations = self.rear_view.associations
        response = []

        res_addrs = sum((len(a.resolutions) for a in associations.addresses.values()))
        res_cache = associations.n_resolutions
        response.append(
            'Actual Resolutions in cache: {}  actual: {}'.format(res_cache, res_addrs)
        )

        cache = associations.cache
        if n_addrs > len(cache):
            n_addrs = len(cache)
        if which_end == '<':
            i = 0
            inc = 1
        else:
            i = -1
            inc = -1
        while n_addrs:
            address = cache[i]
            response.append(
                '{} ({})'.format(address.address, len(address.resolutions))
            )
            i += inc
            n_addrs -= 1
            
        return 200, response
    
    def evictions(self, request):
        """evictions <number>"""
        try:
            n_evicts = int(request[1])
            if n_evicts < 1:
                raise ValueError
        except:
            return self.bad_request('expected a positive integer value')

        logger = self.rear_view.associations.logger
        response = []
        
        if n_evicts > len(logger):
            n_evicts = len(logger)
        
        base = n_evicts * -1
        for n in range(n_evicts):
            entry = logger.log[base + n]
            
            response.append('** {:0.3f} **'.format(entry.timestamp - time.time()))
            
            response.append(
                'Resolutions:'
            )
            response.append(
                '     Overage:{:>6d}      Target:{:>6d}      Working:{:>6d}      N After:{:>6d}'.format(
                    *[entry[k] for k in 'overage target_pool_size working_pool_size n_resolutions'.split()]
                )
            )
            response.append(
                'Addresses:'
            )
            n_addresses = entry['n_addresses']
            response.append(
                '    Selected:{:>6d}  {:>10s}:{:>6d}      Affected:{:>6d}     Deleted:{:>6d}'.format(
                    n_addresses,
                    (n_addresses > 1 and 'Recycled' or 'Single'),
                    (n_addresses > 1 and len(entry['recycled_addresses']) or entry['single_address']),
                    len(entry['affected_addresses']), len(entry['deleted_addresses'])
                )
            )
            response.append(
                'Affected:'
            )
            response += ['    {}'.format(k) for k in sorted(entry['affected_addresses'])]
            response.append(
                'Deleted:'
            )
            response += ['    {}'.format(k) for k in sorted(entry['deleted_addresses'])]

            if n_addresses > 1:
                response.append(
                    'Recycled:'
                )
                response += ['    {}'.format(k) for k in sorted(entry['recycled_addresses'])]
            
            response.append(
                'Candidates:'
            )
            for candidate in sorted(entry['candidates']):
                response.append(
                    '    {:>8.1f}    {:>3d}   {}'.format(candidate[0], candidate[1], candidate[2].address)
                )
                response.append(
                    '          {}'.format(candidate[3].chain)
                )
            
        return 200, response
    
    def refresh(self, request):
        """refresh <number>"""
        try:
            n_updates = int(request[1])
            if n_updates < 1:
                raise ValueError
        except:
            return self.bad_request('expected a positive integer value')

        logger = self.rear_view.rpz.batch_logger
        response = []
        
        if n_updates > len(logger):
            n_updates = len(logger)
        
        
        base = n_updates * -1
        for n in range(n_updates):
            # NOTE: The state will determine what can be displayed, and in turn is determined
            #       by the keys which are available if you read rpz.BatchLogger.
            entry = logger.log[base + n]
            state = logger.state(base + n)
            

            response.append('** {:0.3f} {} **'.format(entry.timestamp - time.time(), state.upper()))

            if logger.STATE[state] <= logger.STATE['accumulating']:
                batch_size = (
                    logger.STATE[state] <= logger.STATE['complete']
                    and 'Batch Size:{:>4d}'.format(entry['batch_size'])
                    or  ''
                )
                response.append(
                    'Add Calls:{:>4d}    Total to Process:{:>4d}    {}'.format(
                        entry['add_calls'], entry['to_process'], batch_size
                    )
                )
                good = entry.get('recycled_good', 0)
                no_best = entry.get('recycled_no_best_resolution', 0)
                no_resolutions = entry.get('recycled_no_resolutions', 0)
                # TODO: This is looking for mangled sheep. It can be removed at some point
                #       in the future when nobody remembers what this is about.
                if (good + no_best + no_resolutions) != entry.get('recycled', 0):
                    response.append('Sheep are disappearing! (hopefully nobody sees this)')
                #
                response.append(
                    'Recycled   Good:{:>4d}   No Best:{:>4d}  No Resolutions:{:>4d}'.format(
                        good, no_best, no_resolutions
                    )
                )
            if logger.STATE[state] <= logger.STATE['complete']:
                response.append(
                    'RCode:{:>3d}      Wire Size Request:{:>5d}   Response:{:>4d}'.format(
                        entry['update_rcode'], entry['wire_req_bytes'], entry['wire_resp_bytes']
                    )
                )
            if logger.STATE[state] <= logger.STATE['writing']:
                processing = (
                    logger.STATE[state] <= logger.STATE['complete']
                    and 'Processing:{:>0.3f}'.format(entry['completion_timestamp']-entry['threshold_timestamp'])
                    or ''
                )
                response.append(
                    'Elapsed   Accumulating:{:>0.3f}  {}'.format(
                        entry['threshold_timestamp'] - entry.timestamp, processing
                    )
                )
            
        return 200, response
                
    def quit(self, request):
        """quit"""
        self.quit_session = True
        return 200, []

    def bad_request(self, reason):
        """A bad/unrecognized request."""
        return 400, [reason]

class Context(object):
    """Context for the console."""
    def __init__(self, dnstap=None):
        """Create a context object.
        
        dnstap is normally set in code, but we pass it in with a default of
        None to make its presence known.
        """
        self.dnstap = dnstap
        return
    
    async def handle_requests(self, reader, writer):
        remote_addr = writer.get_extra_info('peername')
        while True:
            writer.write('# '.encode())
            data = await reader.readline()
            try:
                message = data.decode()
            except UnicodeDecodeError:
                logging.warn('Invalid characters in stream (UnicodeDecodeError), closing connection for {}'.format(remote_addr))
                break
            if not message:
                break

            request = Request(message, self.dnstap)
            if request.quit_session:
                break
            if not request.response:
                continue

            writer.write(request.response.encode())
            await writer.drain()

        writer.close()
        return
