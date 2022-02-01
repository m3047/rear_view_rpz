`heuristic.py` is symlinked to the module providing the heuristic function. We provide `standard_heuristic.py` but you might prefer your own.

## Association, Expiry and Heuristics

(Eventually this will be merged with main, and I may or may not remember to come back and delete this and
correct the verb tense. At the moment I'm working on instrumenting cache expiry and improving the fidelity
of the `TXT` record metadata written to the zone file. This is the explanation why.)

_Heuristics_ in this context refers to a value assigned to an option to gauge its desirability. In other
contexts a heuristic might incorporate information about our location in the problem space (or graph), the
time of day, the phase of the moon, the "cost" of the option. In this case the heuristic is based solely
on the data at hand. Personally I don't think that heuristics are acknowledged and studied with the
seriousness they deserve given their evident implicit presence in virtually all threat hunting activities.
(I wrote a pivot engine for DNS artifacts a few years ago.)

The heuristic was originally utilized to select one resolution to display from among however many are associated with
a given address. The heuristic turns out to be useful for selecting "less useful" resolutions, across
a selected cohort of addresses, for cache expiry.

Although the selected mechanisms, including the heuristic, work well enough for the load and
purposes I'm subjecting them to I am aware of a number of edge cases and I'm not sure how well it'd
perform. If I was trying to optimize for such a case I know I'd want visibility into what was occurring
and how the heuristic was performing and thus the console and the issue about the fidelity of metadata
(I presume you've discovered the Knime workflow.)

For _Association_ the maxim _longest (CNAME) chain with the least number of labels in the final FQDN; if
all other things are equal choose the one most requested_ works for me. But I do think it needs one improvement
to deal with addresses which don't share purposing but rather change purposing over a span of time. The
heuristic as-is works as well as it can when multiple names are resolving to the same address _right now_;
but if one name has been requested and then that stops and a different name is requested _from some point in
time going forward_ it's not going to pick that up so well. I think this is going to require tuning rather than
poking in the dark; hence the need for fidelity in the metadata.

#### So how do I steer this thing?

I figured maybe you'd ask. If you look at:

* `rearview.standard_heuristic`
* `rearview.Heuristics`
* `rearview.db.Resolution`

I would hope that that would be sufficient to explain what the heuristic does and the information it
has available to it. Otherwise I welcome an additional doc, feel free to submit a PR!

After that, download [KNIME](https://www.knime.com/) and load the [Rear View workflow](https://github.com/m3047/rear_view_rpz/blob/main/utilities/Rear_View-knime-workspace.tgz).

So now let's talk about the console. **NOTE:** The console has relatively extensive documentation, see `pydoc3 rearview.console`.

##### `a2z`

In order to reason about it when I was initially coding, there are two in-memory models: a _telemetry view_ which reflects what's
being seen from _Dnstap_ and a _zone view_ which reflects what's written to the actual DNS zone. This tells you about discrepancies
between those two models. You may see occasional discrepancies (updating of the two models is not atomic!) but they should be
transient. Not particularly useful unless something is broken.

##### `address 127.0.0.1`

This command shows you everything in the telemetry view which is known about an address's resolutions: what they are and
which is the heuristically "best" resolution, if there is one (also not an atomic operation). Good for satisfying random
curiosity.

##### `cache > 20`

That command will show you the sheep queued up for shearing (next in line to be considered for eviction) while
`cache < 20` will show you the sheep which most recently survived shearing (recycled to the beginning of the queue).

There is a little number next to each address representing the number of resolutions associated with it. You will
likely observe that the ones which are at the end have more resolutions associated with them than the ones which
are at the beginning of the queue.

There are also two numbers at the top, which should be the same most of the time (again, not atomic). You will also
likely notice that when you (re)start the agent, which is to say after the in-memory view has just been built from
what's on disk, that the number is less than whatever your `CACHE_SIZE` is and that over time it reaches that limit
and more or less stays there.

##### `evict 2`

`eviction 2` shows the log for the two most recent evictions. (See `cache` and note that it may be a while after you
restart the agent before there are any evictions in the log.)

This shows a variety of statistics, followed by a list of resolutions ordered heuristically from most likely to least
likely to be evicted in this round.

A variety of statistics are shown.

The very first number shown in the header is how many seconds in the past this eviction took place.

For resolutions:

* the **overage**, how many need to be evicted
* the **target** pool size
* the **actual** pool size which may be larger than the target because some addresses have multiple resolutions
* the **number remaining** after eviction

For addresses:

* how many were **selected** to achive the pool size
* how many were **recycled**, or survived shearing
* how many were **affected**, or had at least one resolution evicted
* how many were **deleted** because they had no remaining resolutions after shearing

_Affected_ includes both _deleted_ and some which were _recycled_. All three categories of addresses are shown,
you can infer what's going on by studying the lists.

##### `refresh 2`

`refresh 2` shows the log for the two most recent batch refresh events. The scheme for refreshing the metadata in the
DNS zone is to collect recently sheared sheep and make a batch out of them which is then committed to the zone as a
single update.

As with `eviction` the number of seconds ago when the batch was created is shown in the header, along with the _state_ for the batch:

1. **new** when it's just been created
2. **accumulating** while it's collecting entries to commit
3. **writing** while updating the zone
4. **complete** after the update is completed

Various statistics are shown, although some may not be available until the batch has completed.

Accumulating:

* **Add Calls** the number of times attempts were made (typically one per eviction) to add to the batch.
* **Total to Process** the number of addresses which have been available to add to the batch. This is capped at `BATCH_UPDATE_SIZE`.

Writing:

* **Elapsed Accumulating** the number of seconds which were spent accumulating addresses. The update occurs at most every `BATCH_UPDATE_FREQUENCY` seconds and is delayed until at least `BATCH_UPDATE_SIZE * BATCH_THRESHOLD` addresses have been accumulated.

Completed:

* **Batch Size** the actual size of the batch, as processed.
* **RCode** the DNS response code received from the DNS server.
* **Wire Size ...** over-the-wire request and response sizes.
* **Elapsed Processing** the number of seconds which were spent actually updating the zone (writing).

