## Synthesized vs Actual PTR records Provide Very Different Views

TLDR: The big players don't make PTR records to make life easy for you, and they're only getting bigger.

I've been running _Rear View RPZ_ for a while now and have had a decent chance to look at
and play with the data. Consolidation has only grown more apparent while I wasn't paying attention!
If you have any interest in what domains are being communicated with by your networks and devices, it
behooves you to provision that resource, today. I recommend something which is ingesting data which
is as local as possible, whether you do that with something like _Zeek_ or telemetry from local caching
resolvers is up to you. Yes sure there are commercial reverse DNS offerings, but ___all politics is local___
    
So do you want your politics, or the politics of for example _Amazon_ or _Cloudflare_? What you've got,
what sets you apart, is the traffic on your own network.

### My observation network

* Primarily a SOHO "user" network.
* Not many external clients.
* Using a `CACHE_LIMIT` of 3000 resolutions seems to be adequate (resulting in approximately 2500 addresses).

_Synthetic_ refers to `PTR` records generated from DNS resolution telemetry data, whereas _actual_ refers
to what is returned by an actual reverse DNS lookup.

Canonical domains were extracted from both and utilized for the comparisons which follow.

### Main observations

#### Actual and synthetic distributions are very different

Not only are the **domains** different, the **distribution** is different.

![pie chart comparison](utilities/synthesized-vs-actual-ptr.svg)

