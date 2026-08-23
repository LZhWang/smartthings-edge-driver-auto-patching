# Upstream profile corpus

Verbatim device profiles from
[SmartThingsCommunity/SmartThingsEdgeDrivers](https://github.com/SmartThingsCommunity/SmartThingsEdgeDrivers),
Apache-2.0, vendored as test fixtures.

They exist because `schema/profile.schema.json` is only meaningful if it accepts
the profiles the platform actually ships. An earlier revision declared
`additionalProperties: false` on capability entries without checking real data,
and consequently rejected 13 of 38 upstream profiles (34%) over the `config`
key. Validating against a real corpus is what keeps that from recurring.

Refresh them from upstream when the platform's profile shape changes.
