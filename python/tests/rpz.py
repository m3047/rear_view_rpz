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
"""Running the RPZ tests requires an appropriately configured copy of BIND.

The zone needs to:

    * be queryable
    * allow zone transfers
    * allow dynamic updates

The named.conf options / ACL definitions to accomplish this are:
    
    acl testnets {
        localhost;
    };
    
    options {
        masterfile-format text;

        recursion yes;
        allow-query { testnets; };
        allow-update { testnets; };
        allow-transfer { testnets; };
        provide-ixfr yes;
        request-ixfr yes;
    };

The following zone needs to be defined in named.conf, although it doesn't
need to be declared as an RPZ:

    zone "test.rpz.example.com" {
        type master;
        file "test.rpz.example.com.fwd";
    };
    
In a half-hearted nod to security, we presume that the server listens
(only) on the loopback interface.

Use the following as the initial (text) contents of the zone file
test.rpz.example.com.fwd:

    $ORIGIN .
    $TTL 600        ; 10 minutes
    TEST.RPZ.EXAMPLE.COM IN SOA  EXAMPLE.COM. EXAMPLE.EXAMPLE.COM. (
                                    1          ; serial
                                    600        ; refresh (10 minutes)
                                    60         ; retry (1 minute)
                                    86400      ; expire (1 day)
                                    600        ; minimum (10 minutes)
                                    )
                            NS   NS.EXAMPLE.COM.

NOTE: The test harness makes an attempt to clean up after tests, but
records can end up hanging around and fouling things up. Restore a
fresh copy of the zonefile before running tests!

"""

import sysconfig

PYTHON_IS_311 = int( sysconfig.get_python_version().split('.')[1] ) >= 11

import sys
import unittest
from unittest import TestCase
from unittest.mock import Mock, patch

import asyncio

if PYTHON_IS_311:
    from asyncio import CancelledError
else:
    from concurrent.futures import CancelledError

import socket

import dns.message
from dns.update import Update as Updater
import dns.resolver
import dns.rdatatype as rdatatype
import dns.rcode as rcode

if '..' not in sys.path:
    sys.path.insert(0,'..')

import rearview.rpz as rpz
from rearview.db import Associator, Address, RearView

TEST_ZONE = 'test.rpz.example.com'
SERVER_ADDRESS = '127.0.0.1'

BIG_ENDIAN = { 'byteorder':'big', 'signed':False }

TIME_NOW = 23456789.54321
TTL = 600
TEST_RECORDS = (
        (   '4.3.2.1.in-addr.arpa',       'foo.example.com.',
            dict(
                depth = 1,
                first = TIME_NOW,
                last  = TIME_NOW,
                count = 42,
                trend = 2.0,
                score = 4.2
            ), '1.2.3.4'
        ),
        (   '8.7.6.5.in-addr.arpa',       'bar.example.com.',
            dict(
                depth = 3,
                first = TIME_NOW,
                last  = TIME_NOW,
                count = 42,
                trend = 2.0,
                score = 4.2
            ), '5.6.7.8'
        )
    )
NEW_SCORE = 7.7
NEW_CHAIN = ('fizz.example.com.', 'fuzz.example.com.', 'buzz.example.com.', 'boom.example.com.') 

class ZoneCleanupFailure(Exception):
    """Cleaning up the zone in tearDown() failed.
    
    See if you need to restore the original zone file before re-running
    these tests.
    """
    pass

class ZoneUpdateFailure(Exception):
    """A zone update as part of test orchestration failed."""
    pass

class Resolver(object):
    
    ATTRS = { 'resolver' }

    def __init__(self):
        self.resolver = dns.resolver.Resolver()
        return
    
    def __setattr__(self, k, v):
        if k in self.ATTRS:
            object.__setattr__(self, k, v)
        else:
            setattr(self.resolver, k, v)
        return

    def query(self, *args):
        if PYTHON_IS_311:
            return self.resolver.resolve(*args)
        else:
            return self.resolver.query(*args)

