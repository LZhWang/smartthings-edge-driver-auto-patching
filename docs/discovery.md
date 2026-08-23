# Discovering drivers

Enumerate Edge drivers and their Zigbee fingerprints from GitHub or a local
clone, and flag drivers that have no capability mapping yet. This is the
`discovery` component, reachable as `edgeloom discover`.

## Driver Discovery Pipeline

Use the discovery CLI to scan either the public SmartThings Edge repository
directly from GitHub or any local clone that contains official drivers. The
tool aggregates every `fingerprints.yml`, summarizes the devices they target,
and highlights drivers that still lack capability mappings in
`custom_capability_list.config`.

Discover via GitHub (requires internet; optional `GITHUB_TOKEN` for higher
rate limits):

```bash
edgeloom discover \
  --source github \
  --repo SmartThingsCommunity/edge-drivers \
  --branch main \
  --output discovery/catalog.json
```

Work offline against a local clone (or any folder that holds driver
directories with `fingerprints.yml`):

```bash
edgeloom discover \
  --source local \
  --local-dir ~/edge-drivers \
  --driver-subpath drivers \
  --output discovery/catalog-local.yaml \
  --format yaml
```

`unsupported_drivers` in the generated report flags candidates that have no
entry in `custom_capability_list.config`, making it easy to decide which
drivers should be patched next.

