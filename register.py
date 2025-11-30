#!/usr/bin/env python3
"""
Standalone Reddit Account Registration Script for VPS
Supports multiple concurrent instances with unique gluetun containers
Usage: python register.py --instance 1 (or 2, 3, etc.)
"""

import sys
import asyncio
import socket
import time
import json
import random
import string
import re
import requests
from requests import get
import os
import argparse
import logging
from pathlib import Path
import warnings

# Try to import zendriver (local or pip)
try:
    import zendriver
except ImportError:
    print("[ERROR] zendriver not found. Install via: pip install zendriver")
    sys.exit(1)

from bs4 import BeautifulSoup

# Try to import docker
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    print("[WARNING] Docker not available - install via: pip install docker")

# Suppress BeautifulSoup warnings
try:
    from bs4 import MarkupResemblesLocatorWarning
    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
except ImportError:
    pass

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}
NOT_FOUND_PATTERN = re.compile(r"sorry,\s*nobody\s+on\s+reddit\s+goes\s+by\s+that\s+name", re.I)
BANNED_PATTERN = re.compile(r"this\s+account\s+has\s+been\s+banned", re.I)
SUSPENDED_PATTERN = re.compile(r"this\s+account\s+has\s+been\s+suspended", re.I)

# Global instance ID (set via CLI)
INSTANCE_ID = 1
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Setup logging
def setup_logging():
    """Setup logging with instance-specific log file"""
    logs_dir = LOGS_DIR
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"register_instance_{INSTANCE_ID}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized for instance {INSTANCE_ID}")
    return logger

logger = None

def log_info(msg):
    if logger:
        logger.info(msg)
    else:
        print(f"[INFO] {msg}")

def log_error(msg):
    if logger:
        logger.error(msg)
    else:
        print(f"[ERROR] {msg}")

def log_debug(msg):
    if logger:
        logger.debug(msg)
    else:
        print(f"[DEBUG] {msg}")

def get_instance_container_name():
    """Get unique container name for this instance"""
    return f"gluetun_register_{INSTANCE_ID}"

def get_instance_base_port():
    """Get base port for this instance (8888 for instance 1, 8988 for instance 2, etc.)"""
    return 8888 + (INSTANCE_ID - 1) * 100

def load_config():
    """Load configuration from config.json"""
    if not CONFIG_FILE.exists():
        log_error(f"Config file not found: {CONFIG_FILE}")
        log_error("Create config.json with gluetun credentials")
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        log_info(f"✓ Loaded config from {CONFIG_FILE}")
        return config
    except Exception as e:
        log_error(f"Failed to load config: {e}")
        return None

