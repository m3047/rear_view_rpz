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

"""The Database-Like Interface.

The Agent maintains an in-memory database for context. At startup it queries named (BIND)
using AXFR to build an in-memory view of the RPZ. From that point forward, updates
drive dynamic updates to the RPZ while keeping the in-memory copy in sync.

DATABASE CONCEPTS
-----------------

General Architecture
--------------------

The general architecture is two datasets which are kept in sync:

* Telemetry View: A view which is performant to update based on DnsTap telemetry.
* RPZ Mirror: A (more or less) mirror of what's in the RPZ.

The telemetry view is based on atomic associations rather than the final association.
In the telemetry view we have:

    www.example.com --- CNAME --> services.example.net --- A --> 10.10.10.10

In the RPZ mirror there is only the final relationship:

    10.10.10.10 --> www.example.com

although some additional metadata is stored in an associated TXT record.
    
"Left hand side" and "Right hand side"
--------------------------------------

Given the relationships above, www.example.com is always the left hand side and
10.10.10.10 is always the right hand side. We are in interested in the inverse
relationhips.

In the DNS we refer to the left hand side as the qname (query name) and the right hand
side as the rr or rname (resolving record or resolving name). In the DNS, for the PTR
records we generate, this relationship will be reversed and the address (actually an
fqdn constructed from the address) will be the qname and the fqdn will be the rname.

Because our ultimate intent is to create PTR records, the "lhs" (left hand side) of
an edge is the address and the "rhs" (right hand side) is the boundary fqdn.
    
Metadata
--------
    
The metadata which is maintained in the two datasets also reflects the purpose.

* Telemetry View is indexed by address, and each address has any number of associated
        resolutions. The resolutions have metadata which is utilized by the heuristics.
* RPZ TXT records contain first seen, query count, heuristic score.

Heuristics
----------

There is no universal best answer as to which resolution to select from when fabricating
a PTR record. We provide a sample heuristic function. We provide a number of heuristics
for your heuristic function to consult:

* number_of_labels -- number of labels in the final fqdn
* depth_of_chain -- number of cnames in the resolution chain
* first_seen_delta -- first seen, delta from now
* last_seen_delta -- last seen, delta from now
* query_rate -- queries per second
* query_trend -- are queries increasing, decreasing, or remaining the same?

DYNAMIC UPDATING
----------------

The general, overall update process is something like the following and there is
scheduling to ensure that one step doesn't begin until the prior one completes.

0) Context Initialization

When the RearView class is instantiated, it kicks off a job to use AXFR to query
BIND and populate the context database.

1) Address and CNAME associations in DnsTap telemetry

The process starts when DnsTap telemetry arrives. For each address (address ->
fqdn) or cname (fqdn -> fqdn) association, the following is performed:

    IF the association exists THEN
        Update ttl.
        DONE
    END IF
    IF the association doesn't exist THEN
        Add it.
    END IF
    Add the association.
    Schedule a solver for the address.
    If number of resolutions now exceeds the cache size THEN
        Schedule cache eviction.
    END IF
    
2) Cache Eviction

There is a fixed cache size for resolutions. If nodes were added and the cache size
has been previously reached, we now need to delete the overlimit. A two step eviction
strategy is utilized which is intended to penalize addresses with very large numbers
of resolutions.

    Target number to select from = overlimit * 1.2 + 10

    addresses = address to which the resolution was added
    WHILE total number of resolutions < target number to select from
        add an address from the tail of the eviction queue
    END WHILE
    
    FOR EACH OF THE overlimit resolutions which have the worst heuristic scores
        delete the resolution
        IF a solver hasn't been scheduled THEN
            Schedule a solver for the address.
        END IF
    
    IF  there was more than one address
     OR number of resolutions associated with the address < target number to select from
    THEN
        rotate the addresses to the beginning of the eviction queue
    ELSE
        replace the (single) address at the tail of the eviction queue
    END IF

3) Solvers

The prior step queues up solvers for addresses. When a solver runs the following
process is followed:

    Identify the best solution bast on heuristics.
    IF the solution has changed THEN
        Schedule an RPZ update.
    END IF
    
4) RPZ Updates

In addition to the "legitimate" PTR records, the RPZ contains a TXT record for each
PTR record with the heuristic score and some other metadata.

    IF this is a deletion THEN
        process it
        DONE
    END IF
    IF no RPZ entry exists THEN
        create A ptr entry
    END IF
    IF (distance OR rhs) has changed THEN
        update the TXT recrd
    END IF

"""

import time

class Heuristics(object):
    """This is a mixin used when creating the db.Resolution class.
    
    As such it expects self to be a db.Resolution instance. To make that explicit
    we've adopted it in the naming of methods here.
    """

    @property
    def number_of_labels(res_obj):
        """Number of labels in the final fqdn."""
        return len(res_obj.chain[-1].rstrip('.').split('.'))

    @property
    def depth_of_chain(res_obj):
        """Number of cnames in the resolution chain."""
        return len(res_obj.chain)
    
    @property
    def first_seen_delta(res_obj):
        """First seen, delta from now."""
        return time.time() - res_obj.first_seen
    
    @property
    def last_seen_delta(res_obj):
        """Last seen, delta from now."""
        return time.time() - res_obj.last_seen

    @property
    def query_rate(res_obj):
        """Queries per second."""
        return res_obj.query_count / (time.time() - res_obj.first_seen)
    
    #@property
    #def query_trend(res_obj):
        #"""Are queries increasing, decreasing, or remaining the same?"""
        #return res_obj.query_trend

class CountingDict(dict):
    """Counts the values of its keys."""
    
    def increment(self, k, i=1):
        """Returns the incremented value."""
        if k not in self:
            self[k] = i
            return
        self[k] += i
        return self[k]

class CircularLogger(object):
    """Part of internal instrumentation.
    
    Each entry in the logger is a CountingDict. The currently active logging
    context can be accessed directly on the object. Note that increment() only
    works if what's intended to be stored for that key is an integer!
    
    The log itself is the attribute log. The newest entry is at [-1]
    and the oldest is at [0]
    """
    LIMIT = 10
    def __init__(self, limit=LIMIT):
        self.limit = limit
        self.log = []
        return
    
    def rotate(self):
        """Rotate the log.
        
        FLUENT: returns the object.
        
        The entry at [0] is deleted and a new CountingDict is appended to log.
        """
        if len(self.log) >= self.limit:
            del self.log[0]
        self.log.append(CountingDict())
        self.log[-1].timestamp = time.time()
        return self
    
    def increment(self, k, i=1):
        """self.log[-1].increment(k)"""
        return self.log[-1].increment(k,i)
    
    def __getitem__(self, k):
        return self.log[-1][k]
    
    def __setitem__(self, k, v):
        self.log[-1][k] = v
        return

    def __len__(self):
        return len(self.log)
    
