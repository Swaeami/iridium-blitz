#!/usr/bin/env python3

import sys
import json
import argparse
from pathlib import Path
import re
from ipaddress import ip_address
import subprocess
from datetime import datetime, timedelta
from init_paths import *
from paths import NODES_JSON_PATH


def is_valid_ip_or_domain(value: str) -> bool:
    if not value or not value.strip():
        return False
    value = value.strip()
    try:
        ip_address(value)
        return True
    except ValueError:
        domain_regex = re.compile(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$',
            re.IGNORECASE
        )
        return re.match(domain_regex, value) is not None

def is_valid_sni(value: str) -> bool:
    if not value or not value.strip():
        return False
    value = value.strip()
    try:
        ip_address(value)
        return False
    except ValueError:
        if "https://" in value or "http://" in value or "//" in value:
            return False
        domain_regex = re.compile(
            r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$',
            re.IGNORECASE
        )
        return re.match(domain_regex, value) is not None

def is_valid_sha256_pin(value: str) -> bool:
    if not value or not value.strip():
        return False
    value = value.strip().upper()
    pin_regex = re.compile(r'^([0-9A-F]{2}:){31}[0-9A-F]{2}$')
    return re.match(pin_regex, value) is not None

def is_valid_port(port: int) -> bool:
    return 1 <= port <= 65535

def read_nodes():
    if not NODES_JSON_PATH.exists():
        return []
    try:
        with NODES_JSON_PATH.open("r") as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError, OSError) as e:
        sys.exit(f"Error reading or parsing {NODES_JSON_PATH}: {e}")

def write_nodes(nodes):
    try:
        NODES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with NODES_JSON_PATH.open("w") as f:
            json.dump(nodes, f, indent=4)
    except (IOError, OSError) as e:
        sys.exit(f"Error writing to {NODES_JSON_PATH}: {e}")

def add_node(name: str, ip: str, sni: str | None = None, pinSHA256: str | None = None, port: int | None = None, obfs: str | None = None, insecure: bool = False):
    if not is_valid_ip_or_domain(ip):
        print(f"Error: '{ip}' is not a valid IP address or domain name.", file=sys.stderr)
        sys.exit(1)

    if sni and not is_valid_sni(sni):
        print(f"Error: '{sni}' is not a valid domain name for SNI.", file=sys.stderr)
        sys.exit(1)

    if pinSHA256 and not is_valid_sha256_pin(pinSHA256):
        print(f"Error: '{pinSHA256}' is not a valid SHA256 pin format.", file=sys.stderr)
        sys.exit(1)

    if port and not is_valid_port(port):
        print(f"Error: Port '{port}' must be between 1 and 65535.", file=sys.stderr)
        sys.exit(1)

    nodes = read_nodes()
    if any(node['name'] == name for node in nodes):
        print(f"Error: A node with the name '{name}' already exists.", file=sys.stderr)
        sys.exit(1)
    if any(node['ip'] == ip for node in nodes):
        print(f"Error: A node with the IP/domain '{ip}' already exists.", file=sys.stderr)
        sys.exit(1)
    
    new_node = {"name": name, "ip": ip}
    if sni:
        new_node["sni"] = sni.strip()
    if pinSHA256:
        new_node["pinSHA256"] = pinSHA256.strip().upper()
    if port:
        new_node["port"] = port
    if obfs:
        new_node["obfs"] = obfs.strip()
    if insecure:
        new_node["insecure"] = insecure

    nodes.append(new_node)
    write_nodes(nodes)
    print(f"Successfully added node '{name}'.")

def delete_node(name: str):
    nodes = read_nodes()
    original_count = len(nodes)
    nodes = [node for node in nodes if node['name'] != name]
    
    if len(nodes) == original_count:
        print(f"Error: No node with the name '{name}' found.", file=sys.stderr)
        sys.exit(1)

    write_nodes(nodes)
    print(f"Successfully deleted node '{name}'.")


