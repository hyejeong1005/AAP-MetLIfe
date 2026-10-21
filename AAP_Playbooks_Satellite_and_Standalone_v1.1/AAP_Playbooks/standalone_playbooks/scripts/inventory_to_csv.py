#!/usr/bin/env python3
"""Export direct SSH inventory and collection results; standard library only."""
import argparse
import csv
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid


HEADERS = {
    'server_inventory.csv': ['inventory_hostname', 'connection_address', 'hostname', 'hostname_source', 'os', 'os_source', 'live_os', 'architecture', 'architecture_source', 'cpu_vcpus', 'cpu_source', 'memory_mib', 'memory_source', 'kernel', 'default_ipv4', 'all_ipv4', 'uptime_seconds', 'live_collected_at_utc', 'report_created_at_utc'],
    'disk_inventory.csv': ['inventory_hostname', 'device', 'mount', 'fstype', 'total_gib', 'used_gib', 'available_gib', 'used_percent', 'options'],
    'network_inventory.csv': ['inventory_hostname', 'interface', 'active', 'mac', 'ipv4', 'netmask', 'ipv6', 'mtu', 'type', 'speed_mbps'],
    'service_inventory.csv': ['inventory_hostname', 'name', 'state', 'enabled_status', 'source'],
    'collection_result.csv': ['inventory_hostname', 'overall_status', 'ssh_facts_status', 'services_status', 'report_created_at_utc', 'errors'],
}


def lookup(obj, path):
    # Exact flat fact keys take priority; paths otherwise use dot notation.
    if not isinstance(obj, dict) or not path:
        return None
    if path in obj:
        return obj[path]
    for part in path.split('.'):
        if not isinstance(obj, dict) or part not in obj:
            return None
        obj = obj[part]
    return obj


def scalar(value):
    if isinstance(value, dict):
        return value.get('name', value.get('title', value.get('label')))
    if isinstance(value, (list, tuple)):
        return None
    return value


def first(obj, *paths):
    for path in paths:
        value = scalar(lookup(obj, path))
        if value is not None and value != '':
            return value
    return None


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return int(result) if result.is_integer() else result
    except (TypeError, ValueError):
        return None


