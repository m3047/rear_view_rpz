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

import sys
import unittest
from unittest import TestCase
from unittest.mock import Mock, patch

import dns.message

if '..' not in sys.path:
    sys.path.insert(0,'..')

import rearview.db as db

TIME_NOW = 23456789.54321

class TestResolution(TestCase):
    """Tests db.Resolution."""
    
    CHAIN = ('foo.com', 'bar.com', 'www.bar.com')

    @patch('rearview.db.time', return_value=TIME_NOW)
    @patch('time.time', return_value=TIME_NOW)
    def test_seen(self, time_time, db_time):
        """Test that some math is being done right when seen() is called."""
        resolution = db.Resolution(self.CHAIN, TIME_NOW - 10, TIME_NOW - 1)
        
        self.assertEqual(resolution.last_seen, TIME_NOW - 1)
        
        resolution.seen()
        
        self.assertEqual(resolution.first_seen, TIME_NOW - 10)
        self.assertEqual(resolution.last_seen, TIME_NOW)
        self.assertEqual(resolution.query_count, 2)
        self.assertEqual(resolution.query_rate, 2 / 10)
        self.assertEqual(resolution.query_trend, 0.1)
        
        return

    def test_compare_good(self):
        """Basic comparison of resolutions."""
        resolution_1 = db.Resolution(self.CHAIN, TIME_NOW - 10, TIME_NOW - 1)
        resolution_2 = db.Resolution(('bizz.com', 'www.bar.com'), TIME_NOW - 10, TIME_NOW - 1)

        self.assertTrue( resolution_1 != resolution_2 )
        self.assertTrue( resolution_1 > resolution_2 )
        
        return
    
    def test_compare_with_none(self):
        """One of the resolutions contains none in the chain."""
        resolution_1 = db.Resolution(self.CHAIN, TIME_NOW - 10, TIME_NOW - 1)
        resolution_2 = db.Resolution((None, None, 'www.bar.com'), TIME_NOW - 10, TIME_NOW - 1)
        
        self.assertTrue( resolution_1 != resolution_2 )
        self.assertTrue( resolution_1 > resolution_2 )
        
        return
    
class TestAssociatorUpdate(TestCase):
    """db.Associator.update_resolution()"""
    
    CACHE_SIZE = 20
    
    SIMPLE_UPDATE_ARGS = ( '10.0.0.1', ('foo.example.com', 'www.example.com') )
    SECOND_RESOLUTION = ( '10.0.0.1', ('foo.example.com', 'cdn.example.com', 'images.example.com') )
    DIFFERENT_ADDRESS = ( '10.0.0.2', ('foo.example.com', 'www.example.com') )
    
    def basic_associator(self):
        mock_cache_eviction = Mock()
        return ( mock_cache_eviction, db.Associator(self.CACHE_SIZE, mock_cache_eviction) )
    
    def test_update_new_address(self):
        """Update with an address which hasn't been seen before."""
        mock_cache_eviction, associator = self.basic_associator()
        added = associator.update_resolution( *self.SIMPLE_UPDATE_ARGS )

        self.assertTrue(added)
        self.assertEqual(associator.n_resolutions, 1)
        self.assertTrue(self.SIMPLE_UPDATE_ARGS[0] in associator.addresses)
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 1)
        self.assertTrue(self.SIMPLE_UPDATE_ARGS[1] in associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions)
        mock_cache_eviction.assert_not_called()

        return
    
    def test_update_same_resolution(self):
        """Same resolution is seen again."""
        mock_cache_eviction, associator = self.basic_associator()
        added = associator.update_resolution( *self.SIMPLE_UPDATE_ARGS )
    
        added = associator.update_resolution( *self.SIMPLE_UPDATE_ARGS )

        self.assertFalse(added)
        self.assertEqual(associator.n_resolutions, 1)
        self.assertEqual(len(associator.addresses), 1)
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 1)        
        self.assertEqual(associator.addresses[
                                self.SIMPLE_UPDATE_ARGS[0]
                            ].resolutions[self.SIMPLE_UPDATE_ARGS[1]
                                ].query_count,
                         2, 'should have been seen twice'
                    )
        mock_cache_eviction.assert_not_called()

        return
    
    def test_update_different_resolution(self):
        """A different resolution is seen."""
        mock_cache_eviction, associator = self.basic_associator()
        added = associator.update_resolution( *self.SIMPLE_UPDATE_ARGS )
    
        added = associator.update_resolution( *self.SECOND_RESOLUTION )

        self.assertTrue(added)
        self.assertEqual(associator.n_resolutions, 2)
        self.assertEqual(len(associator.addresses), 1)
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 2)
        self.assertEqual(associator.addresses[
                                self.SIMPLE_UPDATE_ARGS[0]
                            ].resolutions[self.SIMPLE_UPDATE_ARGS[1]
                                ].query_count,
                         1, 'should have been seen once'
                    )
        mock_cache_eviction.assert_not_called()

        return
    
    def test_update_different_address(self):
        """A different address is seen."""
        mock_cache_eviction, associator = self.basic_associator()
        added = associator.update_resolution( *self.SIMPLE_UPDATE_ARGS )
    
        added = associator.update_resolution( *self.DIFFERENT_ADDRESS )

        self.assertTrue(added)
        self.assertEqual(associator.n_resolutions, 2)
        self.assertEqual(len(associator.addresses), 2)
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 1)
        self.assertEqual(len(associator.addresses[self.DIFFERENT_ADDRESS[0]].resolutions), 1)
        mock_cache_eviction.assert_not_called()

        return
    
    def test_trigger_eviction(self):
        """Test triggering eviction during a normal update."""
        mock_cache_eviction, associator = self.basic_associator()
        associator.n_resolutions = self.CACHE_SIZE - 1
        
        added = associator.update_resolution( *self.SIMPLE_UPDATE_ARGS )
        mock_cache_eviction.assert_not_called()
    
        added = associator.update_resolution( *self.DIFFERENT_ADDRESS )
        mock_cache_eviction.assert_called()
        
        return
        
