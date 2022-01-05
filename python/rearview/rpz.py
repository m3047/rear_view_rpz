#!/usr/bin/python3
# Copyright (c) 2021 by Fred Morris Tacoma WA
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

"""This is the RPZ view.

We try to keep what's in the telemetry view and what's actually being served by
the zone in sync.
"""

import traceback
import logging

from time import time

import asyncio
from asyncio import Queue

import socket
import re

import dns.message
import dns.rdatatype as rdatatype
import dns.rcode as rcode
import dns.query
from dns.exception import DNSException

# The class has a different name (UpdateMessage) in dnspython 2.x. This is for
# version 1.x.
from dns.update import Update as Updater

PRINT_COROUTINE_ENTRY_EXIT = None

TTL = 600

class Connection(object):
    """Manages a queue of requests and replies."""
    def __init__(self, event_loop, server, rpz, statistics):
        self.event_loop = event_loop
        self.server = server
        self.rpz = rpz
        self.keep_open = False
        self.reader_ = None
        self.writer_ = None
        if statistics:
            self.request_stats = statistics.Collector('dns request')
        else:
            self.request_stats = None
        return
    
    def close(self):
        if self.writer_ is None:
            return
        self.writer_.close()
        self.reader_ = self.writer_ = None
        return
    
    def timer(self, collection):
        """Helper for marshalling coroutines."""
        collection = getattr(self, collection)
        return collection and collection.start_timer() or None

    async def make_request(self, request=None, timer=None):
        """Sends the request and returns the response.
        
        Context is a TCP connection. Request and response are the naked
        request / response bytes respectively. Over the wire, this method
        handles the prepended length bytes.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> rpz.Connection.make_request()')

        # Open a connection if necessary.
        if self.writer_ is None and request is not None:
            self.reader_, self.writer_ = await asyncio.open_connection(self.server, 53)
            
        # Send the request, and await a response.
        if request is not None:
            self.writer_.write( len(request).to_bytes(2, byteorder='big') + request )
            await self.writer_.drain()

        response_length = int.from_bytes( await self.reader_.read(2), byteorder='big')
        response = b''
        while response_length:
            resp = await self.reader_.read(response_length)
            if not len(resp):
                break
            response += resp
            response_length -= len(resp)

        # Close it? Ok, close it.
        if not self.keep_open:
            self.close()
        
        if self.request_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< rpz.Connection.make_request()')
        return response

class ZoneEntry(object):
    """All data for an FQDN.
    
    This means the PTR record.
    """
    TXT_RECORD_REFRESH_MINUTES = 30
    
    def __init__(self, name):
        self.name = name
        self.ptr = None
        self.last_refresh = time()
        return
    
    def update(self, rtype, rval):
        if rtype == rdatatype.PTR:
            self.ptr = rval
            self.last_refresh = time()
        return
    
    def needs_refresh(self):
        """Returns True if the TXT record needs to be refreshed."""
        return time() - self.last_refresh > self.TXT_RECORD_REFRESH_MINUTES
    
class ZoneContents(dict):
    """This is a dictionary of zone entries.
    
    The key is the name and the value is a ZoneEntry.
    """
    def update_entry(self, rname, rtype, rval):
        rname = rname.split('.in-addr.arpa')[0] + '.in-addr.arpa'
        if rname not in self:
            self[rname] = ZoneEntry( rname )
        self[rname].update(rtype, rval)
        return
    
class EndOfZone(EOFError):
    pass

class TelemetryPackage(dict):
    """When we load from the RPZ this is what we get."""
    CONVERSIONS = dict(
        ptr = lambda x:x,
        depth = lambda x:int(x),
        first = lambda x:float(x),
        last = lambda x:float(x),
        count = lambda x:int(x),
        trend = lambda x:float(x),
        score = lambda x:float(x)
    )
    COMPLETE = set(CONVERSIONS.keys())

    def complete(self):
        return self.COMPLETE <= set(self.keys())

    def set(self, k, v):
        self[k] = self.CONVERSIONS[k](v)
        return
        
def reverse_to_address(reverse_ref):
    """Take the reverse lookup qname format and extract the address."""
    return '.'.join(reversed(reverse_ref.split('.in-addr.arpa')[0].split('.')))

def address_to_reverse(address):
    """Take the address and construct the reverse lookup format."""
    return '{}.in-addr.arpa'.format('.'.join(reversed(address.split('.'))))
    
class RPZ(object):
    
    RDTYPES = set((rdatatype.PTR, rdatatype.TXT))
    BYTE_REGEX = '(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})'
    V4ADDR_REGEX = '[.]'.join((BYTE_REGEX,) * 4)
    REV4_RE = re.compile(V4ADDR_REGEX + '[.]in-addr[.]arpa', re.ASCII|re.IGNORECASE)
    # TODO: Ip6 here
    
    def __init__(self, event_loop, server, rpz, statistics, address_record_types, garbage_logger):
        self.event_loop = event_loop
        self.server = server
        self.rpz = rpz.lower().rstrip('.') + '.'
        self.address_record_types = address_record_types
        self.garbage_logger = garbage_logger
        self.task_queue = Queue(loop=event_loop)
        self.processor_ = self.event_loop.create_task(self.queue_processor())
        self.conn_ = Connection(event_loop, server, rpz, statistics)
        self.contents = ZoneContents()
        if statistics:
            self.axfr_stats = statistics.Collector("rpz axfr")
            self.delete_stats = statistics.Collector("rpz delete")
            self.update_stats = statistics.Collector("rpz update")
        else:
            self.axfr_stats = self.delete_stats = self.update_stats = None
        return
    
    async def close(self):
        """Cleanup, such as cancelling the queue processor."""
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> rpz.RPZ.close()')

        self.conn_.close()

        self.processor_.cancel()
        await self.processor_

        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< rpz.RPZ.close()')
        return
    
    def timer(self, collection):
        """Helper for marshalling coroutines."""
        collection = getattr(self, collection)
        return collection and collection.start_timer() or None
    
    def create_task(self, task):
        """Create a task in the RPZ queue."""
        self.task_queue.put_nowait(task)
        return
    
    def process_zone_rec(self, qname, rtype, rval, telemetry_view):
        """Updates the memory view from a zone rec.
        
        This updates both the RPZ view and the telemetry view.
        """
        if not (rdatatype.A in self.address_record_types
            and self.REV4_RE.match(qname)
            # TODO: Ip6 here.
            ):
            if self.garbage_logger:
                self.garbage_logger('unexpected qname {} in zonefile on load'.format(qname))
            return
        
        self.contents.update_entry(qname, rtype, rval)

        # For telemetry updates, wait until we have all of the info for an update.
        if qname not in self.telemetry_data_cache:
            self.telemetry_data_cache[qname] = TelemetryPackage()

        if   rtype == rdatatype.PTR:
            self.telemetry_data_cache[qname].set( 'ptr', rval )
        elif rtype == rdatatype.TXT:
            for kv in rval.strip('"').split(','):
                self.telemetry_data_cache[qname].set( *kv.split('=',1) )
                    
        if not self.telemetry_data_cache[qname].complete():
            return
        
        # We have all of the requisite data...
        telemetry_view.update_resolution_from_rpz(
            reverse_to_address(qname.replace(self.rpz, '').lower()),
            self.telemetry_data_cache[qname]
        )
        
        # Done.
        del self.telemetry_data_cache[qname]
            
        return
        
    async def load_axfr_(self, associations):
        """Internal method."""
        keep_open = self.conn_.keep_open
        self.conn_.keep_open = True
        
        # Construct the AXFR request and send it.
        req = dns.message.make_query(self.rpz, 'AXFR')
        wire_req = req.to_wire()
        wire_resp = await self.conn_.make_request(wire_req, self.conn_.timer('request_stats'))
        resp = dns.message.from_wire(wire_resp, xfr=True)
        if resp.rcode() != rcode.NOERROR:
            self.global_error('axfr - rcode', resp)
            return
        answer = resp.answer

        # First record has to be an SOA record.
        if answer[0].rdtype != rdatatype.SOA:
            self.global_error('axfr - no soa', resp)
            return
        if answer[0].name.to_text().lower() != self.rpz:
            self.global_error('axfr - wrong soa', resp)
            return
        answer = answer[1:]
        
        self.telemetry_data_cache = {}
        # Process and update the in-memory view.
        try:
            while True:                
                for rrset in answer:
                    name = rrset.name.to_text().lower()
                    if rrset.rdtype == rdatatype.SOA and name == self.rpz:
                        raise EndOfZone
                    if rrset.rdtype not in self.RDTYPES:
                        continue
                    for rr in rrset:
                        self.process_zone_rec(name, rrset.rdtype, rr.to_text(), associations)
                wire_resp = await self.conn_.make_request(None, self.conn_.timer('request_stats')) # Get another response, no question asked.
                resp = dns.message.from_wire(wire_resp, xfr=True)
                if resp.rcode() != rcode.NOERROR:
                    self.global_error('axfr - rcode 2', resp)
                    break
                answer = resp.answer
                
        except EndOfZone:
            pass
        self.telemetry_data_cache = None
        
        # Close the connection if we jimmied it open.
        self.conn_.keep_open = keep_open
        if not keep_open and self.task_queue.empty():
            self.conn_.close()
        
        return

    async def load_axfr(self, associations, timer):
        """Use AXFR to load the RPZ context and populate associations.
        
        associations is a db.Associator object.
        
        An AXFR results in one or more query responses being sent by the server.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> rpz.RPZ.load_axfr()')

        await self.load_axfr_(associations)
        
        if self.axfr_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< rpz.RPZ.load_axfr()')
        return
    
    async def delete_(self, address):
        """Internal method."""
        qname = address_to_reverse(address)
        if qname not in self.contents:
            return

        # Remove it from the memory view.
        del self.contents[qname]
        
        # Remove it from the zone.
        qname +=  '.' + self.rpz
        update = Updater(self.rpz)
        update.delete(qname)
        
        wire_req = update.to_wire()
        wire_resp = await self.conn_.make_request(wire_req, self.conn_.timer('request_stats'))
        resp = dns.message.from_wire(wire_resp)
        
        if resp.rcode() != rcode.NOERROR:
            self.global_error('delete', resp)
        
        return
    
    async def delete(self, address, timer):
        """Remove the specified address from the RPZ.
        
        The address is a string.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> rpz.RPZ.delete()')

        await self.delete_(address)
        
        if self.delete_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< rpz.RPZ.delete()')
        return

    async def update_(self, address, score):
        """Internal method."""
        # Get the expected resolution. When this is called by RearView.solve() the
        # best resolution has been determined.
        if not address.best_resolution:
            logging.error(
                'update_(): best_resolution is None for address:{} with resolutions:{}'.format(
                    address.address, [ k for k in address.resolutions.keys() ]
                )
            )
            return
        qname = address_to_reverse(address.address)
        ptr_value = address.best_resolution.chain[-1].rstrip('.') + '.'
        zone_entry = self.contents.get(qname)
        if (  zone_entry is not None
          and zone_entry.ptr is not None
          and ptr_value == zone_entry.ptr
          and not zone_entry.needs_refresh()
           ):
            return
        
        self.contents.update_entry(qname, rdatatype.PTR, ptr_value)

        qname = qname + '.'  + self.rpz
        update = Updater(self.rpz)
        update.delete(qname)
        update.add(qname, TTL, rdatatype.PTR, ptr_value)
        update.add(qname, TTL, rdatatype.TXT,
            ','.join((
                '{}={}'.format( k, v )
                for k, v in
                ( ('depth', len(address.best_resolution.chain)),
                  ('first', address.best_resolution.first_seen),
                  ('last',  address.best_resolution.last_seen),
                  ('count', address.best_resolution.query_count),
                  ('trend', address.best_resolution.query_trend),
                  ('score', score)
                )
            ))
        )
        
        wire_req = update.to_wire()
        wire_resp = await self.conn_.make_request(wire_req, self.conn_.timer('request_stats'))
        try:
            resp = dns.message.from_wire(wire_resp)
        except DNSException as e:
            logging.error('Invalid DNS response to ({} -> {})'.format(address.address, ptr_value))
            self.conn_.close()
            return
        
        if resp.rcode() != rcode.NOERROR:
            self.global_error('update', resp)
        
        return

    async def update(self, address, score, timer):
        """Add / update the specified address in the RPZ.
        
        The address is a db.Address object.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> rpz.RPZ.update()')
            
        await self.update_(address, score)

        if self.update_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< rpz.RPZ.update()')
        return
        
    async def queue_processor(self):
        """Processes the task queue, in coordination with the Connection."""
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> rpz.RPZ.queue_processor()')

        while True:
            task = await self.task_queue.get()
            self.conn_.keep_open = not self.task_queue.empty()
            try:
                await task
                self.task_queue.task_done()
            except Exception as e:
                traceback.print_exc()
                self.event_loop.stop()
                return

        # This actually never exits.
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< rpz.RPZ.queue_processor()')
        return
    
    def global_error(self, text, response):
        """Called when an error related to processing DNS requests occurs.
        
        All this does at the moment is log the text, but it can be overridden
        if needed.
        """
        logging.error(text)
        return
    