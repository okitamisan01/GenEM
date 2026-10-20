#!/usr/bin/env python3
"""Write ignored local deployment settings; never connects or enables actuation."""
import argparse
import ipaddress
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import yaml


def prepare(root, interface, robot_ip, domain, working_dds=None):
    if not re.fullmatch(r'[a-zA-Z0-9_.:-]+', interface):
        raise ValueError('Invalid interface name')
    robot_ip = str(ipaddress.IPv4Address(robot_ip))
    if type(domain) is not int or not 0 <= domain <= 232:
        raise ValueError('ROS domain must be an integer from 0 to 232')
    outputs = [root / 'config/cyclonedds.local.xml', root / 'config/hsr104.local.yaml',
               root / 'docker/hsr104.local.env']
    if any(path.exists() for path in outputs):
        raise ValueError('Local deployment file already exists; preserve/edit it manually instead of overwriting')
    # Read and validate everything before writing any local file.
    if working_dds:
        dds = Path(working_dds).read_text(encoding='utf-8')
        ET.fromstring(dds)
    else:
        document = ET.Element('CycloneDDS', xmlns='https://cdds.io/config')
        group = ET.SubElement(document, 'Domain')
        general = ET.SubElement(group, 'General')
        interfaces = ET.SubElement(general, 'Interfaces')
        ET.SubElement(interfaces, 'NetworkInterface', name=interface)
        ET.SubElement(general, 'AllowMulticast').text = 'true'
        peers = ET.SubElement(ET.SubElement(group, 'Discovery'), 'Peers')
        ET.SubElement(peers, 'Peer', Address=robot_ip)
        ET.indent(document)
        dds = ET.tostring(document, encoding='unicode') + '\n'
    profile = yaml.safe_load((root / 'config/hsr_hardware.example.yaml').read_text())
    profile['verified'] = False
    profile['verification_note'] = ''
    env = (f'ROS_DOMAIN_ID={domain}\nGENEM_HSR_DOMAIN_ID={domain}\nRMW_IMPLEMENTATION=rmw_cyclonedds_cpp\n'
           'ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET\n'
           'CYCLONEDDS_URI=file:///root/genem_config/cyclonedds.local.xml\n')
    values = [dds, yaml.safe_dump(profile, sort_keys=False), env]
    for path, value in zip(outputs, values):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='utf-8') as stream:
            stream.write(value)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface', required=True)
    parser.add_argument('--robot-ip', required=True)
    parser.add_argument('--domain', type=int, required=True)
    parser.add_argument('--working-dds', type=Path,
                        help='Copy a known-working Cyclone DDS XML instead of generating a minimal one')
    args = parser.parse_args()
    try:
        paths = prepare(Path(__file__).resolve().parents[1], args.interface, args.robot_ip,
                        args.domain, args.working_dds)
    except (OSError, ValueError, ET.ParseError, yaml.YAMLError) as exc:
        parser.exit(2, f'Preparation failed: {exc}\n')
    for path in paths:
        print('Created local file:', path.name)
    print('No network access or motion. Hardware remains verified=false.')


if __name__ == '__main__':
    main()