class TestAssociatorUpdateRPZ(TestCase):
    """Tests db.Associator.update_resolution_from_rpz()"""
    
    CACHE_SIZE = 20
    
    SIMPLE_UPDATE_ARGS = ( '10.0.0.1',
                           { 'ptr':         'www.example.com',
                             'depth':       2,
                             'first':       TIME_NOW - 10,
                             'last':        TIME_NOW - 1,
                             'count':       3,
                             'trend':       1.0,
                             'score':       2.5
                           }
                         )
    EXISTING_RESOLUTION = ( '10.0.0.1', ('foo.example.com', 'www.example.com') )
    SECOND_RESOLUTION = ( '10.0.0.1', 
                           { 'ptr':         'images.example.com',
                             'depth':       3,
                             'first':       TIME_NOW - 10,
                             'last':        TIME_NOW - 1,
                             'count':       3,
                             'trend':       1.0,
                             'score':       2.5
                           }
                         )
    
    def basic_associator(self):
        mock_cache_eviction = Mock()
        return ( mock_cache_eviction, db.Associator(self.CACHE_SIZE, mock_cache_eviction) )

    def test_update_from_rpz_new_address(self):
        """RPZ has an address which we haven't seen."""
        mock_cache_eviction, associator = self.basic_associator()
        associator.update_resolution_from_rpz( *self.SIMPLE_UPDATE_ARGS )

        self.assertEqual(associator.n_resolutions, 1)
        self.assertTrue(self.SIMPLE_UPDATE_ARGS[0] in associator.addresses)
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 1)
        self.assertTrue( (None, self.SIMPLE_UPDATE_ARGS[1]['ptr'])
                     in  associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions
        )
        
        resolution = associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions[(None, self.SIMPLE_UPDATE_ARGS[1]['ptr'])]

        self.assertEqual( resolution.chain, (None, self.SIMPLE_UPDATE_ARGS[1]['ptr']) )
        self.assertEqual( resolution.first_seen, self.SIMPLE_UPDATE_ARGS[1]['first'])
        self.assertEqual( resolution.last_seen, self.SIMPLE_UPDATE_ARGS[1]['last'])
        self.assertEqual( resolution.query_count, self.SIMPLE_UPDATE_ARGS[1]['count'])
        self.assertEqual( resolution.query_trend, self.SIMPLE_UPDATE_ARGS[1]['trend'])
        self.assertEqual( resolution.reload_score, self.SIMPLE_UPDATE_ARGS[1]['score'])

        mock_cache_eviction.assert_not_called()

        return
        

    @patch('rearview.db.time', return_value=TIME_NOW)
    @patch('time.time', return_value=TIME_NOW)    
    def test_update_from_rpz_existing_address(self, time_time, db_time):
        """RPZ attempts to update an existing address and resolution."""
        mock_cache_eviction, associator = self.basic_associator()
        added = associator.update_resolution( *self.EXISTING_RESOLUTION )
        
        self.assertEqual(associator.addresses[
                            self.EXISTING_RESOLUTION[0]
                                ].resolutions[
                                    self.EXISTING_RESOLUTION[1]].first_seen,
                         TIME_NOW
                        )

        associator.update_resolution_from_rpz( *self.SIMPLE_UPDATE_ARGS )

        self.assertEqual(associator.addresses[
                            self.EXISTING_RESOLUTION[0]
                                ].resolutions[
                                    self.EXISTING_RESOLUTION[1]].first_seen,
                         TIME_NOW
                        )
        self.assertEqual(len(associator.addresses), 1)                                
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 1)

        mock_cache_eviction.assert_not_called()

        return

    
    def test_update_from_rpz_new_resolution(self):
        """RPZ attempts to update an existing address but different resolution."""
        mock_cache_eviction, associator = self.basic_associator()
        added = associator.update_resolution( *self.EXISTING_RESOLUTION )

        associator.update_resolution_from_rpz( *self.SECOND_RESOLUTION )

        self.assertEqual(len(associator.addresses), 1)                                
        self.assertEqual(len(associator.addresses[self.SIMPLE_UPDATE_ARGS[0]].resolutions), 2)

        mock_cache_eviction.assert_not_called()

        return

    def test_trigger_eviction(self):
        """Test triggering eviction during an RPZ update."""
        mock_cache_eviction, associator = self.basic_associator()
        associator.n_resolutions = self.CACHE_SIZE - 1
        
        added = associator.update_resolution( *self.EXISTING_RESOLUTION )
        mock_cache_eviction.assert_not_called()
    
        added = associator.update_resolution_from_rpz( *self.SECOND_RESOLUTION )
        mock_cache_eviction.assert_called()
        
        return
        
