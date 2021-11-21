# Things in this directory

#### `systemd` service files

* `rearview-rpz.service` Runs a second copy of _BIND_. See the [Optional DNS Service Case Study](https://github.com/m3047/rear_view_rpz/blob/main/Optional_DNS_Service.md).
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
                                600        ; refresh (10 minutes)
                                60         ; retry (1 minute)
                                86400      ; expire (1 day)
                                600        ; minimum (10 minutes)
                                )
                        NS      LOCALHOST.
```

## How do I compile _BIND_?

Look at [this Dockerfile](https://github.com/m3047/shodohflo/blob/master/examples/docker/Dockerfile) for inspiration. You will need to install the _Framestream_ and _Protobuf_ developer libraries / packages. You can download the source [here](https://www.isc.org/bind/).