def edit_node(name: str, new_name: str | None = None, ip: str | None = None, sni: str | None = None, 
              pinSHA256: str | None = None, port: int | None = None, obfs: str | None = None, 
              insecure: bool | None = None):
    """Edit an existing node's configuration."""
    
    # Validate inputs if provided
    if ip and not is_valid_ip_or_domain(ip):
        print(f"Error: '{ip}' is not a valid IP address or domain name.", file=sys.stderr)
        sys.exit(1)

    if sni and not is_valid_sni(sni):
        print(f"Error: '{sni}' is not a valid domain name for SNI.", file=sys.stderr)
        sys.exit(1)

    if pinSHA256 and not is_valid_sha256_pin(pinSHA256):
        print(f"Error: '{pinSHA256}' is not a valid SHA256 pin format.", file=sys.stderr)
        sys.exit(1)

    if port and not is_valid_port(port):
        print(f"Error: Port '{port}' must be between 1 and 65535.", file=sys.stderr)
        sys.exit(1)

    nodes = read_nodes()
    
    # Find the node to edit
    node_index = None
    for i, node in enumerate(nodes):
        if node['name'] == name:
            node_index = i
            break
    
    if node_index is None:
        print(f"Error: No node with the name '{name}' found.", file=sys.stderr)
        sys.exit(1)
    
    # Check if new_name conflicts with another existing node
    if new_name and new_name != name:
        if any(node['name'] == new_name for node in nodes):
            print(f"Error: A node with the name '{new_name}' already exists.", file=sys.stderr)
            sys.exit(1)
    
    # Check if new IP conflicts with another existing node
    if ip:
        for i, node in enumerate(nodes):
            if i != node_index and node['ip'] == ip:
                print(f"Error: A node with the IP/domain '{ip}' already exists.", file=sys.stderr)
                sys.exit(1)
    
    # Update node fields
    if new_name:
        nodes[node_index]['name'] = new_name
    if ip:
        nodes[node_index]['ip'] = ip
    if sni is not None:
        if sni:
            nodes[node_index]['sni'] = sni.strip()
        elif 'sni' in nodes[node_index]:
            del nodes[node_index]['sni']
    if pinSHA256 is not None:
        if pinSHA256:
            nodes[node_index]['pinSHA256'] = pinSHA256.strip().upper()
        elif 'pinSHA256' in nodes[node_index]:
            del nodes[node_index]['pinSHA256']
    if port is not None:
        if port:
            nodes[node_index]['port'] = port
        elif 'port' in nodes[node_index]:
            del nodes[node_index]['port']
    if obfs is not None:
        if obfs:
            nodes[node_index]['obfs'] = obfs.strip()
        elif 'obfs' in nodes[node_index]:
            del nodes[node_index]['obfs']
    if insecure is not None:
        nodes[node_index]['insecure'] = insecure

    write_nodes(nodes)
    display_name = new_name if new_name else name
    print(f"Successfully updated node '{display_name}'.")

def list_nodes():
    nodes = read_nodes()
    if not nodes:
        print("No nodes configured.")
        return
        
    print(f"{'Name':<15} {'IP / Domain':<25} {'Port':<8} {'SNI':<20} {'Insecure':<10} {'OBFS':<20} {'Pin SHA256'}")
    print(f"{'-'*15} {'-'*25} {'-'*8} {'-'*20} {'-'*10} {'-'*20} {'-'*30}")
    for node in sorted(nodes, key=lambda x: x['name']):
        name = node['name']
        ip = node['ip']
        port = node.get('port', 'N/A')
        sni = node.get('sni', 'N/A')
        insecure = str(node.get('insecure', 'False'))
        obfs = node.get('obfs', 'N/A')
        pin = node.get('pinSHA256', 'N/A')
        print(f"{name:<15} {ip:<25} {str(port):<8} {sni:<20} {insecure:<10} {obfs:<20} {pin}")

