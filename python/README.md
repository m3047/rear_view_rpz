**NOTE**: `shodohflo` is a symlink to https://github.com/m3047/shodohflo/tree/master/shodohflo which you should also download.

See the `/installation` directory for installation instructions.

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

### the console
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
