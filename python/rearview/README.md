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

So now let's talk about the console. **NOTE:** The console has relatively extensive documentation, see `pydoc3 rearview.console`
([console.md](console.md) in this directory).

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
* **Total to Process** the number of addresses which have been available to add to the batch. The actual batch size is capped at `BATCH_UPDATE_SIZE`; this number may be larger than that, reflecting the total number prior to capping.

Writing:

* **Elapsed Accumulating** the number of seconds which were spent accumulating addresses. The update occurs at most every `BATCH_UPDATE_FREQUENCY` seconds and is delayed until at least `BATCH_UPDATE_SIZE * BATCH_THRESHOLD` addresses have been accumulated.

Completed:

* **Batch Size** the actual size of the batch, as processed.
* **RCode** the DNS response code received from the DNS server.
* **Wire Size ...** over-the-wire request and response sizes.
* **Elapsed Processing** the number of seconds which were spent actually updating the zone (writing).

## The Thoughtful Attenuator

This is more or less the followon screed to the foregoing one, reviewing the objectives of the heuristic
and its components. It ends with a discussion of the _attenuator_ which was alluded to as a missing piece
previously.

The core functional purpose of the heuristic is to answer:

* Given multiple possible names resolving to an address, which one do I choose to display?

To do so, the simple rule of thumb (all other things being equal) to me seems to be _the longest CNAME chain ending
in the FQDN with the least number of labels_. I claim experience. ;-)

A secondary purpose turns out to be:

* Which entries should I evict from cache?

which hints at the need for something based on time or usage. Once you start thinking about it though,
that doesn't sound like a risible goal for the heuristic in terms of the primary objective either.

Cutting to the chase, we get the general outline of a formula:

    depth_of_chain / number_of_labels + boost(time,usage) / attenuator
    
My first instinct was to boost based on time since first seen but as a thought experiment: how much traffic would
a different FQDN need to get for you to want to see it instead? Based on that I tried simply ln(query_count)
and it seems to work well enough... except for a few which get 10s or 100s of thousands of queries. (Although none
of those have gone dark, they just keep going!)

    depth_of_chain / number_of_labels + ln(query_count) / attenuator


So what to do about the attenuator? I've been computing a query_trend:

    T1 = 0.9*T0 + 0.1*last_seen
    
which eventually converges to the mean or linear query rate:

    T --> first_seen / query_count
    
assuming that the query rate is linear, of course. It's not, which is why I'm using that trend computation which
tends to give more importance to recent events (I'm using a coefficient of **0.1**). That was a hunch, again
I blame experience. Various other things were explored dividing the query count by various time periods before
or after taking the logarithm. Eventually I settled on

    depth_of_chain / number_of_labels + ln(query_count) / (1 + query_trend)
    
as the most promising. The next thing I tried was to address a deficiency in the software computation, which is that
query_trend is only updated when a new query occurs:

    depth_of_chain / number_of_labels + ln(query_count) / (1 + 0.9*query_trend + 0.1*last_seen)
    
That looked better. I could even steer it over a "cliff" (345600 is the number of seconds in four days):

    1 + ( (0.9*query_trend + 0.1*last_seen) / 34560 )^2
    
So why do I use 1/10 of 345600 there? That's because I want the cliff to be in four days, but I'm only adding 1/10 of
the time when updating the query trend ergo 34560. But that does mean that if something _averages_ 9.6 hours, or
in other words approaches that linear mean, that it will suffer unfairly. At this point I've gotta say, I don't
see much impact. However, I think there is one better evolution (172800 is the number of seconds in two days):

    1 + ( sqrt(query_trend^2 + last_seen^2) / 172800 ) ^ 2

in other words:

    depth_of_chain / number_of_labels + ln(query_count) / (1 + ( sqrt(query_trend^2 + last_seen^2) / 172800 ) ^ 2)
    
Yes I am sacrificing somewhat on the position of the cliff, to keep the attenuation at 1/16 at 8 days; I suppose I could
raise it to a higher power than 2 to make the cliff steeper, that would be another option.


So anyway that's what I'm recommending now.

This seems to suit the basic maxim (long chains and short fqdns), while boosting results seen a lot. After several
days of inactivity the boost is increasingly attenuated (down to 1/16th after 8 days).

Eventually the boost is essentially gone, however if the same result is seen again it will be "remembered" and boosted
much more quickly.
