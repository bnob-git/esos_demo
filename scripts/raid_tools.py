#! /usr/bin/python3

# This script is used to install propietary CLI RAID tools in ESOS. With no
# arguments given, the script will attempt to read a JSON file hosted by the
# ESOS project and display a list of RAID tools and a download location for
# each. The user is instructed to download the packages needed, then copy them
# up to the ESOS host (eg, via SCP) and run this script with the path to the
# package as the argument; this will extract and install the RAID tool.

import urllib.error
import urllib.request
import glob
import json
import sys
import subprocess
import tempfile
import shutil
import os


# Script settings
TOOL_JSON_URL = 'http://download.esos-project.com/raid_cli_tools.json'
FETCH_TIMEOUT = 30
BIN_DIR = '/opt/sbin/'
LIB_DIR = '/opt/lib/'


class InstallError(Exception):
    pass


def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True)


def match_one(pattern, cwd):
    matches = sorted(glob.glob(os.path.join(cwd, pattern)))
    if len(matches) != 1:
        raise InstallError('expected exactly one match for "%s", found %d' %
                           (pattern, len(matches)))
    return matches[0]


def match_all(pattern, cwd):
    matches = sorted(glob.glob(os.path.join(cwd, pattern)))
    if not matches:
        raise InstallError('no files match "%s"' % pattern)
    return matches


def extract_rpm(rpm_file, cwd):
    # Equivalent of: rpm2cpio <rpm_file> | cpio -idmv
    rpm2cpio = subprocess.Popen(['rpm2cpio', rpm_file], cwd=cwd,
                                stdout=subprocess.PIPE)
    try:
        cpio = subprocess.run(['cpio', '-idmv'], cwd=cwd,
                              stdin=rpm2cpio.stdout)
    finally:
        rpm2cpio.stdout.close()
        rpm2cpio_exit = rpm2cpio.wait()
    if rpm2cpio_exit != 0:
        raise subprocess.CalledProcessError(rpm2cpio_exit, 'rpm2cpio')
    if cpio.returncode != 0:
        raise subprocess.CalledProcessError(cpio.returncode, 'cpio')


def install_bin(src, dst, cwd):
    run(['install', '-m', '0755', src, dst], cwd)


def copy_libs(pattern, cwd):
    run(['cp'] + match_all(pattern, cwd) + [LIB_DIR], cwd)


def install_storcli(pkg_file, tmp):
    run(['unzip', '-o', pkg_file], tmp)
    run(['unzip', '-o',
         'versionChangeSet/univ_viva_cli_rel/storcli_all_os.zip'], tmp)
    extract_rpm(match_one('storcli_all_os/Linux/storcli-*.rpm', tmp), tmp)
    install_bin('opt/MegaRAID/storcli/storcli64', BIN_DIR, tmp)
    copy_libs('opt/MegaRAID/storcli/libstorelibir*', tmp)


def install_perccli(pkg_file, tmp):
    run(['tar', 'xvfz', pkg_file], tmp)
    extract_rpm(match_one('perccli-*.noarch.rpm', tmp), tmp)
    install_bin('opt/MegaRAID/perccli/perccli64', BIN_DIR, tmp)
    copy_libs('opt/MegaRAID/perccli/libstorelibir*', tmp)


def install_arcconf(pkg_file, tmp):
    run(['unzip', '-o', pkg_file], tmp)
    install_bin('linux_x64/cmdline/arcconf', BIN_DIR, tmp)


def install_hpacucli(pkg_file, tmp):
    extract_rpm(pkg_file, tmp)
    install_bin('opt/compaq/hpacucli/bld/.hpacucli', BIN_DIR + 'hpacucli',
                tmp)
    copy_libs('opt/compaq/hpacucli/bld/*.so', tmp)


def install_hpssacli(pkg_file, tmp):
    extract_rpm(pkg_file, tmp)
    install_bin('opt/hp/hpssacli/bld/hpssacli', BIN_DIR, tmp)


def install_linuxcli(pkg_file, tmp):
    run(['unzip', '-o', pkg_file], tmp)
    install_bin(match_one('linuxcli_*/x86_64/cli64', tmp), BIN_DIR, tmp)


def install_3dm2_cli(pkg_file, tmp):
    run(['unzip', '-o', pkg_file], tmp)
    run(['tar', 'xvfz', 'tdmCliLnx.tgz'], tmp)
    install_bin('tw_cli.x86_64', BIN_DIR, tmp)


def install_megacli(pkg_file, tmp):
    run(['unzip', '-o', pkg_file], tmp)
    extract_rpm(match_one('Linux/MegaCli-*.rpm', tmp), tmp)
    install_bin('opt/MegaRAID/MegaCli/MegaCli64', BIN_DIR, tmp)


# Checked in order against the package file name
RECIPES = [
    ('StorCLI', install_storcli),
    ('perccli', install_perccli),
    ('arcconf', install_arcconf),
    ('hpacucli', install_hpacucli),
    ('hpssacli', install_hpssacli),
    ('linuxcli', install_linuxcli),
    ('3DM2_CLI', install_3dm2_cli),
    ('MegaCLI', install_megacli),
]


def install_pkg(pkg_file):
    print('Attempting to install "%s" on this host...\n' % pkg_file,
          flush=True)
    pkg_name = os.path.basename(pkg_file)
    recipe = next((func for key, func in RECIPES if key in pkg_name), None)
    if recipe is None:
        print('We don\'t know how to extract and install this file!')
        return 1
    if not os.path.isfile(pkg_file):
        print('The package file "%s" does not exist!' % pkg_file)
        return 1
    temp_dir = tempfile.mkdtemp()
    try:
        recipe(pkg_file, temp_dir)
    except (subprocess.CalledProcessError, InstallError, OSError) as err:
        print('\nAn error occurred while installing this package! (%s)' % err)
        return 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    print('\nThe RAID CLI tool was installed successfully.')
    return 0


def list_tools():
    # No package file was given, so print available options and usage
    try:
        print('Fetching JSON file with RAID tool information...\n')
        with urllib.request.urlopen(TOOL_JSON_URL,
                                    timeout=FETCH_TIMEOUT) as url:
            data = json.loads(url.read().decode())
        for each in data:
            print(each['desc'])
            print('File Name: %s' % each['file'])
            print('Download URL: %s\n' % each['url'])
    except (urllib.error.URLError, OSError, ValueError, KeyError,
            TypeError) as err:
        print('An error occurred while fetching the JSON file! (%s)' % err)
        print('For a list of available RAID CLI tools, visit this URL: %s' %
              TOOL_JSON_URL)
        return 0
    print('Fetch the desired RAID CLI tools and upload the files to')
    print('this ESOS machine, then install each using this script')
    print('with the path to the package/archive as the argument.\n')
    print('Sample install syntax: %s /tmp/8-07-14_MegaCLI.zip' % __file__)
    return 0


if __name__ == '__main__':
    if len(sys.argv) == 2:
        sys.exit(install_pkg(os.path.abspath(sys.argv[1])))
    sys.exit(list_tools())
