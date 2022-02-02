# Rear View RPZ

___status: good to go with no backlog items. I expect it to work if you satisfy the prerequisites. tested with python 3.6 & 3.8; dnspython 1.15 & 2.1; bind 9.12.3 & 9.16.23___

Turn your recursive DNS (BIND) server into a network investigation enabler with _DnsTap_ and _Response Policy Zones!_

## What are "DnsTap" and "Response Policy Zones"?

_DnsTap_ and _Response Policy Zones (RPZ)_ are features available with the [ISC BIND 9](https://www.isc.org/bind/) DNS server. _BIND_ is open source and is nearly ubiquitous in software distributions as either the "go to" or an optional recursive DNS service / server.

Unfortunately _DnsTap_ and _RPZ_ are generally considered to be optional features and so may not be available with the _BIND_ binary installed by your operating system, although _ISC's_ alternate packages are compiled with support. It's not hard to compile it from source, particularly on linux (or in a linux container).
These features are documented as part of the regular _BIND_ reference manual.

What's perhaps unusual about usage here is putting _DnsTap_ to work to update a zone served and utilized by the same DNS server as an _RPZ_ and utilizing that _RPZ_ not as a "ban hammer" but as a source of preferred information.

## How does this work?

___Rear View RPZ Agent___ runs as a service and interacts with the _BIND Server_ in two ways:

1. It listens for _DnsTap_ telemetry generated by the _BIND Server_, and uses that telemetry to derive "best guess" name-to-address mappings.
2. It uses dynamic DNS updates sent to the _BIND Server_ to maintain `PTR` entries in an _RPZ_ which targets the `in-addr.arpa.` namespace.

___BIND___ runs as a service answering user (and application) DNS requests. In the process it does two things:

1. Generates _DnsTap_ telemetry concerning the DNS request and response.
2. Consults any _Response Policy Zones_ for "overrides" or edits to be applied in place of what is provided by the global DNS database.

Put it together and you get **PTR responses enhanced with local knowledge**.

Run the policy incorporating this _RPZ_ as a view, possibly bound to a special address, and any client which wants "xray vision" for tools which support it just has to point their network configuration at the appropriate address for DNS services. (If you're running a service which needs the "ground truth" for DNS, have a different view on a different address for that.) In other words: you can do all the admin in _BIND_.

Here is a post with an example: https://lists.isc.org/pipermail/bind-users/2021-December/105450.html or see [Examples.txt](Examples.txt) in this directory.

## What are the prerequisites?

At the present time, you'll probably be frustrated unless you meet the following prerequisites.
If we get some more road dirt, maybe we can get some more playbooks: by all means submit a PR or
open an issue.

* You are familiar with running and configuring _BIND_
* You are familiar with:
  1. building from source...
     * satisfying prerequisites
     * `configure; make; make install...`
  1. ...or installing _BIND_ using _ISC's_ packages (https://www.isc.org/bind/)
* You can use `git clone`
* You are familiar with _Python_ syntax
* You can figure out a `systemd` service file


