### `Rear_View-knime-workspace.tgz`

This is a [KNIME](https://knime.com/) workspace for analyzing the data in the RPZ.

Unpack it in your `knime_workspace` directory to create a `Rear_View` workflow. Follow the
directions to set the zone name and DNS server address.

Aside from standard modules, the following are required:
* `pandas` a _KNIME_ requirement
* `dnspython` used for "speaking DNS"

### Field Notes on working with Meta Data

The `TXT` records written to the zone have metadata associated with the best resolution.

**NOTE:** Using the console, `address 127.0.0.1` will show the available resolutions for an
address, along with the metadata shown for those resolutions in memory. Only the best resolution
is written to the zone.

The metadata is refreshed in small batches.

##### accuracy of date stamps

The three timestamps (in seconds) which are present in the metadata are:

* **first** first seen
* **last** last seen
* **update** when the metadata was last updated

When loading the metadata for analysis, recommended practice is to treat `first` and `last` as deltas from
`update`; whether you choose to make the values positive or negative is up to the discretion and
convenience of the analyst.
