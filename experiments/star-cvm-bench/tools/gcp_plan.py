#!/usr/bin/env python3
"""Matched N2D/SNP resource draft. Requires an agreed project, lifetime and budget.
Preflight checks an image's features; it does not validate pricing, capacity, or
all instance-creation combinations. Mutations default to a printed plan.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys


def query(args):
    return json.loads(subprocess.check_output(['gcloud', *args, '--format=json'], text=True))


def resources(project, zone, names):
    found = {}
    for kind in ('instances', 'disks'):
        rows = query(['compute', kind, 'list', '--project=' + project])
        found[kind] = [r for r in rows if r['name'] in names and r['zone'].rsplit('/', 1)[-1] == zone]
    return found


def image_check(image):
    if image:
        args = ['describe', image]
    else:
        args = ['describe-from-family', 'ubuntu-2404-lts-amd64']
    data = query(['compute', 'images', *args, '--project=ubuntu-os-cloud'])
    if 'SEV_SNP_CAPABLE' not in {f['type'] for f in data.get('guestOsFeatures', [])}:
        raise ValueError('Image does not advertise SEV_SNP_CAPABLE')
    print(json.dumps({k: data.get(k) for k in ('name', 'id', 'creationTimestamp', 'guestOsFeatures')}))
    return data['name']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['preflight', 'create', 'cleanup', 'verify-clean'])
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    project = os.environ.get('PROJECT', '')
    if not project or project.startswith('-'):
        raise ValueError('Set PROJECT to the agreed experiment project')
    zone = os.environ.get('ZONE', 'us-central1-a')
    machine = 'n2d-highmem-8'
    if a.action == 'preflight':
        image_check(os.environ.get('IMAGE'))
        print(json.dumps(query(['compute', 'machine-types', 'describe', machine, '--zone=' + zone, '--project=' + project])))
        return 0
    run_id = os.environ.get('RUN_ID', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,29}', run_id):
        raise ValueError('Set a stable RUN_ID (1-30 lowercase letters, digits or hyphens); reuse it for cleanup')
    names = ['bio-star-vm-' + run_id, 'bio-star-snp-' + run_id]
    common = ['--project=' + project, '--zone=' + zone]
    if a.action == 'verify-clean':
        found = resources(project, zone, names)
        print(json.dumps({k: [r['name'] for r in v] for k, v in found.items()}))
        return 1 if any(found.values()) else 0
    if a.action == 'cleanup':
        # Check BOTH instances before any deletion. A coincident name is not ownership.
        found = resources(project, zone, names) if a.execute else None
        if found:
            for r in found['instances']:
                if r.get('labels', {}).get('experiment') != 'bio-star' or r.get('labels', {}).get('run') != run_id:
                    raise ValueError('Refuse deletion: ownership labels differ for ' + r['name'])
        delete_names = [r['name'] for r in found['instances']] if found is not None else names
        for name in delete_names:
            cmd = ['gcloud', 'compute', 'instances', 'delete', name, *common, '--quiet']
            print(shlex.join(cmd), flush=True)
            if a.execute:
                subprocess.run(cmd, check=True)
        if a.execute:
            remaining = resources(project, zone, names)
            if any(remaining.values()):
                print('Resources remain; inspect them before cleanup. No independent disk deletion was attempted.', file=sys.stderr)
                return 1
        return 0
    image = os.environ.get('IMAGE', '')
    if not re.fullmatch(r'[a-z][a-z0-9-]+', image):
        raise ValueError('Set IMAGE to an exact image name confirmed by preflight')
    hours = int(os.environ.get('MAX_HOURS', '6'))
    if not 1 <= hours <= 6:
        raise ValueError('MAX_HOURS must be 1..6 for this draft')
    if a.execute:
        image_check(image)
        found = resources(project, zone, names)
        if any(found.values()):
            raise ValueError('Refuse creation: one or more planned instance/disk names already exist')
    for name in names:
        cmd = ['gcloud', 'compute', 'instances', 'create', name, *common,
               '--machine-type=' + machine, '--min-cpu-platform=AMD Milan',
               '--image-project=ubuntu-os-cloud', '--image=' + image,
               '--boot-disk-size=300GB', '--boot-disk-type=pd-ssd', '--boot-disk-auto-delete',
               '--boot-disk-interface=NVME', '--maintenance-policy=TERMINATE',
               '--shielded-secure-boot', '--shielded-vtpm', '--max-run-duration=' + str(hours) + 'h',
               '--instance-termination-action=DELETE', '--labels=experiment=bio-star,run=' + run_id,
               '--metadata=enable-oslogin=TRUE']
        if name == names[1]:
            cmd.append('--confidential-compute-type=SEV_SNP')
        print(shlex.join(cmd), flush=True)
        if a.execute:
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                print('Creation failed; earlier resources may remain. Inspect and use cleanup with the same PROJECT, ZONE and RUN_ID.', file=sys.stderr)
                raise
    if a.execute:
        for name in names:
            data = query(['compute', 'instances', 'describe', name, *common])
            print(json.dumps({k: data.get(k) for k in ('name', 'cpuPlatform', 'disks', 'confidentialInstanceConfig', 'scheduling')}))
    print('Before measuring, verify actual CPU, disk interface, kernel and confidential mode on both guests. Parity is not automatic.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