class TestRPZAccess(TestCase):
    """Response Policy Zone"""
    
    ASSOCIATOR_CACHE_SIZE = 20
    
    def setUp(self):
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop( self.event_loop )
        self.rpz = rpz.RPZ( self.event_loop, SERVER_ADDRESS, TEST_ZONE, None, RearView.DEFAULT_ADDRESS_RECORDS, None )
        self.remove = set()
        return
    
    def tearDown(self):
        # Build an update to delete all dangling records.
        update = Updater( TEST_ZONE )
        for oname in self.remove:
            update.delete(oname)
        # Notice we don't rely on the Connection object!
        sock = socket.create_connection( (SERVER_ADDRESS, 53) )
        req = update.to_wire()
        sock.send(len(req).to_bytes(2, **BIG_ENDIAN) + req)
        resp_length = sock.recv(2)
        wire_resp = sock.recv(int.from_bytes(resp_length, **BIG_ENDIAN))
        resp = dns.message.from_wire(wire_resp)
        sock.close()
        if resp.rcode(): raise ZoneCleanupFailure

        # The RPZ object has an outstanding periodic task which we must cancel.
        try:
            self.event_loop.run_until_complete(self.rpz.close())
        except CancelledError:
            pass
        
        return

    def add_test_records(self):
        update = Updater( self.rpz.rpz )
        for rec in TEST_RECORDS:
            update.add( rec[0], TTL, rdatatype.PTR, rec[1] )
            update.add( rec[0], TTL, rdatatype.TXT,
                    ','.join((
                        '{}={}'.format( *kv ) for kv in rec[2].items()
                    ))
            )
            self.remove.add( rec[0] )
        wire_response = self.event_loop.run_until_complete(
                            self.rpz.conn_.make_request( update.to_wire() )
                        )
        resp = dns.message.from_wire(wire_response)
        if resp.rcode(): raise ZoneUpdateFailure
        return

    def test_basic_request(self):
        """Tests basic ability to query the DNS server
        
        Verify basic connectivity to the DNS server and zone sanity.
        If this fails, reload the original test zone.
        """
        resolver = Resolver()
        resolver.nameservers = [ SERVER_ADDRESS ]
        resp = resolver.query( TEST_ZONE, 'NS' )
        self.assertEqual(resp.response.answer[0][0].to_text().lower(), 'ns.example.com.')
        return
    
    def test_connection_request(self):
        """Tests the Connection object"""
        wire_response = self.event_loop.run_until_complete(
                            self.rpz.conn_.make_request(
                                dns.message.make_query( TEST_ZONE, 'NS' ).to_wire()
                        )   )
        resp = dns.message.from_wire(wire_response)
        self.assertEqual(resp.answer[0][0].to_text().lower(), 'ns.example.com.')
        self.assertTrue(self.rpz.conn_.reader_ is None)
        self.assertTrue(self.rpz.conn_.writer_ is None)
        return
        
    def test_axfr(self):
        """Tests initial load via AXFR"""
        self.add_test_records()

        associator = Associator(self.ASSOCIATOR_CACHE_SIZE, Mock())
        self.event_loop.run_until_complete(
                self.rpz.load_axfr( associator, None )
            )

        self.assertEqual( len(self.rpz.contents), 2 )
        
        for rec in TEST_RECORDS:
            self.assertTrue( rec[3] in associator.addresses )

        address_rec = associator.addresses[ TEST_RECORDS[0][3] ]
        depth = TEST_RECORDS[0][2]['depth']
        resolution = address_rec.resolutions[
                        tuple( [None] * (depth - 1) + [ TEST_RECORDS[0][1] ] )
                     ]
        self.assertEqual( len(resolution.chain), depth )
        
        return
    
    def test_delete(self):
        """Tests deletion of an association"""
        self.add_test_records()
        
        associator = Associator(self.ASSOCIATOR_CACHE_SIZE, Mock())
        self.event_loop.run_until_complete(
                self.rpz.load_axfr( associator, None )
            )

        self.event_loop.run_until_complete(
                self.rpz.delete( TEST_RECORDS[1][3], None )
            )
        
        resolver = Resolver()
        resolver.nameservers = [ SERVER_ADDRESS ]

        self.assertTrue( TEST_RECORDS[0][0] in self.rpz.contents )
        self.assertEqual( resolver.query( TEST_RECORDS[0][0] + '.' + TEST_ZONE + '.', 'PTR' ).response.rcode(), rcode.NOERROR )

        self.assertFalse( TEST_RECORDS[1][0] in self.rpz.contents )
        self.assertRaises( dns.resolver.NXDOMAIN, 
                           resolver.query, TEST_RECORDS[1][0] + '.' + TEST_ZONE + '.', 'PTR'
                         )
        return
    
    def test_update(self):
        """Tests updating / adding of an association"""
        self.add_test_records()
        address = Address( TEST_RECORDS[0][3] )
        address.add_resolution( NEW_CHAIN )
        address.best_resolution = address.resolutions[ NEW_CHAIN ]
        
        associator = Associator(self.ASSOCIATOR_CACHE_SIZE, Mock())
        self.event_loop.run_until_complete(
                self.rpz.load_axfr( associator, None )
            )

        self.event_loop.run_until_complete(
            self.rpz.update( address, NEW_SCORE, None )
        )
        test_key = TEST_RECORDS[0][0]
        
        self.assertEqual( self.rpz.contents[test_key].ptr, NEW_CHAIN[-1] )

        resolver = Resolver()
        resolver.nameservers = [ SERVER_ADDRESS ]
        
        self.assertEqual( resolver.query( test_key + '.' + TEST_ZONE + '.', 'PTR' ).response.answer[0][0].to_text().lower(), NEW_CHAIN[-1] )
        params = dict(
            [   p.split('=')
                for p in resolver.query( test_key + '.' + TEST_ZONE + '.', 'TXT' ).response.answer[0][0].to_text().strip('"').split(',')
            ]
        )
        self.assertEqual( float(params['score']), NEW_SCORE )
        
        return
        
if __name__ == '__main__':
    unittest.main(verbosity=2)
