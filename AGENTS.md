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
