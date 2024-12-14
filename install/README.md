# Things in this directory

#### `systemd` service files

* `rearview-rpz.service` Runs a second copy of _BIND_. See the [Optional DNS Service Case Study](https://github.com/m3047/rear_view_rpz/blob/main/install/Optional_DNS_Service.md).
* `rearview-agent.service` Runs `agent.py`.

# Really simple install instructions

***what could go wrong?***

1. Clone https://github.com/m3047/shodohflo and set up `agents/dnstap_agent.py` (to create a source of data).
1. Clone this repo.
1. Copy `configuration-sample.py` to `configuration.py` and make any desired edits.
1. Create the RPZ in your _BIND_ configuration (`named.conf`)
1. As `root`: `cd python; ./agent.py`

## Creating an RPZ

_Response Policy Zones_ are documented in the _BIND Administrators' Reference Manual_. Quick instructions
for this use case only, are as follows. You need to put the following elements into `named.conf`.

#### Access Control List

Define an access control list.

```
acl rpz_update {
    localhost;
};
```

#### Response Policy and Dnstap Socket

In the `options` section add the following, changing the name of the zone as appropriate:

```
     response-policy {
         zone "rearview.example.com";
     };
```

**NOTE**: You will (also) add `dnstap` and `dnstap-output` stanzas when setting up the _ShoDoHFlo_ `dnstap_agent`.

###### Is Dnstap working?

You can use _netcat_ (`nc`) to monitor unicast datagrams (`nc -luk ...`) or my [multicast tool](https://athena.m3047.net/pub/python/multicast/) `receiver.py` to monitor multicast datagrams output by `dnstap_agent.py`:

```
# ./receiver.py 224.4.102.250:1959 10.0.0.220
('10.0.0.220', 52920): {"chain": ["ntp1.glb.nist.gov.", "time.nist.gov."], "client": "10.0.0.118", "qtype": "A", "status": "NOERROR", "id": 239137, "address": "132.163.97.6"}
('10.0.0.220', 52920): {"chain": ["austin.logs.roku.com."], "client": "10.0.1.213", "qtype": "A", "status": "NOERROR", "id": 239138, "address": "35.212.73.121"}
('10.0.0.220', 52920): {"chain": ["austin.logs.roku.com."], "client": "10.0.1.213", "qtype": "A", "status": "NOERROR", "id": 239139, "address": "35.212.66.177"}
('10.0.0.220', 52920): {"chain": ["austin.logs.roku.com."], "client": "10.0.1.213", "qtype": "A", "status": "NOERROR", "id": 239140, "address": "35.212.119.44"}
('10.0.0.220', 52920): {"chain": ["austin.logs.roku.com."], "client": "10.0.1.213", "qtype": "A", "status": "NOERROR", "id": 239141, "address": "35.212.38.156"}
```

Similarly you can use `nc -u...` or `sender.py` to set arbitrary packets to the _Rearview agent_ for testing. (Left as an exercise for the reader.)

###### Dnstap is technically optional

Since the _Rearview agent_ ingests telemetry in JSON format via a UDP socket, if you have some other source for that telemetry
then technically you don't need to set up _BIND_ and `dnstap_agent.py` to generate it.

#### Zone Declaration

Add the following zone declaration, changing the name of the zone as appropriate:

```
zone "rearview.example.com" {
     type master;
     check-names ignore;
     file "rearview.example.com";
     masterfile-format text;

     allow-update { rpz_update; };
     allow-transfer { rpz_update; };
};
```

## The Zone File

You can use this to initialize the zone file:

```
$ORIGIN .
$TTL 600        ; 10 minutes
REARVIEW.EXAMPLE.COM IN SOA  DEV.NULL. DNS.EXAMPLE.COM. (
                                1          ; serial
                                30         ; refresh
                                15         ; retry
                                86400      ; expire (1 day)
                                600        ; minimum (10 minutes)
                                )
                        NS      LOCALHOST.
```

## How do I compile _BIND_?

First off, ***do you need to compile BIND?*** The [ISC BIND 9 Packages](https://www.isc.org/bind/) (from ISC, not your
OS vendor) are compiled with Dnstap support already.

Look at [this Dockerfile](https://github.com/m3047/shodohflo/blob/master/examples/docker/Dockerfile) for inspiration. You will need to install the _Framestream_ and _Protobuf_ developer libraries / packages. You can download the source [here](https://www.isc.org/bind/).
