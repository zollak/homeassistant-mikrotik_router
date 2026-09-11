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

## 2026-06-30 -- synced with upstream (v2.2.4)
Merged upstream tomaae/master (3 commits): connection-method selection improvement,
user-access-policy refactor, Python 3.14 compatibility (#484). Clean auto-merge, no
conflicts. Our update-popup guard (coordinator.py + update.py) is retained. Our former
v2.2.1 librouteros connect() hack is now **superseded** by upstream's proper login_method
handling (plain/token -> librouteros callable) in mikrotikapi.py -- we keep upstream's
version. Released v2.2.4.

## 2026-09-11 -- synced with upstream (v2.2.6)
Merged upstream tomaae/master (19 commits): HA 2026.8/2026.9 compatibility migrations
(device-tracker zone model, ConfigEntry.runtime_data, device_info, entity service
async_setup, config-entry identity modernization) + fixes (non-blocking RouterOS calls in
the HA event loop, serialized commands for concurrent switch timeouts, device-tracker
registry ownership, GPS none-value). Two conflicts, both non-runtime: `.github/workflows/release.yml`
(kept OURS -- fork Actions disabled, manual zip release) and `manifest.json` (took upstream's
content, set version 2.2.6). Runtime files (coordinator.py, update.py) auto-merged clean.
RECONCILE: our phantom "update available (unknown)" guard is RETAINED in coordinator.py + the
RouterOS update entity (MikrotikRouterOSUpdate is_on/latest_version), verified present post-merge;
upstream still returns raw latest-version, so the fix is still needed. Upstream added a new second
update entity (MikrotikRouterBoardFWUpdate, RouterBOARD firmware) with a different
current-vs-upgrade mechanism -- NOT the same phantom bug, no patch needed. All .py AST-parse OK.
Released v2.2.6.
