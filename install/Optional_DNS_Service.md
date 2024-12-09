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

## Configuration items

### named (BIND)

The _BIND_ DNS server (typically) runs as a process / program named `named`.

#### Separate directories

Although it would be possible to run both copies of _BIND_ in the same directory, for clarity and
simplicity a separate directory is utilized for each.

For historical reasons (and partly because I compile _BIND_ myself) I use `/etc/namedb/` as _BIND's_
working directory and I keep the logs and zonefiles in there. So, I created a `/etc/namedb-rv/` for
the second copy of _BIND_.

The "standard" resolver running in `/etc/namedb/` has the usual set of artifacts. The resolver
running the _Rear View_ RPZ contains the following in `/etc/namedb-rv/`:

* Logs
* The RPZ zone file

and that's it!

The working directory is specified in the config file.

#### Configuration files

The standard configuration is in `/etc/named.conf` and the RPZ view is in `/etc/named-rv.conf`.

A comparison of pertinent details is provided in the following table. Code fragments follow.

| item | `named.conf` | `named-rv.conf` |
| ---- | ------------ | --------------- |
| `options:listen-on` | All of the interface addresses (including `localhost`) except for the one which the RPZ instance will listen on. | The address for the special service. |
| `options:directory` | `/etc/namedb` | `/etc/namedb-rv` |
| `options:query-source` | The external (internet facing) interface. | The special service address. |
| `options:max-cache-size` | `20%` | `20m` |
| `options:response-policy` zones | The standard best practice configuration (several RPZs), excluding _Rear View_. | Just the _Rear View_ RPZ. |
| `options:response-policy` zone `min-interval` | n/a | `zone "name" min-interval 10;` |
| `options:dnstap` and `options:dnstap-output` | configured | not configured |
| (RNDC) `controls` | RNDC listens on `localhost:953` | RNDC listens on `localhost:9053` |
| _Rear View_ `zone` | `master; check-names ignore;` | `slave; check-names ignore; masters { <the standard view>; };` |

**standard view**

```
options {
    listen-on { 127.0.0.1; ... };
    query-source address <external interface> port *;
    max-cache-size 20%;
    allow-update { ... };
    allow-transfer { ... };
    provide-ixfr yes;
    request-ixfr yes;
    response-policy {
        zone "allow-list.example.net";
        zone "deny-list.example.net";
    };
     dnstap { client response; };
     dnstap-output unix "/var/run/named/dns_agent-dnstap.socket";
};
controls {
      inet 127.0.0.1 port 953
              allow { 127.0.0.1; } keys { "rndc-key"; };
};

zone "..." {
};

zone "rearview.example.net" {
     type master;
     check-names ignore;
     file "rearview.example.net";
};
```

**rearview view**

```
options {
    listen-on { <special interface address>; };
    query-source address <special interface address> port *;
    max-cache-size 20m;
    forward only;
    forwarders { <standard interface address; };
    min-refresh-time 15;
    response-policy {
        zone "rearview.example.net" min-update-interval 10;
    }
};
controls {
      inet 127.0.0.1 port 9053
              allow { 127.0.0.1; } keys { "rndc-key"; };
};

zone "..." {
};

zone "rearview.example.net" {
     type slave;
     check-names ignore;
     file "rearview.example.net";
     masters { <standard interface address; };
};
```

Note that there's no compelling reason to have separate `rndc-keys` since access is restricted to `localhost`.

#### RNDC config files

There are separate RNDC config files, `/etc/rndc.conf` and `/etc/rndc-rv.conf` respectively. The only difference
is the `port` which is specified (`953` vs `9053`).

#### systemd service files

An [example](https://github.com/m3047/rear_view_rpz/blob/main/install/rearview-rpz.service) is provided for the RPZ
service. The only difference is that the respective config files have been specified (to both `named` and `rndc`)
using `-c`.