def safe(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def status(result, payload):
    if result.get('unreachable'):
        return 'UNREACHABLE'
    if result.get('failed'):
        return 'FAILED'
    if result.get('skipped') or payload not in result:
        return 'NOT_COLLECTED'
    return 'SUCCESS'


def export(records, root):
    os.umask(0o077)
    root = Path(root)
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.isoformat(timespec='seconds')
    final = root / ('Direct_Inventory_' + now.strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:12])
    staging = Path(tempfile.mkdtemp(prefix='.csv-build-', dir=root))
    counts = {'total_hosts': len(records), 'success_hosts': 0, 'partial_hosts': 0, 'failed_hosts': 0, 'error_hosts': 0}
    files, writers = {}, {}
    try:
        for name, headers in HEADERS.items():
            handle = (staging / name).open('w', encoding='utf-8-sig', newline='')
            files[name] = handle
            writers[name] = csv.writer(handle)
            writers[name].writerow(headers)
        def row(name, values):
            writers[name].writerow([safe(value) for value in values])
        for record in records:
            name = record['inventory_hostname']
            sat, live, service = [record.get(key, {}) for key in ('satellite', 'setup', 'services')]
            a, b, c = status(sat, 'host'), status(live, 'ansible_facts'), status(service, 'ansible_facts')
            overall = 'SUCCESS' if b == c == 'SUCCESS' else ('PARTIAL' if b == 'SUCCESS' else 'FAILED')
            counts[{'SUCCESS': 'success_hosts', 'PARTIAL': 'partial_hosts', 'FAILED': 'failed_hosts'}[overall]] += 1
            errors = []
            for label, result, state in [('SSH Facts', live, b), ('Services', service, c)]:
                if state != 'SUCCESS':
                    # Satellite credentials may appear in module invocation/error details.
                    detail = 'Query failed; check Satellite URL, FQDN, permissions, CA and network' if label == 'Satellite' else str(result.get('msg', state))
                    errors.append(label + ': ' + detail)
            row('collection_result.csv', [name, overall, b, c, stamp, '\n'.join(errors)])
            host = sat.get('host', {}) if a == 'SUCCESS' else {}
            facts = live.get('ansible_facts', {}) if b == 'SUCCESS' else {}
            field_map = record.get('field_map', {})
            def fact(key, default=None):
                return facts.get('ansible_' + key, facts.get(key, default))
            def mapped(key, fallback=None):
                value = scalar(lookup(host, field_map.get(key)))
                return value if value is not None and value != '' else fallback
            def choose(satellite, fresh):
                if satellite is not None and satellite != '':
                    return satellite, 'Satellite'
                if fresh is not None and fresh != '':
                    return fresh, 'SSH'
                return None, 'UNAVAILABLE'
            hostname, hs = choose(first(host, 'name'), fact('fqdn') or fact('hostname'))
            live_os = ' '.join(str(x) for x in [fact('distribution'), fact('distribution_version')] if x)
            os_name, os_source = choose(mapped('os', first(host, 'operatingsystem_name', 'operatingsystem.title', 'operatingsystem.name')), live_os)
            architecture, arch_source = choose(mapped('architecture', first(host, 'architecture.name', 'architecture_name')), fact('architecture'))
            cpu, cpu_source = choose(number(mapped('cpu_vcpus')), number(fact('processor_vcpus')))
            memory, memory_source = choose(number(mapped('memory_mib')), number(fact('memtotal_mb')))
            row('server_inventory.csv', [name, record.get('connection_address'), hostname, hs, os_name, os_source, live_os, architecture, arch_source, cpu, cpu_source, memory, memory_source, fact('kernel'), fact('default_ipv4', {}).get('address'), ', '.join(fact('all_ipv4_addresses', [])), fact('uptime_seconds'), fact('date_time', {}).get('iso8601'), stamp])
            for mount in fact('mounts', []):
                total, avail = number(mount.get('size_total')), number(mount.get('size_available'))
                valid = total is not None and avail is not None
                used = total - avail if valid else None
                gib = lambda v: round(v / 1024 ** 3, 2) if v is not None else None
                row('disk_inventory.csv', [name, mount.get('device'), mount.get('mount'), mount.get('fstype'), gib(total), gib(used), gib(avail), round(used / total * 100, 2) if valid and total > 0 else None, mount.get('options')])
            for interface in sorted(fact('interfaces', [])):
                nic = fact(interface, {})
                if not isinstance(nic, dict):
                    continue
                ipv4 = [nic.get('ipv4', {})] + nic.get('ipv4_secondaries', [])
                ipv4 = [entry for entry in ipv4 if entry.get('address')]
                ipv6 = ', '.join(str(entry.get('address', '')) + '/' + str(entry.get('prefix', '')) for entry in nic.get('ipv6', []))
                row('network_inventory.csv', [name, interface, nic.get('active'), nic.get('macaddress'), ', '.join(entry['address'] for entry in ipv4), ', '.join(entry.get('netmask', '') for entry in ipv4), ipv6, nic.get('mtu'), nic.get('type'), nic.get('speed')])
            if c == 'SUCCESS':
                for service_name, item in sorted(service.get('ansible_facts', {}).get('services', {}).items()):
                    row('service_inventory.csv', [name, service_name, item.get('state'), item.get('status'), item.get('source')])
        for handle in files.values():
            handle.close()
        os.rename(staging, final)
    except BaseException:
        for handle in files.values():
            handle.close()
        shutil.rmtree(staging, ignore_errors=True)
        raise
    counts['error_hosts'] = counts['partial_hosts'] + counts['failed_hosts']
    counts['report_directory'] = str(final)
    counts['files'] = [str(final / name) for name in HEADERS]
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    records = json.loads(Path(args.input).read_text(encoding='utf-8'))
    if not isinstance(records, list):
        parser.error('Input must be an array')
    print(json.dumps(export(records, args.output_dir), ensure_ascii=False))


if __name__ == '__main__':
    main()
