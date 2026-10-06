# Deprecated Technology Audit and Removal List

Scope: `ChangeLog`, `Makefile.in`, `configure.ac`, `etc/`, `scripts/`,
`misc/`, `tui/`. This is a list only — nothing is removed in this change.

**Load-bearing** = removing it today breaks boot, networking, storage
management or alerting on a default build. Those items need a replacement
first; they are *not* removal candidates yet.

## Prior modernization (already done, per `ChangeLog`)

| Change | ChangeLog | Residue found |
|---|---|---|
| lvmetad and clvmd removed from `rc.lvm2`/`rc.conf`, `rc.clvmd` deleted (branch `nix_lvmetad`) | "lvmetad and clvmd are deprecated in latest LVM2 version..." | Yes — see A1, A2 |
| Python 2 → 3 for all ESOS scripts; pip → pip3 | "updated all ESOS-specific Python scripts to be compatible with version 3" | None. Only `#!/usr/bin/python` hits are the *removed* lines in `misc/qla2xxx_scst.patch`. |
| `iproute2` added, Busybox `ip`/`tc` applets disabled (branch `add_iproute2`) | "added the 'iproute2' package (provides 'ip' program...)" | Yes — scripts still use net-tools style commands, see C1 |
| Web UI removed | "removed ESOS Web UI bits" | `--enable-nginx` remains as a bare server (see build-system audit) |
| perf-agent, lessfs deprecated | "removed perf-agent (deprecated)", "make lessfs (now deprecated) a build-time option" | lessfs still buildable, see B3 |

## A. Safe to remove (dead references, not load-bearing)

| # | Item | Where | Why it's dead | Suggested action |
|---|---|---|---|---|
| A1 | `rc.clvmd` in `LATE_SERVICES` | `etc/rc.d/common` line 8 | `etc/rc.d/rc.clvmd` no longer exists; `check_enabled` finds no `rc.clvmd_enable` so it is silently skipped | Drop the token from `LATE_SERVICES` |
| A2 | LVM2 configure flags `--with-lvm1=none`, `--with-clvmd=corosync`, `--with-cluster=internal`, `--enable-lvmetad` | `Makefile.in` `lvm2.chroot` | LVM2 2.03.x (in use: `lvm2-2.03.14`) removed LVM1/pool formats, clvmd and lvmetad; configure ignores these options | Remove the four flags; keep `--enable-lockd-dlm` and the rest. |
| A3 | `cciss` device handling (`/dev/cciss`, `cciss!cXdY` rename) | `tui/utility.c` (block device lists) | The `cciss` kernel driver was removed in Linux 4.14 (replaced by `hpsa`); ESOS ships 5.4 | Remove the `cciss` branches |
| A4 | Orphaned patches `cdk-5.0-20190303.patch`, `scst-3.7.x_20230120.patch`, `sg3_utils-1.45.patch` | `misc/` | No matching tarball in `dist_files` | Delete (also listed in the build-system audit) |

## B. Removal candidates (optional or not used by default, confirm with maintainers)

| # | Item | Where | Notes |
|---|---|---|---|
| B1 | `xmlrpc-c-1.39.13` | `Makefile.in` (`dist_files`, `xmlrpc-c.chroot` in `chroot_tgts`, installs `/usr/bin/xmlrpc`) | No other make target depends on `xmlrpc-c.chroot` and no in-tree script/RA/TUI calls `xmlrpc`. Only an end-user CLI. Confirm no external tooling relies on it, then drop the package. |
| B2 | Legacy vendor RAID CLIs: `MegaCLI` (superseded by StorCLI), `hpacucli` → `hpssacli` (both superseded by `ssacli`), 3ware `tw_cli` (3DM2), Areca `linuxcli` | `scripts/raid_tools.py`, `scripts/health_chk.sh` (`MegaCli64`), `tui/system.h` (`MEGACLI_BIN`) | `hw_raid_cli.py` (used by the TUI) only supports StorCLI/PerCLI/arcconf. Keep `health_chk.sh` MegaCLI checks until StorCLI equivalents exist. |
| B3 | `lessfs` (`--enable-lessfs`), `EnhanceIO` (`--enable-eio`, configure says "broken"), `btier` (`--enable-btier`, "broken") | `configure.ac`, `Makefile.in`, `misc/*.patch`, `etc/rc.d/rc.eio`, `rc.btier`, `misc/ocf/brick/btier` | All off by default and unmaintained upstream. Removing them also removes out-of-tree modules that block a newer LTS kernel. |
| B4 | `mysql-5.0.96`, `postgresql-9.6.13` | `Makefile.in` (`--enable-python_sql`) | Both long EOL; only for the optional Python SQL modules. |

