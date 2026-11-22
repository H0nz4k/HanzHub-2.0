# Cloudflare connector recovery — 2026-11-22

## Observed cause

HUB2 has no installed cloudflared binary, systemd unit, container or running
connector. Cloudflare reports the existing hanzhub-hub tunnel Down with zero
replicas. An authenticated browser reproduces Error 1033. The dashboard and
health API respond locally.

The read-only migration archive contains the original token-based service.
Its token was decoded privately and its tunnel UUID matched the existing
Cloudflare tunnel. No token was rotated and no new tunnel was created.
The archived /usr/local/bin/cloudflared is a symlink to a missing package
binary, so restoring that entry alone cannot start the connector.

## Prepared connector

Source: migration/cloudflared.service. Install as
/etc/systemd/system/cloudflared.service, keeping the historical service name.
It uses DynamicUser and systemd LoadCredential instead of putting a secret in
ExecStart. Store the existing token at /etc/hanzhub/cloudflared/tunnel-token,
owned by root with mode 0600, inside a root-owned 0700 directory.
Never copy the archived token-bearing service into Git.

Official ARM64 release selected from cloudflare/cloudflared GitHub metadata:

- Version: 2026.11.1
- Asset: cloudflared-linux-arm64
- SHA-256: b155cec3e48e489cfb8e5c602769fb8c771083018d8881d68b4d18a791567c5a
- URL: https://github.com/cloudflare/cloudflared/releases/download/2026.11.1/cloudflared-linux-arm64

The binary has NOT yet been downloaded, installed or run. Automatic approval
review rejected downloading and executing a new binary as root. Explicit
approval was requested for the pinned, hash-verified binary, with version/help
checks and the connector itself running only as an unprivileged account.

## Cloudflare routing changes already applied

DNS and Access policies are unchanged. Existing route ordering is unchanged.

- hanzhub.cz dashboard route: HTTP Host Header now equals its existing
  origin authority (the existing LAN origin, port 4001). This is necessary
  because the current server rejects Host: hanzhub.cz with HTTP 400.
  The service URL itself is unchanged.
- ntfy.hanzhub.cz: service changed from loopback port 4014 to http_status:404.
  On HUB2 that port belongs to Radioama, not ntfy. Do not expose that service
  through an obsolete notification route.
- build.hanzhub.cz: service changed from loopback port 4088 to http_status:404.
  HubAgent now uses port 4088 on its LAN address. Keep it private and prevent
  future bind-address changes from exposing it through the obsolete route.

Calendar and other local-only data protections in the dashboard are unchanged.
The calendar route still has its historical Host behavior; end-to-end calendar
availability is not claimed. The main health/services API routes still use
their original origin on port 4010.

## Rollback

Before activating, require no pre-existing target unit/binary/token and verify
the original token identity and the downloaded binary SHA-256. Retain the
root-only recovery staging directory and the original archive read-only.

To undo activation: sudo systemctl disable --now cloudflared.service.
Remove only the exact files created by this recovery after checking their
hashes against the recorded installed files, then daemon-reload.
There was no previous active cloudflared installation on HUB2 to restore.

To undo the dashboard header adjustment, clear only that route's HTTP Host
Header setting. The original values of the blocked obsolete routes are
documented above, but do NOT restore them until service identity and privacy
are verified again. Do not alter DNS, Access policy, HubAgent binding or SSH.

## Verification checkpoint

Confirmed: LAN dashboard redirects to /living-glass/; local /api/services and
/api/health return HTTP 200/JSON; Cloudflare HTTPS and edge-name DNS resolution
work from HUB2. Existing Access login is still enforced for anonymous requests.
The authenticated public browser still reports 1033 while no connector runs.

Pending: pinned binary approval/installation; unit validation; enabled/running
service; connector logs showing registrations to Cloudflare; Cloudflare Healthy
status; authenticated public dashboard plus health/services JSON; confirmation
that obsolete build/ntfy routes do not expose private services.
