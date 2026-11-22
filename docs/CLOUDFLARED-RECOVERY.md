# Cloudflare connector recovery — 2026-11-22

## Observed cause before recovery

Before recovery HUB2 had no installed cloudflared binary, systemd unit,
container or running connector. Cloudflare reports the existing hanzhub-hub tunnel Down with zero
replicas. An authenticated browser reproduces Error 1033. The dashboard and
health API respond locally.

The read-only migration archive contains the original token-based service.
Its token was decoded privately and its tunnel UUID matched the existing
Cloudflare tunnel. No token was rotated and no new tunnel was created.
The archived /usr/local/bin/cloudflared is a symlink to a missing package
binary, so restoring that entry alone cannot start the connector.

## Installed connector

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

The user explicitly approved this pinned installation after the initial
automatic approval rejection. The downloaded binary matched the SHA-256 above
and the official 37,818,397-byte asset size. Version/help checks ran as nobody;
the cloudflared binary was never executed as root. The service passed
systemd-analyze verify and was enabled and started on HUB2.

Runtime token: root-owned 0600; containing directory: root-owned 0700.
The active service uses DynamicUser=yes with User=cloudflared.
Installed unit SHA-256:
b34e37a6955a5d48ec9d1002925c5882f3f609faafd6e76d0953076e44ec3e7d

Private provenance and installation receipts are retained in the root-only
/var/lib/hanzhub/cloudflared-recovery directory, outside Git.

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
After activation on 2026-11-22 at 22:44 UTC:

- Four registered QUIC connections, including Prague and Frankfurt edges.
- Cloudflare dashboard: Healthy, replica hostname HUB2, linux_arm64 2026.11.1.
- systemd: enabled, active/running, zero restarts during verification.
- Connector metrics: four HA connections, zero tunnel request errors.
- An authenticated browser opened https://hanzhub.cz/living-glass/ and
  displayed the real dashboard instead of Error 1033.
- The same public HTTPS browser path returned JSON from /api/health and
  /api/services. HTTP 200 responses are also recorded in connector metrics.
- Anonymous HTTPS requests to root and /api/health returned 302 to Access.
- build.hanzhub.cz returned Access Forbidden (403); its origin route is also
  http_status:404. ntfy.hanzhub.cz returned 404.
- HubAgent still listens only on its existing LAN address, not loopback or
  all interfaces. No route was added to it; its binding was not changed.

The tunnel outage is resolved. This does NOT certify every dependent app.
Health JSON still reports several unavailable services. The dashboard also
has existing missing /api/presence/state and /api/display endpoints and
unavailable remote IoT registry/local-only data. Calendar remote availability
is not claimed. These application issues were not repaired or bypassed as
part of restoring transport and preserving access restrictions.