def generate_cert():
    try:
        script_dir = Path(__file__).parent.resolve()
        key_filepath = script_dir / "iridium.key"
        cert_filepath = script_dir / "iridium.crt"
        
        if cert_filepath.exists():
            try:
                check_cmd = ['openssl', 'x509', '-in', str(cert_filepath), '-noout', '-enddate']
                result = subprocess.run(check_cmd, capture_output=True, text=True, check=True)
                
                end_date_str = result.stdout.strip().split('=')[1]
                end_date = datetime.strptime(end_date_str, '%b %d %H:%M:%S %Y %Z')
                
                if end_date > datetime.now() + timedelta(days=30):
                    print("Existing certificate is valid for more than 30 days.")
                    print("\n")
                    print(cert_filepath.read_text().strip())
                    return
                else:
                    print("Existing certificate is expiring in less than 30 days. Generating a new one.")
            except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError) as e:
                print(f"Could not validate existing certificate: {e}. Generating a new one.")

        print("Generating new certificate and key...")
        openssl_command = [
            'openssl', 'req', '-x509',
            '-newkey', 'ec',
            '-pkeyopt', 'ec_paramgen_curve:prime256v1',
            '-keyout', str(key_filepath),
            '-out', str(cert_filepath),
            '-sha256', '-days', '3650', '-nodes',
            '-subj', '/CN=Iridium'
        ]
        
        result = subprocess.run(openssl_command, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            sys.exit(f"Error generating certificate with OpenSSL:\n{result.stderr}")
        
        cert_content = cert_filepath.read_text()
        
        print("Successfully generated certificate and key:")
        print("\n")
        print(cert_content.strip())

    except FileNotFoundError:
        sys.exit("Error: 'openssl' command not found. Please ensure OpenSSL is installed and in your PATH.")
    except Exception as e:
        sys.exit(f"An unexpected error occurred: {e}")

def main():
    parser = argparse.ArgumentParser(description="Manage external node configurations.")
    subparsers = parser.add_subparsers(dest='command', required=True)

    add_parser = subparsers.add_parser('add', help='Add a new node.')
    add_parser.add_argument('--name', type=str, required=True, help='The unique name of the node.')
    add_parser.add_argument('--ip', type=str, required=True, help='The IP address or domain of the node.')
    add_parser.add_argument('--port', type=int, help='Optional: The port of the node.')
    add_parser.add_argument('--sni', type=str, help='Optional: The Server Name Indication.')
    add_parser.add_argument('--pinSHA256', type=str, help='Optional: The public key SHA256 pin.')
    add_parser.add_argument('--obfs', type=str, help='Optional: The obfuscation key.')
    add_parser.add_argument('--insecure', action='store_true', help='Optional: Skip certificate verification.')

    edit_parser = subparsers.add_parser('edit', help='Edit an existing node.')
    edit_parser.add_argument('--name', type=str, required=True, help='The name of the node to edit.')
    edit_parser.add_argument('--new-name', type=str, help='Optional: New name for the node.')
    edit_parser.add_argument('--ip', type=str, help='Optional: New IP address or domain.')
    edit_parser.add_argument('--port', type=int, help='Optional: New port.')
    edit_parser.add_argument('--sni', type=str, help='Optional: New SNI (use empty string to remove).')
    edit_parser.add_argument('--pinSHA256', type=str, help='Optional: New SHA256 pin (use empty string to remove).')
    edit_parser.add_argument('--obfs', type=str, help='Optional: New obfuscation key (use empty string to remove).')
    edit_parser.add_argument('--insecure', type=str, choices=['true', 'false'], help='Optional: Skip certificate verification.')

    delete_parser = subparsers.add_parser('delete', help='Delete a node by name.')
    delete_parser.add_argument('--name', type=str, required=True, help='The name of the node to delete.')

    subparsers.add_parser('list', help='List all configured nodes.')
    
    subparsers.add_parser('generate-cert', help="Generate iridium.crt and iridium.key.")
    
    args = parser.parse_args()

    if args.command == 'add':
        add_node(args.name, args.ip, args.sni, args.pinSHA256, args.port, args.obfs, args.insecure)
    elif args.command == 'edit':
        insecure_val = None
        if args.insecure is not None:
            insecure_val = args.insecure.lower() == 'true'
        edit_node(args.name, args.new_name, args.ip, args.sni, args.pinSHA256, args.port, args.obfs, insecure_val)
    elif args.command == 'delete':
        delete_node(args.name)
    elif args.command == 'list':
        list_nodes()
    elif args.command == 'generate-cert':
        generate_cert()

if __name__ == "__main__":
    main()