# Build System Audit (`Makefile.in`, `configure.ac`, `misc/`)

Scope: audit of the package manifest in `Makefile.in` (`dist_files`) and the
patch/config sets in `misc/`. The `configure.ac` / `Makefile.in` entry points
are unchanged.

## 1. Kernel patch/config sets

The kernel build (`esos_kernels.chroot`) resolves its patch and config by the
name of the single extracted source tree (`$(notdir $(linux_src))`), and
`dist_files` pins `linux-5.4.288.tar.xz`. Only these files are ever read:

- `misc/linux-5.4.288.config`
- `misc/linux-5.4.288.patch`
- `misc/linux-5.4.288-debug.patch` (only with `--enable-debug_kernel`)

Removed (unreferenced by `Makefile.in`, `configure.ac`, checksums or scripts;
superseded by 5.4.288 and still available in git history):

| Version  | `.config` | `.patch` | `-debug.patch` |
|----------|-----------|----------|----------------|
| 5.4.12   | removed   | removed  | removed        |
| 5.4.45   | removed   | removed  | removed        |
| 5.4.69   | removed   | removed  | removed        |
| 5.4.145  | removed   | removed  | removed        |
| 5.4.190  | removed   | removed  | removed        |
| 5.4.212  | removed   | removed  | removed        |
| 5.4.229  | removed   | removed  | removed        |

### Path to a maintained LTS kernel

The 5.4 LTS line reached upstream end-of-life in December 2025; 5.4.288 no
longer receives fixes. Suggested migration:

1. **Pick a target LTS** from <https://www.kernel.org/category/releases.html>
   (6.12 is the newest LTS at time of writing; 6.6 or 6.1 are fallbacks if an
   out-of-tree module lags). Confirm the projected EOL date on kernel.org
   before committing.
2. **SCST compatibility first.** The kernel is coupled to
   `scst-3.9.x_20241230` (+ `misc/scst-3.9.x_20241230.patch`) and the
   `qla2x00t` / `qla2x00t-32gbit` target drivers. Validate SCST builds against
   the target kernel before anything else; bump SCST if required.
3. **Re-check out-of-tree modules** built in `esos_kernels.chroot`: mhvtl,
   EnhanceIO (`--enable-eio`), btier (`--enable-btier`), ZFS 0.8.3
   (`--enable-zfs`, does not support 6.x kernels — needs OpenZFS 2.2+),
   cls_switchtec (`cls_switchtec-4.1.0_5.4_*`, 5.4-specific), and the optional
   vendor drivers (MLNX OFED, ATTO, Celerity, bnxt_en, qla2xxx_scst).
4. **Rebase `linux-5.4.288.patch`.** It carries bcache (`btree.c/.h`),
   `dm-raid.c` and `md.c` fixes; drop hunks already upstream in the target
   LTS and forward-port the rest.
5. **Regenerate the config** with `make olddefconfig` from
   `linux-5.4.288.config`, review new/removed symbols (keep
   `CONFIG_WATCHDOG_SYSFS`, `CONFIG_DM_DELAY/DUST/FLAKEY`, fault injection),
   and regenerate the `-debug.patch` against the new config.
6. Add `linux-6.x.y.{config,patch,-debug.patch}`, update `dist_files` and both
   `CHECKSUM.*` files (e.g. via `pkg_update.sh`), then delete the 5.4.288 set
   in the same change so only one kernel set lives in `misc/`.

## 2. EOL / unmaintained dependencies

Flagged only — no version bumps in this change.

| Package (in `dist_files`) | Status | Notes / suggested target |
|---|---|---|
| `openssl-1.1.1w` (+ `misc/openssl-1.1.1w.patch`) | EOL upstream since 2023-09-11 (1.1.1w was the final public 1.1.1 release) | Move to the 3.5 LTS line. Dependents: openssh, Python, curl, nginx, lessfs, ssmtp, stunnel, Linux-PAM chain. API break (1.1 → 3.x) — expect patch work. |
| `glibc-2.29` (+ `misc/glibc-2.29.patch`) | 2019 release, no longer on an upstream maintained branch | Bump together with the toolchain (`gcc-9.1.0`, `binutils-2.32`); required anyway for a 6.x kernel's headers. |
| `qemu-5.2.0` (+ `misc/qemu-5.2.0.patch`, `--enable-qemu` only) | Dec 2020; upstream only maintains recent releases | Current QEMU stable; pulls pixman, libguestfs, etc. |
| `libvirt-6.10.0` (+ `misc/libvirt-6.10.0.patch`, `--enable-qemu` only) | Dec 2020; libvirt has no LTS, only current releases are fixed | Bump in lockstep with QEMU. |
| `linux-5.4.288` | 5.4 LTS EOL Dec 2025 | See section 1. |

Other long-unmaintained packages noticed during the audit (candidates for a
follow-up dependency sweep): `gcc-9.1.0`, `binutils-2.32`, `Python-3.9.5`
(3.9 EOL Oct 2025), `pacemaker-1.1.20` / `corosync-2.4.6` (1.1.x / 2.x
superseded by pacemaker 2.x+/corosync 3.x), `nginx-1.16.0`,
`postgresql-9.6.13` (EOL Nov 2021) and `mysql-5.0.96` (both only with
`--enable-python_sql`), `zfs-0.8.3`, `grub-2.02`, `curl-7.64.1`,
`sudo-1.8.27`, `nss-3.43`, `cdk-5.0-20161210`, `ncurses-6.1`,
`setuptools-28.6.0`.

## 3. Other stale files in `misc/` (not removed)

These patches do not match any `dist_files` entry, so `apply_pkg_patch`
never selects them. Left in place pending maintainer confirmation:

- `misc/cdk-5.0-20190303.patch` — tarball in use is `cdk-5.0-20161210`.
- `misc/scst-3.7.x_20230120.patch` — tarball in use is `scst-3.9.x_20241230`.
- `misc/sg3_utils-1.45.patch` — tarball in use is `sg3_utils-1.48`.

## 4. `enable_nginx` / `enable_simple_tui` flags (audit only, no changes)

- `--enable-nginx` (`Makefile.in` `enable_nginx`): adds `nginx-1.16.0` to
  `dist_files` and `nginx.chroot` to `chroot_tgts` (built with
  `--with-http_ssl_module`, against openssl 1.1.1w). The only runtime pieces
  are `etc/rc.d/rc.nginx` and `rc.nginx_enable=NO` in `etc/rc.conf`. No web
  UI, nginx config or web content is shipped in this repo — the flag provides
  a bare HTTP server only. If kept, it inherits the nginx 1.16 and
  openssl 1.1.1 EOL issues above.
- `--enable-simple_tui` (`enable_simple_tui`): adds `-DSIMPLE_TUI` to
  `tui_cpp_flags`, which compiles an alternate *text* front-end in
  `tui/main.c` (one scroll menu plus an IP-address label, no CDK menubar).
  It's another TUI variant, not a web UI.
- Both default to `no`. The product UI is still the CDK/ncurses TUI only.
