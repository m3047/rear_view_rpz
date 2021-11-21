# Case Study: An Optional DNS Service offering _Rear View_ PTR records

## Use case

A workgroup is provided with DNS caching resolver services. We want to use all of the
workgroup's DNS traffic to inform _Rear View_, but we want utilization of _Rear View_ to
be optional, tied to network configuration of the laptop / VM.

These services incorporate (other) _Response Policy Zone_ (RPZ) services, which complicates
the utilization of _Views_ considerably. Two copies of _BIND_ are run, each listening on different
addresses. The choice of service to utilize is determined by the DNS server address(es)
specified as part of the network configuration.

#### The standard DNS service view

* Consults authoritative DNS sources.
* Has a large cache.
* Consults locally maintained allow / deny RPZs (RPZ best practice).
* Generates _Dnstap_ telemetry.
* Masters the _Rear View_ RPZ (but does not consult it), updating it from _Dnstap_ telemetry.

#### The Rear View service view

* Forwards to the standard service view.
* Has a small cache.
* Mirrors the _Rear View_ RPZ and uses it as a _Response Policy Zone_.

