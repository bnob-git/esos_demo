# Shell Script Audit (ShellCheck)

Scope: `install.sh`, `scripts/*.sh`, `misc/ocf/*/*` resource agents,
`etc/rc.local`, `etc/rc.d/*` (59 files; `rc.eio` and `rc.network` are Perl
and excluded).

Reproduce (ShellCheck 0.8.0):

```sh
F="install.sh scripts/*.sh misc/ocf/*/* etc/rc.local \
   $(ls etc/rc.d/* | grep -v -E 'rc.eio$|rc.network$')"
shellcheck -S warning -f gcc $F
```

| Severity | Before | After |
|---|---|---|
| error | 56 | 0 |
| warning | 404 | 320 |
| all (incl. info/style) | 1729 | 1573 |

## Fixed

- **SC2068** (48 rc scripts): `check_args ${@}` → `check_args "${@}"`;
  `${!nodes[@]}` and `$@` in `misc/ocf/onesty/scst_aluadg`, `stmf-ha/zfs`.
- **Deprecated `egrep`** → `grep -E` in all in-scope files (`/bin/egrep` →
  `/bin/grep -E`, GNU grep 3.3). `install.sh` no longer lists `egrep` as a
  required tool.
- **Real bugs in `misc/ocf/esos/syncro`**:
  - SC2203/SC2077: `[[ ${blk_dev_name}" =~ "^sd[a-z].* ]]` was one quoted
    word, so the test was always true. Now `[[ "${blk_dev_name}" =~ ^sd[a-z] ]]`.
  - SC2152: `get_ctrlr_id` returned `-1` (really 255) while the caller tested
    `-ne -1`, so "not found" was never detected. Now returns/checks 255.
- **SC1115**: `misc/ocf/brick/btier` shebang `# !/bin/bash` → `#!/bin/bash`.
- **SC2148**: `etc/rc.d/common` (sourced library) gets a
  `# shellcheck shell=bash` directive.
- **SC2045**: `scripts/startup.sh` loops over a glob instead of `ls`.
- **SC2164 / unhandled exit codes**: `cd` in `rc.rbdmap` stop() returns 1 on
  failure; `rc.openibd` uses `cd ... &&` in the subshell.
- **SC2166**: `[ a -a b ]` / `[ a -o b ]` split into `[ ] && [ ]` in
  `etc/rc.d/common`, `scripts/crm_mon_email.sh`, `syncro`.
- **SC2062 / SC1083 / SC2184**: quoted grep patterns (`install.sh` macOS
  path, `rc.rbdmap`), `awk {'print $1'}` → `awk '{print $1}'`, quoted
  `unset` array element.
- **SC2155**: `local x=$(...)` split in `scst_aluadg` so return codes are not
  masked.
- **SC2113**: `function foo {` → `foo() {` in `scripts/usb_sync.sh`.
- **SC2086 inside `[ ... ]` tests** (60 sites): word splitting is never
  intended in a test operand, so these were quoted mechanically
  (ShellCheck's own fix, restricted to single-bracket tests).

## Not fixed (intentional / out of scope)

- **SC2086 outside tests (~1000)**: many expansions rely on splitting, e.g.
  `eval ${DAEMON} ${USER_OPTS}` (user options from `rc.conf`),
  `kill $(pidof ...)` (multiple PIDs), option strings in RAs. A blanket fix
  would change behavior; needs per-site review.
- **SC2046 (45)**: same reason — mostly `kill -TERM $(pidof ...)`.
- **SC3xxx (≈160)**: "bashism in `#!/bin/sh`". ESOS links `/bin/sh` to bash
  (`Makefile.in`: `$(LN) -v bash $(CHROOT_DIR)/bin/sh`), so `source`,
  `local`, `[[ ]]`, `==` all work. Lint with `shellcheck -s bash` or switch
  shebangs to `#!/bin/bash` in a separate change.
- **SC2154/SC2034/SC1090**: variables come from sourced `rc.d/common` or
  the OCF shell function library.
- **SC2044/SC2010** (`for x in $(find|ls)`): sysfs names have no
  whitespace; rewriting the SCST RA loops is a larger refactor.
- **SC2053/SC2254** in `onesty` RAs: unquoted RHS may be meant as a glob;
  needs owner review.
- **SC2181** (`[ $? -ne 0 ]`): style only.

## Systemd migration path (note only — not implemented)

ESOS boots with sysvinit 2.94 (`/sbin/init` + `/etc/inittab`) and
`etc/rc.d/rc.sysinit` → `rc.2` / `rc.0`, which walk `EARLY_SERVICES` and
`LATE_SERVICES` in `etc/rc.d/common` and gate each `rc.*` with
`<name>_enable=` in `/etc/rc.conf`. A migration could go:

1. **Inventory**: one unit per `rc.*` script. Most are simple daemons
   (`rc.sshd`, `rc.acpid`, `rc.snmpd`, ...) → `Type=forking`/`simple` units
   using `EnvironmentFile=` for the `*_opts` values in `rc.conf`.
2. **Ordering**: translate the `EARLY_SERVICES`/`LATE_SERVICES` order into
   `After=`/`Requires=` (e.g. `rc.lvm2` after `rc.mdraid`, `rc.scst` after
   `rc.fsmount`, cluster stack `sbd → corosync → dlm → lvmlockd →
   pacemaker`). Storage units should be `Before=` SCST/NVMe-oF targets.
3. **rc.conf compatibility**: a generator (`/usr/lib/systemd/system-generators/`)
   can read `*_enable=YES` from `rc.conf` and enable units, so the TUI and
   existing configs keep working during the transition.
4. **rc.sysinit / rc.0**: replace with stock units (`systemd-udevd`,
   `systemd-modules-load`, `systemd-remount-fs`, crypttab/fstab
   generators) plus small ESOS units for the persistent config sync
   (`conf_sync.sh`, `usb_sync.sh`) and the MD boot-array shutdown
   handling in `rc.0`.
5. **Build impact**: replace `sysvinit.chroot` + `eudev` with systemd (which
   also brings udev), add journald or keep syslog forwarding, and update
   the initramfs (`misc/initramfs_init`) hand-off. This also affects image
   size (a goal of ESOS), so measure before committing.
6. **Pacemaker/OCF**: resource agents are unaffected; pacemaker can use
   `systemd:` resources alongside `ocf:` ones.

Alternative with lower churn: stay on sysvinit (3.x is maintained) and
keep `rc.d`, applying the quoting/exit-code fixes above.