## C. Deprecated but load-bearing (replace first, then remove)

| # | Item | Where | Why it's load-bearing | Replacement path |
|---|---|---|---|---|
| C1 | `ifconfig`, `route`, `brctl`, `vconfig`, `ifenslave`, `netstat`, `arp` (Busybox applets: `CONFIG_IFCONFIG/ROUTE/BRCTL/VCONFIG/IFENSLAVE/NETSTAT/ARP=y`) | `etc/rc.d/rc.2` (loopback: `ifconfig lo`, `route add -net 127.0.0.0`), `etc/rc.d/rc.network` (Perl; all interface/bond/bridge/VLAN setup, default-GW via `netstat -rn`), `misc/initramfs_init` | All network bring-up | `iproute2-5.9.0` is already built: port to `ip addr/link/route`, `ip link add type bridge/vlan/bond` (or sysfs bonding), `ip route show default`; then disable the Busybox applets in `misc/busybox-1.30.1.config`. |
| C2 | SysV init (`sysvinit-2.94`, `/etc/inittab`, `etc/rc.d/rc.*`, `etc/rc.d/common`) | `Makefile.in` (`sysvinit.chroot`), `misc/sysvinit-2.94.patch`, `misc/initramfs_init`, `etc/rc.d/rc.serial` (inittab edits), `scripts/iso_installer.sh`, `etc/rc.d/rc.pacemaker` (`runlevel`) | PID 1 and all service management | Short term: stay on sysvinit (3.x is still maintained). Long term: see the systemd migration note in the shell-modernization PR (`docs/modernization/shell-audit.md`). |
| C3 | `ssmtp-2.64` | `Makefile.in`, `tui/menu_system.c` (`mailDialog` edits `ssmtp.conf`), `tui/system.h`, `scripts/support_pkg.sh`, `etc/services` | Email alerting configured from the TUI | `msmtp-1.8.14` is already built (`rc.msmtpd`); move the TUI dialog and `/usr/sbin/sendmail` link to msmtp, then drop ssmtp. |
| C4 | `vixie-cron-4.1` | `Makefile.in`, `etc/rc.d/rc.2` | Scheduled jobs (log archive, health checks) | cronie (maintained vixie-cron fork) or Busybox `crond` (already enabled: `CONFIG_CROND=y`). |
| C5 | `sysklogd-new_remote_opt_20190715` | `Makefile.in`, `etc/rc.d/rc.syslogd` | System logging | Current sysklogd 2.x or rsyslog. |
| C6 | `egrep` | `etc/rc.d/common`, `rc.0`, `rc.sysinit`, `rc.rbdmap`, `install.sh`, `scripts/health_chk.sh`, `misc/ocf/*`, `misc/initramfs_init`, `Makefile.in` (`$EGREP` sed) | Used in `check_enabled()` → every rc script | Replaced with `grep -E` in the shell-modernization PR (except `misc/initramfs_init` / `Makefile.in`, which are build/initramfs paths). |

## Not deprecated (checked, no action)

- **LVM2 itself** (2.03.14) and `lvmlockd` — current replacement for clvmd.
- **iproute2** — present; the issue is the remaining callers of the old tools (C1).
- **eudev** — still used for udev without systemd.
- **Python** — all scripts are Python 3 (`#! /usr/bin/python3`); Python 3.9.5 itself is EOL, tracked in the build-system audit.
