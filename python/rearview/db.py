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
"""This is the Telemetry Database.

All async methods belong to the RearView class.
"""

import traceback
import logging

import asyncio
from asyncio import Queue

from time import time
from collections import deque as Deque
from heapq import heappush, heappop

import dns.rdatatype as rdatatype

from . import Heuristics, CircularLogger
from .heuristic import heuristic_func
from .rpz import RPZ

PRINT_COROUTINE_ENTRY_EXIT = None

class Address(object):
    """An IP address, with one or more resolutions."""
    def __init__(self, address):
        self.address = address
        self.resolutions = {}
        self.last_seen = time()
        self.best_resolution = None
        self.best_score = 0.0
        return
    
    def __eq__(self, other):
        return self.address == other.address
        
    def __lt__(self, other):
        return self.address < other.address
            
    def seen(self):
        self.last_seen = time()
        return
        
    def match_resolution(self, matchfunc):
        for resolution in self.resolutions.values():
            if matchfunc(resolution):
                return resolution
        return None
    
    @staticmethod
    def identical_reloaded_resolution(resolution, chain):
            return (
                  resolution.reload_score is not None
              and len(resolution.chain) == len(chain)
              and chain[-1] == resolution.chain[-1]
            )
            
    @staticmethod
    def identical_resolution(resolution, chain):
            return (
                  len(resolution.chain) == len(chain)
              and chain[-1] == resolution.chain[-1]
            )
    
    def add_resolution(self, chain):
        """Add / merge a resolution.
        
        Returns True if added, False if merged.
        
        Special case of resurrected resolutions
        ---------------------------------------
        
        When resolutions are restored from the RPZ, all of the elements of the
        chain will be None except for the last one. If / when a valid answer
        is seen with the same depth and final element is seen, the resurrected
        resolution is merged with it.
        """
        chain_depth = len(chain)
        def matchfunc(resolution):
            return self.identical_reloaded_resolution(resolution, chain)
        match = self.match_resolution(matchfunc)
        if match:
            # Merge them and change the index.
            del self.resolutions[match.chain]
            self.resolutions[chain] = match
            match.chain = chain
            # Leave first_seen alone.
            match.last_seen = time()
            # Leave query trend alone, updating during the reload is unlikely to 
            # be accurate.
            match.query_count += 1
            match.reload_score = None
            return False
            
        self.resolutions[chain] = Resolution(chain)
        return True
    
    def delete_resolution(self, resolution):
        """Delete the resolution, returning True if no more resolutions remain."""
        del self.resolutions[resolution.chain]
        self.best_resolution = None
        self.best_score = 0.0
        return not self.resolutions
    
    def match(self, ptr):
        """Locate the chain ending in ptr.
        
        There could be more than one, in which case (one of the) longest chains
        is returned, preferentially the one loaded from the zone file.
        """
        resolutions = sorted(( (len(chain), chain) for chain in self.resolutions if chain[-1] == ptr ))
        if not resolutions:
            return (None,)
        chain = resolutions[-1]
        for resolution in reversed(resolutions):
            if resolution[0] is None:
                chain = resolution
                break
            if resolution[0] < chain[0]:
                break
        return chain[1]
        
class Resolution(Heuristics):
    """A single resolution for an address."""
    def __init__(self, chain, first_seen=None, last_seen=None, query_count=None, reload_score=None):
        self.chain = chain
        self.first_seen = first_seen is None and time() or first_seen
        self.last_seen = last_seen is None and time() or last_seen
        self.query_count = query_count is None and 1 or query_count
        self.query_trend = 0.0
        self.reload_score = reload_score
        return
    
    def __eq__(self, other):
        return self.chain == other.chain
        
    def __lt__(self, other):
        # There is a corner case where this gets invoked (it's not normal)
        # and if one of the chains was read from the actual zone, then
        # it goes sideways because the intermediates are filled with None
        # on the reload.
        self_chain = self.chain
        other_chain = other.chain
        if None in self_chain:
            self_chain = list(self_chain)
            for i in range(len(self_chain)):
                if self_chain[i] is None:
                    self_chain[i] = ''
            self_chain = tuple(self_chain)
        if None in other_chain:
            other_chain = list(other_chain)
            for i in range(len(other_chain)):
                if other_chain[i] is None:
                    other_chain[i] = ''
            other_chain = tuple(other_chain)
        
        return self_chain < other_chain
        
    def seen(self):
        self.query_trend = 0.9 * self.query_trend + 0.1 * (time() - self.last_seen)
        self.last_seen = time()
        self.query_count += 1
        return
    