class TestAssociatorEviction(TestCase):
    """Tests db.Associator.do_cache_eviction()"""

    CACHE_SIZE = 20
    
    BASE_ADDRESS = '10.0.0.1'
    BASE_RESOLUTION = ['foo.example.com', '{}.example.com']
    
    DIFF_ADDRESS = '10.0.1.{}'
    DIFF_RESOLUTION = ('foo.example.com', 'www.example.com')
    
    def different_resolutions(self, n):
        """Yield different resolutions for the same address."""
        for i in range(n):
            resolution = self.BASE_RESOLUTION.copy()
            resolution[-1] = resolution[-1].format(i)
            yield ( self.BASE_ADDRESS, tuple(resolution) )
        return
    
    def different_addresses(self, n, base=0):
        """Yield resolutions for different addresses."""
        for i in range(n):
            yield ( self.DIFF_ADDRESS.format(i+base), self.DIFF_RESOLUTION )
        return
    
    def basic_associator(self):
        mock_cache_eviction = Mock()
        return ( mock_cache_eviction, db.Associator(self.CACHE_SIZE, mock_cache_eviction) )

    def test_many_addresses(self):
        """Many addresses with a small number of resolutions."""
        mock_cache_eviction, associator = self.basic_associator()

        for resolution in self.different_addresses(self.CACHE_SIZE + 10):
            added = associator.update_resolution( *resolution )
            self.assertTrue(added)

        mock_cache_eviction.assert_called()
        self.assertEqual(len(associator.cache), self.CACHE_SIZE + 10)

        addresses = associator.do_cache_eviction()
        self.assertEqual(len(associator.cache), self.CACHE_SIZE)
        self.assertEqual(len(addresses), 10)
        self.assertEqual(associator.n_resolutions, self.CACHE_SIZE)
        
        return
    
    def test_many_resolutions(self):
        """An address with many resolutions."""        
        mock_cache_eviction, associator = self.basic_associator()
        
        for resolution in self.different_addresses(5):
            added = associator.update_resolution( *resolution )
        
        for resolution in self.different_resolutions(self.CACHE_SIZE):
            added = associator.update_resolution( *resolution )
        
        for resolution in self.different_addresses(5, 5):
            added = associator.update_resolution( *resolution )

        self.assertEqual(len(associator.addresses[self.BASE_ADDRESS].resolutions), self.CACHE_SIZE)
        self.assertEqual(len(associator.cache), 11)

        addresses = associator.do_cache_eviction()

        self.assertEqual(len(addresses), 6)
        self.assertEqual(len(associator.cache), 6)
        self.assertEqual(associator.n_resolutions, self.CACHE_SIZE)
        self.assertEqual(len(associator.addresses[self.BASE_ADDRESS].resolutions), self.CACHE_SIZE - 5)
        
        return
    
    def test_single_address(self):
        """When a single address can shed enough resolutions the cache shouldn't rotate."""
        mock_cache_eviction, associator = self.basic_associator()
        
        for resolution in self.different_resolutions(self.CACHE_SIZE):
            added = associator.update_resolution( *resolution )
        
        for resolution in self.different_addresses(2):
            added = associator.update_resolution( *resolution )
        
        self.assertEqual(len(associator.addresses[self.BASE_ADDRESS].resolutions), self.CACHE_SIZE)
        self.assertEqual(len(associator.cache), 3)

        addresses = associator.do_cache_eviction()

        self.assertEqual(len(addresses), 1)
        self.assertEqual(len(associator.cache), 3)
        self.assertEqual(associator.n_resolutions, self.CACHE_SIZE)
        self.assertEqual(len(associator.addresses[self.BASE_ADDRESS].resolutions), self.CACHE_SIZE - 2)
        self.assertEqual(associator.cache[-1].address, self.BASE_ADDRESS)
        
        return

