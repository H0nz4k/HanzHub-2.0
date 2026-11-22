# Public Dashboard: real status, no fixture fallback

Prepared for the existing HUB2 runtime. Preserve the current UI and local-only
control boundaries. This does not activate MCP, change device state or expose
HubAgent, task submission, approvals, IoT commands, or private calendar data.

Problem: the hosted interface declines the local main-mode activation, begins
with static design metrics, and waits for all legacy API requests without a
deadline. The old cloud route sends status and dashboard reads to the legacy
health service rather than the current loopback-aware Dashboard.

Files:
- dashboard-web.patch: minimal patch against the discovered runtime preimage.
- dashboard-local.js: existing adapter with immediate unknown values, bounded
  reads and an actual registry count (not sample online devices).
- dashboard-public.js: remote read-only labels, no sample operational sections,
  and no loopback links that would point at the visitor's computer.
- preimage.json: checked SHA-256 baseline for the two runtime replacements.
- verify-render.py: verifies rendered fixture removal, remote boot ordering,
  preservation of LAN mode, and explicit opt-in demo separation.

Routing: reuse the existing redundant explicit /api/health route, changing its
path to ^/api/(health|services|dashboard|backup/status)(/|$), its service to the
existing Dashboard origin on port 4001, and HTTP Host Header to that origin's
authority. Move only this read-status route ahead of the generic /api rule.
Keep all remaining routes, DNS, Access policy and private control unchanged.
The selected current handlers are read-only; an accidental POST to those
paths is rejected by the existing write handler.

Before deployment verify both preimage hashes and no pre-existing public
adapter. Back up these exact runtime files and ownership/modes to a root-only
directory under /opt/hanzhub/dashboard. Deploy only the patched server and two
adapters. Restart only hanzhub-dashboard2.service. Roll back by restoring the
two preimages, removing only the newly installed public adapter and restarting
that service. Cloud rollback: restore /api/health -> previous port 4010 with
no HTTP Host Header override at original third position.

Validation before deployment: Python render assertions and Node --check.
Deployed and verified on 2026-11-23 (Europe/Prague):
- Public browser shows 12/12 checked services, two actual registered devices
  and the real failed daily backup state, not 10/13, 46 C or 2/3.
- Initial HTML is fixture-free before asynchronous reads.
- Henk remote view has a LAN-only notice, no demo task list.
- LAN ?hub=main still starts its existing live mode; its unavailable MCP
  status is unchanged and was not presented as a working agent.
- Node syntax and Python render regression checks passed after installation.
- Impeccable mechanical detector reported [] for both changed JS adapters.
- Desktop render verified. Browser viewport override did not apply reliably,
  so a mobile-width browser verification is not claimed.
- Rollback snapshot: /opt/hanzhub/dashboard/.rollback-public-data.05l55ygv
- Routing change reused the existing health route, moved to first position.
  DNS, Access policies and blocked build/ntfy routes are unchanged.

The count is a service HTTP-health result, not proof of physical device state.
Registry entries report online/offline/unknown as returned by the live
registry; unknown is displayed as registered, never as a confirmed online
device. A failed backup is displayed explicitly and was not repaired here.

dashboard-web.updated.py is a generated staging artifact, not a second source.
Apply dashboard-web.patch only to the checked preimage; pass the staged Python
path to verify-render.py before deployment. With no argument the verifier uses
the installed server.
