**NOTE**: `shodohflo` is a symlink to https://github.com/m3047/shodohflo/tree/master/shodohflo which you should also download.

See the [`/install`](/install) directory for installation instructions.

### `configuration.py`

Hopefully the comments will get you where you need to go, but here are my "hot takes".

##### cache size
You might start with a smaller cache size (maybe 1000) and see where that gets you. You can bump it at any time.
However my cache management is not perfect at the moment and you may see odd things if you reduce the size
(although restarting it several times seems to more or less bludgeon it into compliance).

##### logging level
I recommend setting this to something!

##### statistics
This reports on throughput and backpressure. The statistics are calculated for the last 60 seconds.
That doesn't mean that you have to report on it that often, I find every 10 minutes is plenty.

There are various statistics collections, you'll just have to look through the code. The statistics
reported from collections include counts, number of outstanding counters (depth), and elapsed time.
See `pydoc3 shodohflo.statistics`. Statistics are logged at level `INFO` (see `STATISTICS_PRINTER`
in `agent.py`).

##### coroutine tracing
Setting `PRINT_COROUTINE_ENTRY_EXIT` will log coroutine entry/exits. If you're trying to understand the
code turning this on will help. It's very verbose though, and it will negatively impact performance.

### The Console
You can enable a console, which will listen on the unencrypted TCP port of your choosing. I won't waste
your time with a _mea culpa_ about how dangerous this is! It only provides readonly access but it could
impact performance if abused.

This is my tool for understanding what's happening "under the hood", the exact specifications and
behavior are subject to change at any time. A lot of the behavior is implementation specific and if I
change underlying architecture it may not make sense anymore or do remotely the same thing.

`pydoc3 rearview.console` is the authoritative documentation.

Briefly, there are three views of the data in the current implementation:

1) The telemetry view, based on what's coming from _Dnstap_.
2) The zone view, which is in memory and is supposed to mirror what's in the actual zone.
3) The actual zone.

This tool can show if there are discrepancies between the two in-memory views, detailed info for
an address in all of the views, depths of processing queues (not the same as statistics), and information
about the cache eviction queue.

### Ingesting Telemetry
Defining `UDP_LISTENER` in the configuration file enables a UDP listener which expects telemetry in
JSON format. This can be used in lieu of or in addition to receipt of _Dnstap_ telemetry.

For simple, standalone use _Dnstap_ is straightforward. If you have telemetry from multiple caching
nameservers (or from some other source entirely) then this may be a useful option.

At the moment work is ongoing in [ShoDoHFlo](https://github.com/m3047/shodohflo) to split the existing
_DNS Agent_ which reads _Dnstap_ telemetry into separate _Dnstap_ and _DNS_ parts.

The fields which _Rearview_ expects to see are `address` and `chain` as documented in m3047/shodohflo#11:

```
{"address":"10.2.66.5","chain":["server.example.com.","www.example.com."]}
```

Note that the chain is ***reversed*** from normal understanding. The semantics above should be understood as

    www.example.com -> server.example.com -> 10.2.66.5

Define `UDP_LISTENER` as a dictionary with the following keys:

* `recipient` The address to listen on (implicitly defining an interface).
* `port` The port to listen on.

##### multicast

NO FREE SUPPORT IS PROVIDED FOR MULTICAST ISSUES AND AT THE PRESENT TIME IT ONLY WORKS WITH IPv4

However, multicast is supported. If you have multiple consumers of _Dnstap_ telemetry, this is how you do it.

Define `UDP_LISTENER` as a dictionary with the following keys:

* `recipient` The multicast group to listen on.
* `port` The port to listen on.
* `interface` The interface to listen for group traffic on. Specify the address which is bound to the interface at the system level.

### Messages

##### unexpected qname {} in zonefile on load

During zone load when the agent is initializing, `TXT` and `PTR` records with qnames like `4.3.2.1.in-addr.arpa` are loaded
and other records are rejected.

What you should do about this message depends on what you're doing with the zone. If you're not doing anything with
the zone yourself, you should manually remove the entries from the zone file:

1. `rndc freeze`
2. Remove the offending records from the zone file and **increment the serial number**.
3. `rndc thaw`

On the other hand if you're putting your own `PTR` or `TXT` records in the zone, you may want to simply
make the agent shut up. You can do this by setting `GARBAGE_LOGGER = None` in your configuration.

History: At one time there was a bug where IPv6 records were loaded incorrectly.
