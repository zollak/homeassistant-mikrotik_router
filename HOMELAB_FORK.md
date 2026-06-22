# Homelab fork notes

This is Zoltán's maintained fork of
[`tomaae/homeassistant-mikrotik_router`](https://github.com/tomaae/homeassistant-mikrotik_router).

The upstream maintainer is inactive (no release since v2.2 / 2025-05) and upstream
`master` does not work with current `librouteros` + recent Home Assistant cores. HACS
installs from a branch/release, so we keep our working build here.

## Branch model

- **`master`** — mirror of upstream `tomaae:master`, left unmodified so upstream changes
  are easy to see and merge.
- **`homelab`** — our working branch: upstream `master` + the minimal fixes below.
  HACS (custom repository) tracks this branch / its tagged releases.

## Divergence from upstream `master`

### 1. `mikrotikapi.py` — librouteros `connect()` fix

Upstream passes `login_methods` (wrong keyword) with a string value to
`librouteros.connect()`. Current `librouteros` (>=3.4.1, manifest requirement) expects
`login_method` (singular) and a **callable**. Symptoms:
`connect() got an unexpected keyword argument 'login_methods'`, then after a naive
rename, `'str' object is not callable`.

Fix: **remove the `login_method` kwarg entirely** from `connect()`'s kwargs dict, so
`librouteros` uses its own default `login_method=plain` (the correct callable). The
integration still stores `self._login_method = "plain"` but no longer passes it.

(Note: the options-flow `config_entry` read-only-property crash that hit older installs
on HA 2024.12+ is already fixed in upstream `master` via `self._config_entry`, so it is
NOT re-patched here.)

### 2. `manifest.json` — version

`version` bumped `0.0.0` → `2.2.1` so HACS shows a real version for this fork build.

## Upstream PR

The `login_method` fix matches the intent of existing open upstream PRs (#476 / #486 /
#480). If upstream ever merges one, rebase `homelab` onto the new `master` and drop the
local patch.

## Re-syncing with upstream

```
git remote add upstream https://github.com/tomaae/homeassistant-mikrotik_router.git
git fetch upstream
git checkout master && git merge --ff-only upstream/master && git push origin master
git checkout homelab && git rebase master && git push --force-with-lease origin homelab
```
