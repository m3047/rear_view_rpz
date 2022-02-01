Help on module rearview.console in rearview:

NAME
    rearview.console - An interactive console.

DESCRIPTION
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
    whether this is reflected in the zone construct.
    
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

CLASSES
    builtins.object
        Context
        Request
    
    class Context(builtins.object)
     |  Context for the console.
     |  
     |  Methods defined here:
     |  
     |  __init__(self, dnstap=None)
     |      Create a context object.
     |      
     |      dnstap is normally set in code, but we pass it in with a default of
     |      None to make its presence known.
     |  
     |  handle_requests(self, reader, writer)
     |  
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |  
     |  __dict__
     |      dictionary for instance variables (if defined)
     |  
     |  __weakref__
     |      list of weak references to the object (if defined)
    
    class Request(builtins.object)
     |  Everything to do with processing a request.
     |  
     |  The idiom is generally Request(message).response and then do whatever is sensible
     |  with response. Response can be nothing, in which case there is nothing further
     |  to do.
     |  
     |  Methods defined here:
     |  
     |  __init__(self, message, dnstap)
     |      Initialize self.  See help(type(self)) for accurate signature.
     |  
     |  a2z(self, request)
     |      a2z
     |  
     |  address(self, request)
     |      addr{ess} <some-address>
     |      
     |      Kind of a hot mess, but here's what's going on:
     |      
     |      * If there's no best resolution it could be that's because it was loaded
     |        from the actual zone file, which we can tell if it has a depth > 1 and
     |        the first entry is None.
     |        
     |      * Other things.
     |  
     |  bad_request(self, reason)
     |      A bad/unrecognized request.
     |  
     |  cache(self, request)
     |      cache [<|>] <number>
     |  
     |  dispatch_request(self, request)
     |      Called by __init__() to dispatch the request.
     |  
     |  entry(self, request)
     |      entry <some-address>
     |  
     |  evictions(self, request)
     |      evictions <number>
     |  
     |  qd(self, request)
     |      qd
     |  
     |  quit(self, request)
     |      quit
     |  
     |  refresh(self, request)
     |      refresh <number>
     |  
     |  validate_request(self, request)
     |  
     |  ----------------------------------------------------------------------
     |  Data descriptors defined here:
     |  
     |  __dict__
     |      dictionary for instance variables (if defined)
     |  
     |  __weakref__
     |      list of weak references to the object (if defined)
     |  
     |  ----------------------------------------------------------------------
     |  Data and other attributes defined here:
     |  
     |  ABBREVIATED = {'address', 'cache', 'entry', 'evictions', 'refresh'}
     |  
     |  COMMANDS = {'a2z': 1, 'address': 2, 'cache': 3, 'entry': 2, 'evictions...

FILE
    /home/m3047/GitHub/rear_view_rpz/python/rearview/console.py


