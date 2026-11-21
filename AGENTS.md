# AGENTS.md — HanzHub 2.0

## Mission
HanzHub is a Raspberry Pi development/operations host for existing SW/HW projects. Preserve working apps and data. A task is complete only when a real result is verified on the target system, not when a PR exists.

## Deployment contract
- Install all **HanzHub-managed application runtimes** under `/opt/<app>/` or `/opt/hanzhub/<component>/`. Never deploy application trees into arbitrary home directories. Existing paths are discovered and migrated deliberately, not silently overwritten.
- Runtime configuration belongs in `/etc/hanzhub/<app>/`, persistent data in `/var/lib/hanzhub/<app>/`, optional file logs in `/var/log/hanzhub/<app>/`; systemd units in normal systemd locations. Honor OS/packaging exceptions and document them.
- Prefer `hanzhub-<app>.service` and `hanzhub_<app>` for **newly deployed** services/containers, with migration aliases where required. Never break existing consumers through premature renaming.
- Each app: declarative manifest (identity, repo and pinned source SHA, services, ports, routes, GPIO, APIs/MCP, dependencies, config/data mounts, health, backup and rollback). Never store secrets in Git.
- Check port, GPIO, API route and service-name collisions before deploying. Keep Henk and the Dashboard independent from each other and from applications.
- Reuse existing tools such as systemd, Docker Compose, libgpiod, Ansible where suitable; do not invent a new generic framework without a compelling evaluated gap.

## Data and filesystem
- Before any destructive storage operation: identify physical device by stable serial, WWN or UUID, device tree, partitions, mount flags, system use and dependencies. Distinguish SD system disk, old backup disk and external export destination.
- **Never format, repartition, fsck a mounted filesystem, remount read-write after errors, or erase a disk on ambiguous identity or without a separately proven independent copy and explicit user approval identifying exact device.**
- Do not treat the existing Patriot SSD as disposable: prior report says `ro,norecovery` and it may contain the only backups.
- Use a **separate verified writable destination** for exports when needed. Restore-test before any OS replacement.
- Make application-consistent data exports (database-native dumps, SQLite online backup/transaction-safe snapshot, persistent Docker volumes). Do not copy live DB files blindly.
- Produce manifest/checksums, verify all payloads, and perform an isolated restore test before relying on a bundle.

## Access and change control
- Prefer read-only discovery first. Codex access on HUB, if enabled, must use a distinct SSH key/account, time limit and audit trail. Scope administrative escalation and revoke automatically.
- Never store private keys, tokens, passwords, DB contents or sensitive network details in this public repository.
- Do not grant cloud agents permanent unrestricted root access. No changes to live services, GPIO outputs, tunnels or disks without an approved precise plan.
- Never disable safety gates or bypass existing user approvals. Fail closed on unknown/ambiguous state.
- Always retain the original boot medium and a tested rollback path until migration is accepted.

## Migration target
- HanzHub Dashboard 2.0 and a consistent design on **7-inch HDMI only**; 3.5-inch ILI9486 is excluded from UI migration (not physically removed without an explicit request).
- Preserve Henk flame/animations/assets and the existing Henk Studio (even if partially broken); fix rather than discard.
- Preserve retained applications and their original behavior/data, e.g. REDcheck, Meteo, IoT, InfoLCD dependencies, radios, CoinList, LoRa, Calendar, stream, Whiteboard.
- Document what is preserved, retired, held for review, and what remains unverified.

## Deliverables and reporting
- Phase 0: signed-off read-only inventory and storage identity; no system changes.
- Phase 1: runnable export/verify/restore tooling and per-app manifests, plus restoration test evidence.
- Phase 2: only after explicit go-ahead, new clean OS on a **different** boot medium, followed by selectively verified app restore.
- Status fields: discovered / prepared / exported / verified / restore-tested / approved / restored / live-verified. Never promote one state to another without evidence.


## Proven operating pattern — HUB2 bring-up (2026-11-21)

The successful HUB2 run on branch `hub2-bringup` (commit `9e04b37`) used **one autonomous, outcome-driven local Codex session** rather than a chat relay of individual commands:

1. Work **directly on the target HUB2**, using already restored application files, existing documentation and real system state. Do not repeat completed inventory or synthetic tests without a specific reason.
2. Iterate independently: **inspect → execute the next safe step → read its actual output → diagnose → correct → verify → commit/report**. Do not stop after writing a plan or installer.
3. Focus on recovering concrete user-facing services using existing Compose/systemd/runtime tools. Reuse proven migrations; avoid building another broker/abstraction layer for a simple deployment.
4. Run bounded checks **at the point of change**: service status, local HTTP/API response, data integrity if relevant, and boot-enable status. A 200 response proves endpoint response, not every feature or peripheral.
5. Keep `/opt` deployment policy, preserve new OS/SSH/accounts, avoid writing secrets to Git, and never auto-activate relays, physical GPIO, risky migration or outdated Operations Broker without authorization. Human approves genuinely risky/root steps.
6. Maintain an application matrix: **files restored / service starts / API answers / functional or hardware verified / missing prerequisites**. Report unsupported/unverified functionality explicitly.
7. Commit the scripts, units and sanitized evidence during the run; push to a development branch when available. Do not lose working progress if network/GitHub is blocked. Never commit private export bundles or credentials.
8. Aim for **maximum independently verified production progress per session** rather than many preparatory PRs or repeated permission requests. When one task is blocked, continue independent safe tasks.

Evidence at end of first bring-up: **12 systemd units running** and **17 local HTTP/HTTPS probes**, with open gaps including REDcheck, data and hardware/peripherals. This is a pattern of work, not blanket permission to bypass safety rules or proof that every app is functional.