class Associator(object):
    
    EVICTION_POOL_BASE_SIZE = 10
    EVICTION_POOL_MULTIPLIER = 1.2
    
    def __init__(self, cache_size, cache_eviction):
        self.cache_size = cache_size
        self.cache_eviction = cache_eviction
        self.cache = Deque()
        self.n_resolutions = 0
        self.addresses = {}
        self.logger = CircularLogger()
        return
    
    def address_objects(self, addresses):
        """Genfunc for Address objects from the Associator given a list of addresses."""
        for address in addresses:
            if address in self.addresses:
                yield self.addresses[address]
        return
    
    def update_resolution(self, address, chain):
        """Adds an address and the resolution, implicitly updating some counters."""
        if address not in self.addresses:
            self.addresses[address] = Address(address)
            self.cache.appendleft(self.addresses[address])
        address = self.addresses[address]
        address.seen()

        if chain not in address.resolutions:
            if address.add_resolution(chain):
                self.n_resolutions += 1
                if self.n_resolutions > self.cache_size:
                    self.cache_eviction()
                return True

        resolution = address.resolutions[chain]
        resolution.seen()
        
        if address.best_resolution and address.best_resolution.chain != chain:
            if heuristic_func(resolution) > address.best_score:
                return True

        return False
    
    def update_resolution_from_rpz(self, address, data):
        """Updates the resolution for an address based on info from the RPZ.
        
        Parameters:
            address (str): The IP address.
            data (TelemetryPackage): Information from the RPZ to use to update
                the telemetry data.
        """
        added = False
        if address not in self.addresses:
            self.addresses[address] = Address(address)
            self.cache.appendleft(self.addresses[address])
            added = True
        address = self.addresses[address]
        if data['last'] > address.last_seen or added:
            address.last_seen = data['last']

        added = False
        chain = tuple( [None] * (data['depth'] - 1) + [data['ptr']] )
        for resolution in address.resolutions.values():
            if Address.identical_resolution(resolution, chain):
                return
        address.add_resolution(chain)
        self.n_resolutions += 1
        if self.n_resolutions > self.cache_size:
            self.cache_eviction()
        resolution = address.resolutions[chain]
        resolution.first_seen = data['first']
        resolution.last_seen = data['last']
        resolution.query_count = data['count']
        resolution.query_trend = data['trend']
        resolution.reload_score = data['score']
        # Omits optional elements such as update.

        return
    
    def do_cache_eviction(self):
        """Performs the actual cache eviction on behalf of the coprocess."""
        self.logger.rotate()
        
        overage = self.n_resolutions - self.cache_size
        target_pool_size = int(overage * self.EVICTION_POOL_MULTIPLIER + self.EVICTION_POOL_BASE_SIZE)
        self.logger['overage'] = overage
        self.logger['target_pool_size'] = target_pool_size

        addresses = []
        candidates = []
        working_pool_size = 0
        while working_pool_size < target_pool_size:
            if not self.cache:
                break
            addresses.append(self.cache.pop())
            for resolution in addresses[-1].resolutions.values():
                # Lowest heuristic scores will be preferred.
                heappush(candidates, (heuristic_func(resolution), len(candidates), addresses[-1], resolution) )
            working_pool_size += len(addresses[-1].resolutions)
        self.logger['working_pool_size'] = working_pool_size
        self.logger['candidates'] = candidates.copy()
        
        affected_addresses = set()
        deleted_addresses = set()
        for i in range(overage):
            score, unused, address, resolution = heappop(candidates)
            affected_addresses.add(address.address)
            if address.delete_resolution(resolution):
                del self.addresses[address.address]
                deleted_addresses.add(address.address)
            self.n_resolutions -= 1
            
        # If there was only one address in the candidate pool and it still has more than
        # enough to be trimmed, we don't rotate.
        recycled = set()
        if len(addresses) == 1 and len(addresses[0].resolutions) >= target_pool_size:
            self.cache.append(addresses[0])
            self.logger['single_address'] = len(addresses[0].resolutions)
        else:
            for address in addresses:
                if address.address not in deleted_addresses:
                    recycled.add(address.address)
                    self.cache.appendleft(address)
            self.logger['recycled_addresses'] = recycled

        self.logger['affected_addresses'] = affected_addresses
        self.logger['deleted_addresses'] = deleted_addresses
        self.logger['n_addresses'] = len(addresses)
        self.logger['n_resolutions'] = self.n_resolutions
        
        return affected_addresses, recycled