def reconstitute(message_text):
    """Used to reconstitute a dns.message.Message in text format."""
    return dns.message.from_text(
            '\n'.join((
                line for line in [ l.strip() for l in message_text.split('\n') ]
                if line
            ))
        )

class TestRearView(TestCase):
    """db.RearView."""
    
    CACHE_SIZE = 20
    RESOLUTIONS = (
        ('this.wont.get.chosen.example.com',),
        ('foo.example.com', 'www.example.com')
    )
    
    MESSAGE = """
        id 4100
        opcode QUERY
        rcode NOERROR
        flags QR AA RD RA
        ;QUESTION
        docs.m3047. IN A
        ;ANSWER
        DOCS.m3047. 600 IN CNAME SOPHIA.M3047.
        SOPHIA.m3047. 600 IN A 10.0.0.224
        ;AUTHORITY
        m3047. 600 IN NS ATHENA.m3047.
        ;ADDITIONAL
        ATHENA.m3047. 600 IN A 10.0.0.220
    """
    
    def basic_rear_view(self):
        associations = db.Associator(self.CACHE_SIZE, Mock())
        return Mock(associations=associations, address_record_types=db.RearView.DEFAULT_ADDRESS_RECORDS), associations
    
    def test_solve_deleted(self):
        """An address which is missing from the telemetry view."""
        mock_RV, associator = self.basic_rear_view()
        need_update = db.RearView.solve_(mock_RV, '1.2.3.4')
        self.assertFalse(need_update)
        mock_RV.rpz.create_task.assert_called()
        return
    
    def test_solve_no_best(self):
        """No best resolution is calculated."""
        mock_RV, associator = self.basic_rear_view()
        for resolution in self.RESOLUTIONS:
            self.assertTrue(associator.update_resolution( '1.2.3.4', resolution))
        address = associator.addresses['1.2.3.4']

        self.assertTrue(address.best_resolution is None)

        need_update = db.RearView.solve_(mock_RV, '1.2.3.4')
        self.assertTrue(need_update)
        
        self.assertEqual(address.best_resolution.chain, self.RESOLUTIONS[1])
        
        return
    
    def test_solve_score(self):
        """This resolution has a better score."""
        mock_RV, associator = self.basic_rear_view()
        for resolution in self.RESOLUTIONS:
            self.assertTrue(associator.update_resolution( '1.2.3.4', resolution))
        address = associator.addresses['1.2.3.4']
        poor_resolution = address.resolutions[self.RESOLUTIONS[0]]

        poor_resolution.reload_score = 0.1
        address.best_resolution = poor_resolution

        need_update = db.RearView.solve_(mock_RV, '1.2.3.4')
        self.assertTrue(need_update)
        
        self.assertEqual(address.best_resolution.chain, self.RESOLUTIONS[1])
        
        return
    
    def test_process_answer(self):
        """DNS response to telemetry view processing."""
        mock_RV, associator = self.basic_rear_view()
        msg = reconstitute(self.MESSAGE)

        added = db.RearView.process_answer_(mock_RV, msg)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0], '10.0.0.224')
        self.assertTrue(('sophia.m3047.', 'docs.m3047.') in associator.addresses['10.0.0.224'].resolutions)
        
        return
    
if __name__ == '__main__':
    unittest.main(verbosity=2)
    
