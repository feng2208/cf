import os
import sys
import json
import urllib.request
import concurrent.futures
import subprocess

URL_PREFIX = os.environ.get('URL_PREFIX')
TARGET_URL = os.environ.get('TARGET_URL')

def test_ip_port(ip_port):
    """
    测试单个 IP:PORT 是否可用。
    """
    try:
        ip, port = ip_port.split(':')
    except ValueError:
        return False
    
    cmd = [
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
        "--connect-to", f"::{ip}:{port}",
        "--connect-timeout", "5",
        "-m", "10",
        TARGET_URL
    ]

    try:
        # 执行 curl 命令进行测试
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        http_code = result.stdout.strip()
        
        # 认为 200 或其他 2xx/3xx 状态码为成功
        if http_code.startswith('2') or http_code.startswith('3'):
            return True
    except Exception:
        pass
        
    return False

def process_file(filename):
    url = f"{URL_PREFIX}{filename}"
    print(f"[{filename}] Downloading {url}...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"[{filename}] Failed to download: {e}", file=sys.stderr)
        return

    if not isinstance(data, list):
        print(f"[{filename}] Error: Data is not a JSON list.", file=sys.stderr)
        return

    print(f"[{filename}] Start testing {len(data)} addresses...")
    successful_ips = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ip = {executor.submit(test_ip_port, ip_port): ip_port for ip_port in data}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip_port = future_to_ip[future]
            try:
                if future.result():
                    successful_ips.append(ip_port)
                    print(f"[SUCCESS] {ip_port}")
            except Exception as e:
                print(f"[ERROR] Testing {ip_port} threw an exception: {e}", file=sys.stderr)
                
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(successful_ips, f, indent=2)
        
    print(f"[{filename}] Finished. Saved {len(successful_ips)} working addresses.")

def main():
    if not URL_PREFIX:
        print("Error: URL_PREFIX environment variable is not set.", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.exists('filename.txt'):
        print("Error: filename.txt not found in current directory.", file=sys.stderr)
        sys.exit(1)
        
    with open('filename.txt', 'r', encoding='utf-8') as f:
        filenames = [line.strip() for line in f if line.strip()]
        
    if not filenames:
        print("Warning: filename.txt is empty.")
        sys.exit(0)
        
    for filename in filenames:
        process_file(filename)

if __name__ == "__main__":
    main()
