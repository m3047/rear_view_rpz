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

"""This is the standard heuristic function.

It should be symlinked to heuristic.py.
"""

from math import log

def heuristic_func(resolution):
    """This is the heuristic function.

    It can access some built-in properties to get information about the
    Resolution object. See rearview.Heuristics as well as db.Resolution.

    It returns a positive number, where a larger number is "better".

    The goals of this heuristic are:
    
    * prioritize deeper chains
    * terminating in shorter FQDNS
    * all other things being roughly equal choose the one with a larger query count
    
    The formula is:
    
        <depth of chain> / <number of labels> + log(<query count>)
    """
    n_labels = resolution.number_of_labels
    if not n_labels:
        return 0.0
    return resolution.depth_of_chain / n_labels + log(resolution.query_count)