def find_chromium_executable():
    """Find Chromium executable"""
    import glob
    import subprocess
    
    playwright_paths = [
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        "/home/*/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    ]
    
    for pattern in playwright_paths:
        matches = glob.glob(pattern)
        if matches and os.path.isfile(matches[0]):
            log_debug(f"Found Chromium at: {matches[0]}")
            return matches[0]
    
    for cmd in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        try:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            if result.returncode == 0:
                exe_path = result.stdout.strip()
                log_debug(f"Found {cmd} at: {exe_path}")
                return exe_path
        except Exception:
            pass
    
    log_debug("No Chromium executable found, Zendriver will attempt auto-discovery")
    return None

def fetch_html(url: str, timeout: int = 10):
    """Fetch a URL"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        return resp.status_code, resp.text
    except requests.RequestException as e:
        log_debug(f"Request error for {url}: {e}")
        return None, None

def make_soup(html_content: str):
    """Create BeautifulSoup object"""
    return BeautifulSoup(html_content, "html.parser")

def detect_reddit_account_status(html_content: str) -> str:
    """Detect Reddit account status"""
    if not html_content:
        return "unknown"
    
    soup = make_soup(html_content)
    
    for tag_name in ("h1", "h2"):
        for tag in soup.find_all(tag_name):
            text = " ".join(tag.get_text(strip=True).split())
            if NOT_FOUND_PATTERN.search(text):
                return "not_found"
            if BANNED_PATTERN.search(text):
                return "banned"
            if SUSPENDED_PATTERN.search(text):
                return "suspended"
    
    body = soup.body.get_text(" ", strip=True) if soup.body else ""
    body = " ".join(body.split())
    if NOT_FOUND_PATTERN.search(body):
        return "not_found"
    if BANNED_PATTERN.search(body):
        return "banned"
    if SUSPENDED_PATTERN.search(body):
        return "suspended"
    
    return "active"

def get_docker_socket_path() -> str:
    """Find docker socket"""
    common_paths = [
        '/var/run/docker.sock',
        '/run/docker.sock',
        '/var/lib/docker/docker.sock',
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

def get_docker_client():
    """Get Docker client"""
    if not DOCKER_AVAILABLE:
        return None
    
    try:
        client = docker.from_env()
        return client
    except Exception:
        pass
    
    socket_path = get_docker_socket_path()
    if socket_path:
        try:
            client = docker.DockerClient(base_url=f'unix://{socket_path}')
            return client
        except Exception:
            pass
    
    return None

def test_gluetun_proxy(proxy_url: str, timeout: int = 10) -> bool:
    """Test if proxy is working"""
    try:
        response = requests.get(
            'http://httpbin.org/ip',
            proxies={'http': proxy_url, 'https': proxy_url},
            timeout=timeout
        )
        return response.status_code == 200
    except Exception as e:
        log_debug(f"Proxy test failed: {e}")
        return False

def find_available_port(start_port: int) -> int:
    """Find available port"""
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None

def restart_gluetun_container(container_name: str):
    """Restart gluetun container"""
    client = get_docker_client()
    if not client:
        log_debug(f"Docker not available, cannot restart {container_name}")
        return False
    
    try:
        container = client.containers.get(container_name)
        container.restart()
        time.sleep(10)
        log_info(f"✓ Container {container_name} restarted")
        return True
    except docker.errors.NotFound:
        log_debug(f"Container {container_name} not found")
        return False
    except Exception as e:
        log_debug(f"Failed to restart container {container_name}: {e}")
        return False

def restart_and_wait_for_proxy(container_name: str, gluetun_info: dict = None, max_restarts: int = 5, wait_between_restarts: int = 5, stable_checks: int = 3, check_interval: int = 3) -> bool:
    """Restart container and wait for stable proxy"""
    attempts = 0
    candidates = []
    
    if gluetun_info and gluetun_info.get('http_proxy'):
        candidates.append(gluetun_info['http_proxy'])
    
    candidates.append('http://127.0.0.1:8888')
    
    while True:
        attempts += 1
        if max_restarts and attempts > max_restarts:
            log_info(f"Reached max restart attempts ({max_restarts})")
            return False
        
        log_info(f"Restart attempt #{attempts} for {container_name}...")
        restarted = restart_gluetun_container(container_name)
        if not restarted:
            log_info(f"Restart failed, will retry after {wait_between_restarts}s")
            time.sleep(wait_between_restarts)
            continue
        
        time.sleep(wait_between_restarts)
        
        for proxy_url in candidates:
            good = 0
            total_wait = 0
            max_check_time = stable_checks * check_interval * 2
            
            while total_wait < max_check_time:
                ok = test_gluetun_proxy(proxy_url, timeout=10)
                if ok:
                    good += 1
                    log_debug(f"Proxy {proxy_url} OK ({good}/{stable_checks})")
                    if good >= stable_checks:
                        log_info(f"✓ Proxy {proxy_url} is stable")
                        return True
                else:
                    good = 0
                
                time.sleep(check_interval)
                total_wait += check_interval
        
        log_info(f"No proxy candidate stabilized, retrying...")
        time.sleep(1)

def get_ip_geolocation(gluetun_info: dict = None, container_name: str = None) -> tuple:
    """Get IP geolocation"""
    proxies = None
    if gluetun_info and gluetun_info.get('http_proxy'):
        proxies = {
            'http': gluetun_info['http_proxy'],
            'https': gluetun_info['http_proxy']
        }
    
    try:
        response = get('https://ipinfo.io/json', proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            loc = data.get('loc', '0,0').split(',')
            return {
                'ip': data.get('ip', ''),
                'city': data.get('city', ''),
                'region': data.get('region', ''),
                'country': data.get('country', 'US'),
                'latitude': float(loc[0]) if len(loc) > 0 and loc[0] else 0.0,
                'longitude': float(loc[1]) if len(loc) > 1 and loc[1] else 0.0,
                'timezone': data.get('timezone', 'America/New_York'),
                'org': data.get('org', ''),
            }, True
    except Exception as e:
        log_debug(f"ipinfo.io failed: {e}")
    
    try:
        response = get('http://ip-api.com/json/', proxies=proxies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'ip': data.get('query', ''),
                    'city': data.get('city', ''),
                    'region': data.get('regionName', ''),
                    'country': data.get('countryCode', 'US'),
                    'latitude': float(data.get('lat', 0)),
                    'longitude': float(data.get('lon', 0)),
                    'timezone': data.get('timezone', 'America/New_York'),
                    'org': data.get('org', ''),
                }, True
    except Exception as e:
        log_debug(f"ip-api.com failed: {e}")
    
    log_debug("Using default location settings")
    
    return {
        'ip': 'unknown',
        'city': '',
        'region': '',
        'country': 'US',
        'latitude': 0.0,
        'longitude': 0.0,
        'timezone': 'America/New_York',
        'org': '',
    }, False

def start_gluetun_container(container_name: str, config: dict, country: str = None, city: str = None) -> dict:
    """Start gluetun container for this instance"""
    if not DOCKER_AVAILABLE:
        log_error("Docker not available, cannot create gluetun container")
        return None
    
    try:
        client = docker.from_env()
    except Exception as e:
        log_error(f"Failed to connect to Docker: {e}")
        return None
    
    # Check if container already exists
    try:
        existing = client.containers.get(container_name)
        if existing.status == 'running':
            log_info(f"Container {container_name} already running, checking proxy...")
            
            max_restarts = 3
            for attempt in range(1, max_restarts + 1):
                try:
                    existing.reload()
                    time.sleep(3)
                except Exception as e:
                    log_debug(f"Failed to reload container: {e}")
                    break
                
                container_ports = existing.attrs.get('NetworkSettings', {}).get('Ports', {}) or {}
                http_port = None
                
                if '8888/tcp' in container_ports and container_ports['8888/tcp']:
                    http_port = container_ports['8888/tcp'][0].get('HostPort')
                
                if http_port:
                    test_proxy = f'http://127.0.0.1:{http_port}'
                    
                    try:
                        test_response = get(
                            'http://httpbin.org/ip',
                            proxies={'http': test_proxy, 'https': test_proxy},
                            timeout=5,
                        )
                        if test_response.status_code == 200:
                            log_info(f"✓ Reusing existing container {container_name}")
                            return {
                                'name': container_name,
                                'http_port': int(http_port),
                                'container': existing,
                                'http_proxy': test_proxy,
                                'proxy_ready': True,
                            }
                    except Exception as e:
                        log_debug(f"Proxy test failed on attempt {attempt}: {e}")
                
                if attempt < max_restarts:
                    log_info(f"Restarting container (attempt {attempt}/{max_restarts})")
                    try:
                        existing.restart(timeout=20)
                    except Exception as e:
                        log_error(f"Failed to restart: {e}")
                        break
                    time.sleep(5)
            
            log_info(f"Removing unhealthy container {container_name}...")
            try:
                existing.remove(force=True)
            except Exception as e:
                log_error(f"Failed to remove container: {e}")
                return None
        else:
            log_info(f"Container {container_name} not running, removing...")
            try:
                existing.remove(force=True)
            except Exception as e:
                log_error(f"Failed to remove stopped container: {e}")
                return None
    except docker.errors.NotFound:
        pass
    except Exception as e:
        log_debug(f"Error checking existing container: {e}")
    
    # Find available ports for this instance
    base_port = get_instance_base_port()
    http_port = find_available_port(base_port)
    
    if not http_port:
        log_error(f"Could not find available port starting from {base_port}")
        return None
    
    log_info(f"Using HTTP port: {http_port}")
    
    # Get VPN credentials from config
    gluetun_config = config.get('gluetun', {})
    openvpn_user = gluetun_config.get('openvpn_user')
    openvpn_password = gluetun_config.get('openvpn_password')
    vpn_provider = gluetun_config.get('vpn_service_provider', 'nordvpn')
    
    if not openvpn_user or not openvpn_password:
        log_error("OpenVPN credentials missing from config.json")
        return None
    
    # Build environment
    env = {
        'VPN_SERVICE_PROVIDER': vpn_provider,
        'HTTPPROXY': 'on',
        'SOCKS5PROXY': 'on',
        'OPENVPN_USER': openvpn_user,
        'OPENVPN_PASSWORD': openvpn_password,
    }
    
    if city:
        env['SERVER_CITY'] = city
        log_info(f"Setting city to: {city}")
    elif country:
        env['SERVER_COUNTRIES'] = country
        log_info(f"Setting country to: {country}")
    
    ports = {
        '8888/tcp': ('0.0.0.0', http_port),
    }
    # Prepare volume mappings (may include OVPN configs)
    volumes = {}

    # If there's an ovpn_tcp directory with .ovpn files, choose one at random
    try:
        ovpn_dir = os.path.join(os.path.dirname(__file__), 'ovpn_tcp')
        if os.path.isdir(ovpn_dir):
            ovpn_files = [f for f in os.listdir(ovpn_dir) if f.lower().endswith('.ovpn')]
            if ovpn_files:
                chosen = random.choice(ovpn_files)
                log_info(f"Selected OVPN config: {chosen}")
                # Mount the whole ovpn directory read-only into the container
                volumes[os.path.abspath(ovpn_dir)] = {'bind': '/gluetun/custom', 'mode': 'ro'}
                # Tell gluetun to use a custom provider and point to the chosen config (without extension)
                env['OPENVPN_PROVIDER'] = 'custom'
                env['OPENVPN_CONFIG'] = os.path.splitext(chosen)[0]
    except Exception as e:
        log_debug(f"OVPN selection/mount failed: {e}")
    
    try:
        log_info(f"Starting gluetun container {container_name} on port {http_port}...")
        
        container = client.containers.run(
            image='qmcgaw/gluetun:latest',
            name=container_name,
            cap_add=['NET_ADMIN'],
            devices=['/dev/net/tun:/dev/net/tun'],
            environment=env,
            volumes=volumes,
            ports=ports,
            detach=True,
            restart_policy={'Name': 'unless-stopped'},
        )
        
        log_info(f"Waiting for gluetun container to be ready...")
        max_wait = 120
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                container.reload()
                if container.status != 'running':
                    log_debug(f"Container status: {container.status}")
                    time.sleep(3)
                    continue
                
                test_proxy = f'http://127.0.0.1:{http_port}'
                test_response = get(
                    'http://httpbin.org/ip',
                    proxies={'http': test_proxy, 'https': test_proxy},
                    timeout=10
                )
                if test_response.status_code == 200:
                    elapsed = int(time.time() - start_time)
                    log_info(f"✓ Proxy ready after {elapsed}s!")
                    return {
                        'name': container_name,
                        'http_port': http_port,
                        'container': container,
                        'http_proxy': test_proxy,
                        'proxy_ready': True,
                    }
            except Exception as e:
                pass
            
            time.sleep(3)
        
        log_info(f"Proxy not ready after {max_wait}s, but continuing...")
        return {
            'name': container_name,
            'http_port': http_port,
            'container': container,
            'http_proxy': f'http://127.0.0.1:{http_port}',
            'proxy_ready': False,
        }
        
    except Exception as e:
        log_error(f"Error starting gluetun container: {e}")
        return None

def generate_username():
    """Generate random username"""
    users = ['sarah', 'isabella', 'sophia', 'charlotte', "Luna", "Mia", "Bella", "Sophie", "Ava", "Chloe", "Isla", "Ella", "Grace", "Zoe",
        "Ruby", "Lily", "Aria", "Nora", "Emma", "Scarlett", "Olivia", "Hana", "Amelia", "Layla"
    ]
    prefix = random.choice(users)
    suffix = '_'.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f'{prefix}{suffix}'

def generate_email():
    """Generate random email"""
    return f'{generate_username()}@gmail.com'

async def fill_input_field(instance, tagname: str, attrs: dict, value: str, description: str, timeout: int = 10) -> bool:
    """Fill input field with retries and verification.

    Attempts to find the input, clear it, send keys, and then verify the
    input contains the expected value. Retries a few times before failing.
    """
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            element = await instance.find(attrs=attrs, timeout=timeout)

            try:
                await element.scroll_into_view()
            except Exception:
                pass

            try:
                await element.clear_input()
            except Exception:
                pass

            try:
                await element.send_keys(value)
            except Exception as e:
                log_debug(f"send_keys failed on attempt {attempt}: {e}")

            # small pause to let the browser update the input value
            await asyncio.sleep(0.5 + (attempt - 1) * 0.3)

            # Verify value was set (try attribute 'value' or fallback to text)
            current = ''
            try:
                current = await element.get_attribute('value')
            except Exception:
                try:
                    current = await element.get_text()
                except Exception:
                    current = ''

            if current is not None and str(current).strip() != '':
                try:
                    if str(value) in str(current) or str(current) in str(value):
                        log_info(f"Filled {description} (attempt {attempt})")
                        return True
                except Exception:
                    pass

            log_debug(f"Attempt {attempt} to fill '{description}' did not verify (current='{current}'). Retrying...")

        except Exception as e:
            log_debug(f"Could not fill {description} on attempt {attempt}: {e}")

        # small backoff before retrying
        await asyncio.sleep(0.5 + attempt * 0.2)

    log_debug(f"Failed to fill {description} after {max_attempts} attempts")
    return True

async def click_by_text(instance, text: str = None, tagname: str = None, attrs: dict = None, timeout: int = 8) -> bool:
    """Click element by text or attributes"""
    try:
        elements = []
        
        if text:
            elements = await instance.find_all(text=text, timeout=timeout)
        elif attrs:
            elements = await instance.find_all(attrs=attrs, timeout=timeout)
        else:
            log_debug(f"Must provide text or attrs")
            return False
        
        if not elements:
            return False
        
        log_debug(f"Found {len(elements)} matching elements")
        
        for idx, el in enumerate(elements, start=1):
            try:
                try:
                    await el.scroll_into_view()
                except:
                    pass
                
                await el.click()
                log_debug(f"Clicked element #{idx}")
                return True
            except Exception as e:
                log_debug(f"Failed clicking element #{idx}: {e}")
        
        return False
    
    except Exception as e:
        log_debug(f"Error in click_by_text: {e}")
        return False

async def click_first_selector(instance, selectors: list, description: str, timeout: int = 5) -> bool:
    """Try multiple selectors"""
    for selector in selectors:
        try:
            element = await instance.select(selector, timeout=timeout)
            try:
                await element.scroll_into_view()
            except Exception:
                pass
            for _ in range(2):
                await element.click()
            log_info(f"Clicked {description} via selector: {selector}")
            return True
        except Exception as e:
            log_debug(f"Selector '{selector}' failed: {e}")
            continue
    log_error(f"Unable to click {description}")
    return False

async def perform_registration(instance, geo_info: dict) -> dict:
    """Execute Reddit registration flow"""
    log_info("Completing registration form...")
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    email = generate_email()
    username = generate_username()
    password = "13123244"
    
    if not await fill_input_field(instance, "input", {"name": "email"}, email, "email field", timeout=20):
        return None
    
    await asyncio.sleep(random.uniform(0.5, 1.0))
    if not await click_by_text(instance, attrs={"name": "email"}, timeout=10):
        log_debug("Email input not focused, trying continue button...")
    
    await asyncio.sleep(random.uniform(0.5, 1.0))
    if not await click_first_selector(
        instance,
        ["button[type='submit']", "button[class*='continue']"],
        "continue button",
    ):
        return None
    
    await asyncio.sleep(random.uniform(0.5, 1.0))
    try:
        await click_by_text(instance, attrs={"name": "skip"}, timeout=5)
    except Exception:
        pass
    
    await asyncio.sleep(random.uniform(0.5, 1.0))
    if not await fill_input_field(instance, "input", {"name": "username"}, username, "username field", timeout=15):
        return None
    
    if not await fill_input_field(instance, "input", {"name": "password"}, password, "password field", timeout=15):
        return None
    
    await asyncio.sleep(random.uniform(0.5, 1.0))
    signup_clicked = await click_first_selector(
        instance,
        ["[data-testid='signup-button']", "button[type='submit']", "form button[type='submit']"],
        "sign up button",
    )
    
    await asyncio.sleep(random.uniform(0.5, 1.0))
    if not signup_clicked:
        return None
    
    await asyncio.sleep(2)
    try:
        await click_by_text(instance, text="Skip", timeout=4)
    except Exception:
        pass
    
    status_code, content = fetch_html(f'https://www.reddit.com/user/{username}?captcha=1')
    log_info(f"Username: {username}")
    if not content or detect_reddit_account_status(content) != 'active':
        return None
    
    ip_address = geo_info.get("ip", "unknown")
    city = geo_info.get("city", "")
    
    account_info = {
        'username': username,
        'password': password,
        'email': email,
        'ip': ip_address,
        'city': city,
        'instance': INSTANCE_ID,
    }
    
    try:
        data_dir = DATA_DIR
        data_dir.mkdir(exist_ok=True)
        success_file = data_dir / "registration_success.txt"
        with open(success_file, "a", encoding="utf-8") as f:
            f.write(f"{username},{email},{password},{city},{ip_address},{INSTANCE_ID}\n")
        log_info(f"✓ Registered account {username} ({email})")
    except Exception as e:
        log_debug(f"Could not write success file: {e}")
    
    return account_info

async def create_browser_with_fingerprint(gluetun_info: dict = None, headless: bool = False, container_name: str = None):
    """Create browser with zendriver"""
    log_info("Getting IP geolocation...")
    geo_info, geo_success = get_ip_geolocation(gluetun_info, container_name=container_name)
    
    log_info(f"IP: {geo_info['ip']}")
    log_info(f"Location: {geo_info['city']}, {geo_info['region']}, {geo_info['country']}")
    log_info(f"Timezone: {geo_info['timezone']}")
    
    locale = 'en-US'
    log_info(f"Locale: {locale}")
    
    viewport_sizes = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1440, 'height': 900},
        {'width': 1280, 'height': 720},
    ]
    viewport = random.choice(viewport_sizes)
    log_info(f"Viewport: {viewport['width']}x{viewport['height']}")
    
    home_dir = os.path.expanduser("~")
    profile_base = os.path.join(home_dir, ".chrome_profiles")
    os.makedirs(profile_base, exist_ok=True)
    user_data_dir = os.path.join(profile_base, f"profile_{INSTANCE_ID}_{geo_info['ip'].replace('.', '_')}")
    
    # Clean old profile if it exists to avoid SingletonLock
    if os.path.exists(user_data_dir):
        try:
            import shutil
            shutil.rmtree(user_data_dir, ignore_errors=True)
            log_debug(f"Cleaned old profile: {user_data_dir}")
        except Exception as e:
            log_debug(f"Could not clean old profile: {e}")
    
    os.makedirs(user_data_dir, exist_ok=True)
    
    log_info(f"Profile dir: {user_data_dir}")
    
    chromium_path = find_chromium_executable()
    
    browser_config = zendriver.Config(
        user_data_dir=user_data_dir,
        browser_executable_path=chromium_path,
        browser_args=[
            "--disable-gpu",
            "--start-maximized",
            "--disable-background-networking",
            "--disable-sync",
            "--blink-settings=imagesEnabled=false",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ],
        sandbox=False
    )
    
    browser_config.headless = headless
    
    if gluetun_info and gluetun_info.get('http_proxy'):
        proxy_url = gluetun_info['http_proxy']
        proxy_parts = proxy_url.replace('http://', '').replace('https://', '').split(':')
        if len(proxy_parts) >= 2:
            proxy_host = proxy_parts[0]
            proxy_port = proxy_parts[1]
        else:
            proxy_host = '127.0.0.1'
            proxy_port = str(gluetun_info.get('http_port', 8888))
        
        proxy_server_arg = f"--proxy-server=http://{proxy_host}:{proxy_port}"
        browser_config.add_argument(proxy_server_arg)
        log_info(f"Using proxy: http://{proxy_host}:{proxy_port}")
    
    log_info("Starting browser...")
    browser = await zendriver.start(config=browser_config)
    
    instance = browser.targets[0] if browser.targets else await browser.get("about:blank")
    
    log_info("Setting browser fingerprint...")
    try:
        from zendriver import cdp
        
        await instance.send(cdp.emulation.set_timezone_override(timezone_id=geo_info['timezone']))
        log_info(f"✓ Set timezone to: {geo_info['timezone']}")
        
        await instance.send(cdp.emulation.set_geolocation_override(
            latitude=geo_info['latitude'],
            longitude=geo_info['longitude'],
            accuracy=100
        ))
        log_info(f"✓ Set geolocation to: {geo_info['latitude']}, {geo_info['longitude']}")
        
    except Exception as e:
        log_error(f"Could not set fingerprint: {e}")
    
    log_info("Navigating to Reddit...")
    post_url = 'https://www.reddit.com/r/StLouis/comments/1ozypnp/north_star_ice_cream_sandwiches?captcha=1'
    instance = await browser.get(post_url)
    await instance.wait()
    await asyncio.sleep(random.uniform(2, 4))
    
    # Try to dismiss cookie/consent banner by clicking a variety of possible "accept" buttons
    try:
        accept_texts = [
            "Accept all",
            "Accept All",
            "Accept all cookies",
            "Accept Cookies",
            "Accept cookies",
            "I agree",
            "Agree",
        ]
        accepted = False
        for t in accept_texts:
            try:
                btn = await instance.find(text=t, timeout=3)
                await btn.click()
                log_info(f"Clicked consent button: {t}")
                accepted = True
                await asyncio.sleep(1)
                break
            except Exception:
                pass

        # Fallback: look for common data attributes or role-based buttons
        if not accepted:
            try:
                candidates = await instance.find_all(attrs={"data-testid": "accept-button"}, timeout=3)
                for c in candidates:
                    try:
                        await c.click()
                        log_info("Clicked consent button (data-testid)")
                        accepted = True
                        break
                    except Exception:
                        pass
            except Exception:
                pass

        # Final fallback: try any button containing the word "accept" in its text
        if not accepted:
            try:
                candidates = await instance.find_all(timeout=3)
                for c in candidates:
                    try:
                        txt = ''
                        try:
                            txt = (await c.get_text()) or ''
                        except Exception:
                            pass
                        if 'accept' in txt.lower():
                            await c.click()
                            log_info("Clicked consent button (text match)")
                            accepted = True
                            break
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

    # Try to click the comments-action-button (use attrs-only API)
    try:
        buttons = await instance.find_all(attrs={"name": "comments-action-button"})
        for b in buttons:
            try:
                log_info("Clicking comment button")
                await b.click()
                break
            except Exception:
                pass
    except Exception as e:
        log_debug(f"Comment button not found: {e}")
    
    await asyncio.sleep(random.uniform(1, 2))
    
    account_info = await perform_registration(instance, geo_info)
    if account_info:
        log_info("✓ Registration flow completed")
    else:
        log_error("Registration flow failed")
    
    return browser, instance, geo_info, account_info

async def cleanup_chrome_profile(profile_path: str):
    """Clean up Chrome profile"""
    try:
        import shutil
        if os.path.exists(profile_path):
            shutil.rmtree(profile_path, ignore_errors=True)
            log_debug(f"Cleaned up profile: {profile_path}")
    except Exception as e:
        log_debug(f"Could not clean up profile: {e}")

async def kill_all_chrome_instances():
    """Kill chromium processes"""
    import subprocess
    try:
        subprocess.run(["pkill", "-9", "chromium"], check=False, capture_output=True)
        log_info("Killed chromium instances")
    except Exception as e:
        log_debug(f"Could not kill chromium: {e}")

async def register_account(gluetun_info: dict = None, headless: bool = False, container_name: str = None) -> dict:
    """Register Reddit account"""
    browser = None
    profile_path = None
    
    try:
        browser, instance, geo_info, account_info = await create_browser_with_fingerprint(
            gluetun_info=gluetun_info,
            headless=headless,
            container_name=container_name
        )
        
        if browser and hasattr(browser, 'config') and hasattr(browser.config, 'user_data_dir'):
            profile_path = browser.config.user_data_dir
        
        return account_info
    except Exception as e:
        log_error(f"Failed to register account: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        try:
            if browser:
                await browser.stop()
                log_info("Browser stopped")
        except Exception as e:
            log_debug(f"Error stopping browser: {e}")
        
        await asyncio.sleep(1)
        await kill_all_chrome_instances()
        
        if profile_path:
            await cleanup_chrome_profile(profile_path)
        
        await asyncio.sleep(2)

async def main():
    """Main registration loop"""
    global logger
    logger = setup_logging()
    
    log_info("=" * 60)
    log_info(f"Reddit Account Registration Service - Instance {INSTANCE_ID}")
    log_info("=" * 60)
    
    # Load configuration
    config = load_config()
    if not config:
        log_error("Failed to load configuration")
        return
    
    # Get instance-specific container name
    container_name = get_instance_container_name()
    log_info(f"Using container: {container_name}")
    
    # Start gluetun container
    log_info(f"Starting gluetun container...")
    gluetun_info = start_gluetun_container(container_name, config)
    
    if not gluetun_info:
        log_error("Failed to start gluetun container")
        return
    
    log_info(f"✓ Gluetun container started")
    log_info(f"  HTTP Proxy: {gluetun_info['http_proxy']}")
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    account_count = 0
    log_info(f"Starting registration loop...")
    
    while True:
        try:
            log_info(f"\n[ATTEMPT] Creating account #{account_count + 1}...")
            account_info = await register_account(
                gluetun_info=gluetun_info,
                headless=False,
                container_name=container_name
            )
            
            if account_info:
                account_count += 1
                log_info(f"✓ Account saved. Total: {account_count}")
                
                # Restart proxy after success
                try:
                    log_info(f"Restarting proxy after successful account creation...")
                    restart_gluetun_container(container_name)
                except Exception as e:
                    log_debug(f"Restart failed: {e}")
            else:
                log_error(f"Account registration failed")
                
                # Restart proxy after failure
                try:
                    log_info(f"Restarting proxy after failed attempt...")
                    restart_gluetun_container(container_name)
                except Exception as e:
                    log_debug(f"Restart failed: {e}")
        
        except Exception as e:
            log_error(f"Exception in registration loop: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            log_info(f"Waiting 3 seconds before next attempt...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Reddit Account Registration for VPS")
    parser.add_argument('--instance', type=int, default=1, help='Instance ID (1, 2, 3, etc.)')
    args = parser.parse_args()
    
    INSTANCE_ID = args.instance
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        sys.exit(0)
