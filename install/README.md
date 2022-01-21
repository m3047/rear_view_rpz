# Things in this directory

#### `systemd` service files

* `rearview-rpz.service` Runs a second copy of _BIND_. See the [Optional DNS Service Case Study](https://github.com/m3047/rear_view_rpz/blob/main/install/Optional_DNS_Service.md).
* `rearview-agent.service` Runs `agent.py`.

# Really simple install instructions

***what could go wrong?***

1. Clone this repo.
1. Clone https://github.com/m3047/shodohflo in the same directory.
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

     dnstap { client response; };
     dnstap-output unix "/tmp/dnstap";
```

###### Is Dnstap working?

The simplest way that I know of to tell is to run `../../shodohflo/examples/dnstap2json.py` and it should spew (abbreviated)
output to the console:

```
# ../../shodohflo/examples/dnstap2json.py /tmp/dnstap
INFO:root:dnstap2json starting. Socket: /tmp/dnstap  Destination: STDOUT
INFO:root:Accepting: protobuf:dnstap.Dnstap
{"client": "10.0.0.224", "qtype": "AAAA", "status": "NOERROR", "chain": [["infoblox.com."], ["2620:12a:8001::3", "2620:12a:8000::3"]]}
{"client": "10.0.0.224", "qtype": "A", "status": "NOERROR", "chain": [["www.worldtimeserver.com."], ["54.39.158.232"]]}
{"client": "10.0.0.118", "qtype": "A", "status": "NOERROR", "chain": [["pool.ntp.org."], ["64.142.54.12", "208.67.72.50", "45.15.168.98", "137.190.2.4"]]}
```

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

Look at [this Dockerfile](https://github.com/m3047/shodohflo/blob/master/examples/docker/Dockerfile) for inspiration. You will need to install the _Framestream_ and _Protobuf_ developer libraries / packages. You can download the source [here](https://www.isc.org/bind/).