class RearView(object):
    """This is the database-like interface.
    
    The architecture is described in __init__.py. You should be able to read
    it with "pydoc3 rearview".
    
    Cache Size
    ----------
    
    Cache size represents the number of associations. RPZ entries can represent multiple
    associations, since associations can be chained. Therefore the number of PTR entries
    in the RPZ should be less than this although the exact number can vary.
    """
    
    DEFAULT_ADDRESS_RECORDS = { rdatatype.A, rdatatype.AAAA }
    DEFAULT_CACHE_SIZE = 10000
    
    def __init__(self, event_loop, dns_server, rpz, statistics=None, cache_size=None,
                 address_record_types=DEFAULT_ADDRESS_RECORDS, garbage_logger=logging.warning):
        self.event_loop = event_loop
        if statistics is not None:
            self.solve_stats = statistics.Collector("solve")
            self.cache_stats = statistics.Collector("cache eviction")
            self.answer_stats = statistics.Collector("process answer")
        else:
            self.solve_stats = self.cache_stats = self.answer_stats = None

        self.address_record_types = address_record_types
        
        self.association_queue = Queue(loop=event_loop)
        #self.eviction_queue = Queue(loop=event_loop)   # Cache evictions are done more or less "real time".
        self.solver_queue = Queue(loop=event_loop)
        self.associations = Associator(cache_size is None and self.DEFAULT_CACHE_SIZE or cache_size,
                                       self.schedule_cache_eviction
                                )
        self.processor_ = self.event_loop.create_task(self.queue_processor())
        self.rpz = RPZ(event_loop, dns_server, rpz, statistics, address_record_types, garbage_logger)
        self.cache_eviction_scheduled = False

        # Kick off a job to load the context with AXFR.
        self.rpz.create_task(self.rpz.load_axfr(self.associations, self.rpz.timer('axfr_stats')))

        return
    
    def solve_(self, address):
        """Internal implementation of solve()."""
    
        # If it doesn't exist then check if it needs to be deleted from the RPZ.
        if address not in self.associations.addresses:
            self.rpz.create_task(self.rpz.delete(address, self.rpz.timer('delete_stats')))
            return None
        address = self.associations.addresses[address]
        resolutions = []
        for resolution in address.resolutions.values():
            heappush(resolutions, (-1*heuristic_func(resolution), resolution) )
        
        score, resolution = heappop(resolutions)
        score *= -1

        # NOTE: This would be the place to do some sort of need-based refresh of the
        #       zonefile metadata driven by events. To get here, we already passed the
        #       test in associations.update_resolution() which replaces the reloaded
        #       chain and so reload_score should be None.
        need_update = (
                address.best_resolution is None
            or  address.best_resolution.chain != resolution.chain
        )
          
        if need_update:
            if resolution is not None:
                address.best_resolution = resolution
                address.best_score = score
            else:
                need_update = False
                logging.error(
                    'solve_(): resolution is None for address:{} with resolutions:{}'.format(
                        address.address, [ k for k in address.resolutions.keys() ]
                    )
                )
            
        return need_update and (address, score) or None

    async def solve(self, address, timer):
        """Solve the name for an address.
        
        Scheduling:
            Queues an RPZ update if the preferred resolution has changed.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> db.RearView.solve()')

        update = self.solve_(address)
        if update:
            update += (self.rpz.timer('update_stats'),)
            self.rpz.create_task(self.rpz.update( *update ))
        
        if self.solve_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< db.RearView.solve()')
        return
        
    async def do_cache_eviction(self, timer):
        """Perform cache eviction.
        
        Scheduling:
            Queues a solver for any address which was the lefthand side of an
                evicted association.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> db.RearView.do_cache_eviction()')

        try:
            affected, recycled = self.associations.do_cache_eviction()
            batch = []
            logger = self.rpz.batch_logger
            # We are making an assumption that recycled is "clean" but maybe that's incorrect
            # and shearing is leaving us with mangled sheep?
            recycled -= affected
            logger.increment('recycled', len(recycled))
            for candidate in self.associations.address_objects(recycled):
                if not candidate.resolutions:
                    logger.increment('recycled_no_resolutions')
                    affected.add(candidate.address)
                    continue
                if candidate.best_resolution is None:
                    logger.increment('recycled_no_best_resolution')
                    affected.add(candidate.address)
                    continue
                logger.increment('recycled_good')
                batch.append( (candidate, heuristic_func(candidate.best_resolution)) )
                
            for address in affected:
                self.solver_queue.put_nowait(
                    self.solve(address, self.solve_stats and self.solve_stats.start_timer() or None)
                )
            # Anything which was kept in the cache but not otherwise affected gets potentially added
            # to the next batch refresh.
            self.rpz.add_to_batch_refresh(batch)
            
            self.cache_eviction_scheduled = False
        except Exception as e:
            traceback.print_exc()
            self.event_loop.stop()

        if self.cache_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< db.RearView.do_cache_eviction()')
        return

    def schedule_cache_eviction(self):
        """Schedule cache eviction.
        
        Scheduling:
            A cache eviction task is created if one does not already exist. There
                is only ever one cache eviction task scheduled, it is not queued
                but it is deferred.
        """
        if self.cache_eviction_scheduled:
            return
        self.cache_eviction_scheduled = True
        self.event_loop.create_task(self.do_cache_eviction(self.cache_stats and self.cache_stats.start_timer() or None))
        return

    def process_answer_(self, response):
        """Internal memory view updater."""

        # associations becomes a reverse lookup.
        associations = {}
        addresses = set()
        for rrset in response.answer:
            qname = rrset.name.to_text().lower()
            for rr in rrset:
                rval = rr.to_text().lower()
                associations[rval] = qname
                if rrset.rdtype in self.address_record_types:
                    addresses.add(rval)

        added = []
        for address in addresses:
            lhs = address
            seen = set()
            chain = []
            while lhs in associations:
                if lhs in seen:
                    break
                seen.add(lhs)
                lhs = associations[lhs]
                chain.append(lhs)
            chain = tuple(chain)
            
            # Add / update the resolution.
            if self.associations.update_resolution(address, chain):      # Implicit: schedules cache eviction.
                added.append(address)
        
        return added
    
    async def process_answer_coro(self, response, timer):
        """Coroutine generating updates to the memory view.
        
        Scheduling:
            Cache eviction.
            Solvers.
        """
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> db.RearView.process_answer_coro()')

        for address in self.process_answer_(response):
            self.solver_queue.put_nowait(
                self.solve(address, self.solve_stats and self.solve_stats.start_timer() or None)
            )
            
        if self.answer_stats:
            timer.stop()
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< db.RearView.process_answer_coro()')
        return

    def process_answer(self, response):
        """Process the supplied DNS answer RRset generating updates to the memory view.
        
        Scheduling:
            Association queue.
        """
        if response.question[0].rdtype not in self.address_record_types:
            return

        self.association_queue.put_nowait(
            self.process_answer_coro(response, self.answer_stats and self.answer_stats.start_timer() or None)
        )

        return

    async def queue_processor(self):
        """Prioritizes associations over solvers."""
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('> db.RearView.queue_processor()')

        while True:
            if not   self.association_queue.empty():
                queue = self.association_queue
                task = self.association_queue.get_nowait()
            elif not self.solver_queue.empty():
                queue = self.solver_queue
                task = self.solver_queue.get_nowait()
            else:
                queue = self.association_queue
                task = await self.association_queue.get()

            try:
                await task
                queue.task_done()
            except Exception as e:
                traceback.print_exc()
                self.event_loop.stop()
                return
            
        # This actually never exits.
        if PRINT_COROUTINE_ENTRY_EXIT:
            PRINT_COROUTINE_ENTRY_EXIT('< db.RearView.queue_processor()')
        return

