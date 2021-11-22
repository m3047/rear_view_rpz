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

![data flow diagram](https://github.com/m3047/rear_view_rpz/blob/main/install/cs-01.png)

#### Data flows

Please refer to the diagram above.

Starting with the (standard and rear view) clients, these issue queries to the chosen
_BIND_ (named) instance.

The rear view view, a named instance consults the Rear View RPZ for PTR record overrides.
In all other cases it forwards queries to the standard view.

The standard view consults the sitewide RPZs and consults the authoritative servers
on the internet as needed.

In the process of servicing requests, the standard view generates Dnstap telemetry which
is processed by the sputnik to synthesize PTR records. These are sent back to the standard
view, which uses them to update the RPZ. (The dashed line indicates that logically speaking
the sputnik updates the RPZ.)
