#!/usr/bin/env python3
"""
Reddit Account Registration with Camoufox Anti-Detect Browser
Supports multiple concurrent instances with unique gluetun containers
Uses Camoufox + Playwright for superior anti-detection capabilities

Installation:
    pip install camoufox playwright beautifulsoup4 requests docker

Usage:
    python camoufox.py --instance 1 (or 2, 3, etc.)
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

import asyncio
# Removed hardcoded virtualenv path and unconditional camoufox import to be portable on VPS.
# The camoufox import is handled below with a try/except to provide a clear error message if missing.

# Try to import Playwright (Camoufox uses Playwright's API)
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    print("[ERROR] Playwright not found. Install via: pip install playwright")
    print("Then run: playwright install firefox")
    sys.exit(1)

# Try to import camoufox
try:
    from camoufox import AsyncCamoufox
    from camoufox import fingerprints
except ImportError as e:
    print(f"[ERROR] Camoufox not found. Install via: pip install camoufox ({e})")
    sys.exit(1)

from bs4 import BeautifulSoup

# Try to import docker
# Try to import docker
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    print("[WARNING] Docker python package not available. Install it with: pip install docker")
    print("Note: To run containers on the VPS you also need Docker Engine installed (system package).")
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
    log_file = logs_dir / f"camoufox_instance_{INSTANCE_ID}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized for instance {INSTANCE_ID} (Camoufox)")
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

def validate_and_refresh_gluetun_info(container_name: str, gluetun_info: dict = None, retries: int = 3, probe_timeout: int = 5) -> dict:
    """Ensure gluetun_info['http_proxy'] points to the live host port and probe it."""
    client = get_docker_client()
    if not client:
        log_debug("Docker not available for proxy validation")
        return gluetun_info

    try:
        container = client.containers.get(container_name)
    except Exception as e:
        log_debug(f"Could not inspect container {container_name}: {e}")
        return gluetun_info

    # Determine host port for container's proxy port
    host_port = None
    try:
        ports = container.attrs.get('NetworkSettings', {}).get('Ports', {}) or {}
        if '8888/tcp' in ports and ports['8888/tcp']:
            host_port = ports['8888/tcp'][0].get('HostPort')
        else:
            # Fallback: pick any mapped tcp host port
            for k, v in ports.items():
                if v and k.endswith('/tcp'):
                    host_port = v[0].get('HostPort')
                    break
    except Exception as e:
        log_debug(f"Error reading container ports: {e}")

    if not host_port:
        log_debug("Could not determine host port for proxy")
        return gluetun_info

    proxy_url = f'http://127.0.0.1:{host_port}'
    if gluetun_info is None:
        gluetun_info = {}
    gluetun_info.update({'http_port': int(host_port), 'http_proxy': proxy_url, 'container': container})

    # Quick probe with retries
    for attempt in range(1, retries + 1):
        try:
            log_debug(f"Probing proxy {proxy_url} (attempt {attempt}/{retries})")
            r = requests.get('http://httpbin.org/ip', proxies={'http': proxy_url, 'https': proxy_url}, timeout=probe_timeout)
            if r.status_code == 200:
                log_info(f"Proxy probe successful ({proxy_url})")
                return gluetun_info
            else:
                log_debug(f"Proxy probe returned status {r.status_code}")
        except Exception as e:
            log_debug(f"Proxy probe failed (attempt {attempt}): {e}")

        # Quick restart attempt before next probe
        try:
            log_info(f"Quickly restarting {container_name} to refresh proxy (attempt {attempt})")
            container.restart(timeout=10)
            time.sleep(2 + attempt)
            container.reload()
        except Exception as e:
            log_debug(f"Quick restart failed: {e}")

    log_error(f"Proxy did not respond after {retries} quick attempts: {proxy_url}")
    return None

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
        # DNS configuration - CRITICAL for geolocation and connectivity
        'DNS_ADDRESS': '1.1.1.1,1.0.0.1',  # Cloudflare DNS
        'DNS_KEEP_ALIVE': '30',
        # Firewall - allow all outbound for HTTP proxy
        'FIREWALL_ENABLED': 'off',  # Disable firewall for external proxy access
        # Enable health checks and logging
        'LOG_LEVEL': 'info',
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
    volumes = {}

    # OVPN file selection
    try:
        ovpn_dir = os.path.join(os.path.dirname(__file__), 'ovpn_tcp')
        if os.path.isdir(ovpn_dir):
            ovpn_files = [f for f in os.listdir(ovpn_dir) if f.lower().endswith('.ovpn')]
            if ovpn_files:
                chosen = random.choice(ovpn_files)
                log_info(f"Selected OVPN config: {chosen}")
                volumes[os.path.abspath(ovpn_dir)] = {'bind': '/gluetun/custom', 'mode': 'ro'}
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
            healthcheck={
                'test': ['CMD', 'curl', '-f', 'http://127.0.0.1:8888/', '-x', 'http://127.0.0.1:8888/', '--connect-timeout', '5'],
                'interval': 10,
                'timeout': 5,
                'retries': 3,
                'start_period': 30,
            },
        )
        
        log_info(f"Waiting for gluetun container to be ready...")
        max_wait = 120
        start_time = time.time()
        health_check_passed = False
        
        while time.time() - start_time < max_wait:
            try:
                container.reload()
                health = container.attrs.get('State', {}).get('Health', {})
                health_status = health.get('Status', 'unknown')
                
                log_debug(f"Container status: {container.status}, Health: {health_status}")
                
                if container.status != 'running':
                    time.sleep(2)
                    continue
                
                # Try proxy test first
                test_proxy = f'http://127.0.0.1:{http_port}'
                try:
                    test_response = get(
                        'http://httpbin.org/ip',
                        proxies={'http': test_proxy, 'https': test_proxy},
                        timeout=8
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
                    log_debug(f"Proxy test failed: {e}")
                
            except Exception as e:
                log_debug(f"Container check error: {e}")
            
            time.sleep(3)
        
        log_info(f"Proxy not ready after {max_wait}s, but continuing with retries...")
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

async def fill_input_field_camoufox(page, selector: str, value: str, description: str, timeout: int = 10) -> bool:
    """Fill input field with retries and verification using Camoufox/Playwright"""
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            await page.fill(selector, value, timeout=timeout * 1000)
            await asyncio.sleep(0.5)
            
            # Verify value was set
            current = await page.input_value(selector)
            if current and str(current).strip():
                if str(value) in str(current) or str(current) in str(value):
                    log_info(f"Filled {description} (attempt {attempt})")
                    return True
            
            log_debug(f"Attempt {attempt} to fill '{description}' did not verify (current='{current}'). Retrying...")
        except Exception as e:
            log_debug(f"Could not fill {description} on attempt {attempt}: {e}")
        
        await asyncio.sleep(0.5 + attempt * 0.2)
    
    log_debug(f"Failed to fill {description} after {max_attempts} attempts")
    return True

async def click_by_text_camoufox(page, text: str = None, selector: str = None, timeout: int = 8) -> bool:
    """Click element by text or selector using Camoufox/Playwright"""
    try:
        if selector:
            await page.click(selector, timeout=timeout * 1000)
            log_debug(f"Clicked via selector: {selector}")
            return True
        elif text:
            # Try to find and click by text
            await page.click(f"text={text}", timeout=timeout * 1000)
            log_debug(f"Clicked via text: {text}")
            return True
        else:
            return False
    except Exception as e:
        log_debug(f"Error clicking: {e}")
        return False

async def perform_registration_camoufox(page, geo_info: dict) -> dict:
    """Execute Reddit registration flow with Camoufox"""
    log_info("Completing registration form...")
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    email = generate_email()
    username = generate_username()
    password = "13123244"
    
    try:
        # Fill email field
        log_info(f"Filling email: {email}")
        try:
            await page.fill('input[name="email"]', email, timeout=10000)
            log_info("✓ Email filled")
        except Exception as e:
            log_debug(f"Email fill failed: {e}, trying alternative selector...")
            try:
                await page.fill('input[type="email"]', email, timeout=10000)
                log_info("✓ Email filled (alt selector)")
            except Exception as e2:
                log_error(f"Could not fill email: {e2}")
                return None
        
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Click continue button
        log_info("Clicking continue button...")
        continue_clicked = False
        
        continue_selectors = [
            'button:has-text("Continue")',
            'button[type="submit"]:has-text("Continue")',
            'button[aria-label*="Continue"]',
            '[data-testid="continue-button"]',
            'button:nth-of-type(1)',  # First button as fallback
        ]
        
        for selector in continue_selectors:
            try:
                log_debug(f"Trying continue selector: {selector}")
                await page.click(selector, timeout=5000)
                log_info(f"✓ Continue button clicked (selector: {selector})")
                continue_clicked = True
                break
            except Exception as e:
                log_debug(f"Continue selector '{selector}' failed: {e}")
        
        if not continue_clicked:
            log_error("Could not click continue button with any selector")
            # Try to press Enter key as last resort
            try:
                await page.press('input[name="email"]', 'Enter')
                log_info("✓ Pressed Enter on email field")
                continue_clicked = True
            except Exception as e:
                log_debug(f"Enter key failed: {e}")
        
        if not continue_clicked:
            return None
        
        await asyncio.sleep(random.uniform(1.0, 2.0))
        
        # Try to skip optional fields
        try:
            await page.click('button:has-text("Skip")', timeout=5000)
            log_info("✓ Skipped optional fields")
        except Exception:
            log_debug("Skip button not found")
        
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Fill username
        log_info(f"Filling username: {username}")
        try:
            await page.fill('input[name="username"]', username, timeout=10000)
            log_info("✓ Username filled")
        except Exception as e:
            log_error(f"Could not fill username: {e}")
            return None
        
        # Fill password
        log_info(f"Filling password...")
        try:
            await page.fill('input[name="password"]', password, timeout=10000)
            log_info("✓ Password filled")
        except Exception as e:
            log_error(f"Could not fill password: {e}")
            return None
        
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Click sign up button
        log_info("Clicking sign up button...")
        signup_clicked = False
        
        # Try multiple selectors for sign up button
        signup_selectors = [
            '[data-testid="signup-button"]',
            'button[type="submit"]:has-text("Sign Up")',
            'button:has-text("Sign Up")',
            'button[type="submit"]',
        ]
        
        for selector in signup_selectors:
            try:
                await page.click(selector, timeout=500)
                log_info(f"✓ Sign up button clicked (selector: {selector})")
                await asyncio.sleep(1)
                signup_clicked = True
                break
            except Exception as e:
                log_debug(f"Sign up selector '{selector}' failed: {e}")
        
        if not signup_clicked:
            log_error("Could not click sign up button")
            await page.locator("button[type='submit']").dblclick()
            signup_clicked = True
        
        await asyncio.sleep(2)
        
        # Try to skip bonus features
        try:
            await page.click('button:has-text("Skip")', timeout=4000)
            log_info("✓ Skipped bonus features")
        except Exception:
            log_debug("Skip button not found for bonus features")
        
        # Verify account
        log_info(f"Verifying account: {username}")
        status_code, content = fetch_html(f'https://www.reddit.com/user/{username}?captcha=1')
        
        if not content:
            log_error("Could not fetch user page for verification")
            return None
        
        account_status = detect_reddit_account_status(content)
        log_info(f"Account status: {account_status}")
        
        if account_status != 'active':
            log_error(f"Account not active, status: {account_status}")
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
        
    except Exception as e:
        log_error(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        return None

async def create_browser_with_camoufox(gluetun_info: dict = None, headless: bool = False, container_name: str = None):
    """Create browser with Camoufox + Playwright"""
    log_info("Getting IP geolocation...")

    # Fast validation/refresh of gluetun_info
    refreshed = None
    try:
        refreshed = validate_and_refresh_gluetun_info(container_name, gluetun_info, retries=2, probe_timeout=4)
        if refreshed:
            gluetun_info = refreshed
    except Exception as e:
        log_debug(f"validate_and_refresh_gluetun_info failed: {e}")

    # Get geolocation
    geo_info, geo_success = get_ip_geolocation(gluetun_info, container_name=container_name)

    # Geolocation retry logic
    if (not geo_success or not geo_info.get('city')):
        max_geo_attempts = int(os.environ.get('GEO_MAX_RETRIES', '3'))
        geo_attempt = 1
        while (not geo_success or not geo_info.get('city')) and geo_attempt <= max_geo_attempts:
            log_info(f"Geolocation invalid (retry {geo_attempt}/{max_geo_attempts}). Quick restart and re-check...")
            try:
                restart_gluetun_container(container_name)
            except Exception as e:
                log_debug(f"Quick restart failed: {e}")

            # After restarting, make up to 2 geolocation attempts
            geo_checked = False
            for geo_try in range(1, 3):
                wait = 1 + geo_try
                log_info(f"Waiting {wait}s before geolocation re-check (try {geo_try}/2)...")
                time.sleep(wait)
                geo_info, geo_success = get_ip_geolocation(gluetun_info, container_name=container_name)
                if geo_success and geo_info.get('city'):
                    geo_checked = True
                    log_info(f"Geolocation obtained after restart: {geo_info.get('city')}, {geo_info.get('country')}")
                    break

            if not geo_checked:
                geo_attempt += 1

    if not geo_success or not geo_info.get('city'):
        log_info("Proceeding with default/unknown geolocation after quick retries")

    log_info(f"IP: {geo_info.get('ip', 'unknown')}")
    log_info(f"Location: {geo_info.get('city','')}, {geo_info.get('region','')}, {geo_info.get('country','US')}")
    log_info(f"Timezone: {geo_info.get('timezone','America/New_York')}")
    
    # Generate Camoufox fingerprint config
    fp_config = {
        "timezone": geo_info.get('timezone', 'America/New_York'),
        "geolocation": {
            "latitude": geo_info.get('latitude', 0),
            "longitude": geo_info.get('longitude', 0),
            "accuracy": 100
        },
        "locale": "en-US",
    }
    
    # Setup proxy if available (needs to be dict format for Camoufox)
    proxy_server = None
    if gluetun_info and gluetun_info.get('http_proxy'):
        proxy_url = gluetun_info['http_proxy']
        proxy_parts = proxy_url.replace('http://', '').replace('https://', '').split(':')
        if len(proxy_parts) >= 2:
            proxy_server = {
                'server': f"http://{proxy_parts[0]}:{proxy_parts[1]}"
            }
            log_info(f"Using proxy: {proxy_server['server']}")
    
    log_info("Starting Camoufox browser...")
    
    # Start Camoufox with retries
    browser = None
    max_browser_attempts = 3
    for browser_attempt in range(1, max_browser_attempts + 1):
        try:
            # Build launch options dict
            launch_kwargs = {}
            
            if proxy_server:
                launch_kwargs['proxy'] = proxy_server
                launch_kwargs['geoip'] = True  # Enable geoip with proxy

            if headless:
                launch_kwargs['headless'] = False
                launch_kwargs["locale"] = "en-US"
            # launch_kwargs['geoip'] = True
            # Initialize Camoufox with launch options passed to constructor
            camoufox_obj = AsyncCamoufox(**launch_kwargs)
            
            # Start the browser (no kwargs to start())
            browser = await camoufox_obj.start()
            
            log_info(f"Camoufox browser started (attempt {browser_attempt})")
            break
        except Exception as e:
            log_debug(f"Browser startup failed (attempt {browser_attempt}): {e}")
            if browser_attempt < max_browser_attempts:
                await asyncio.sleep(3 + (browser_attempt * 2))
            else:
                log_error(f"Failed to start browser after {max_browser_attempts} attempts")
                raise
    
    log_info("Navigating to Reddit...")
    post_url = 'https://www.reddit.com/r/StLouis/comments/1ozypnp/north_star_ice_cream_sandwiches?captcha=1'
    
    # Navigation with retries
    page = None
    nav_attempts = 0
    max_nav_attempts = 2
    while nav_attempts < max_nav_attempts:
        try:
            page = await browser.new_page()
            
            # Block image loading for faster page loads
            async def block_images(route):
                if 'image' in route.request.resource_type:
                    await route.abort()
                else:
                    await route.continue_()
            
            await page.route('**/*', block_images)
            log_debug("Image blocking enabled")
            
            await page.goto(post_url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            break
        except Exception as e:
            nav_attempts += 1
            if page:
                try:
                    await page.close()
                except:
                    pass
            log_debug(f"Navigation attempt {nav_attempts} failed: {e}")
            if nav_attempts < max_nav_attempts:
                await asyncio.sleep(3)
            else:
                log_error(f"Failed to navigate after {max_nav_attempts} attempts")
                raise
    
    await asyncio.sleep(random.uniform(2, 4))
    
    # Try to dismiss cookie/consent banner
    try:
        accept_texts = ["Accept all", "Accept All", "Accept all cookies", "I agree", "Agree"]
        for text in accept_texts:
            try:
                await click_by_text_camoufox(page, text=text, timeout=3)
                log_info(f"Clicked consent button: {text}")
                await asyncio.sleep(1)
                break
            except Exception:
                pass
    except Exception:
        pass
    
    await asyncio.sleep(random.uniform(1, 2))
    
    # Click on comment button to open registration modal
    try:
        # Try to find comment button by various selectors
        comment_selectors = [
            'button[name="comments-action-button"]',
            '[name="comments-action-button"]',
            'button:has-text("Comment")',
        ]
        
        comment_clicked = False
        for selector in comment_selectors:
            try:
                await page.click(selector, timeout=5000)
                log_info("✓ Clicked comment button to open registration modal")
                comment_clicked = True
                await asyncio.sleep(1)
                break
            except Exception:
                raise
        
        if not comment_clicked:
            log_debug("Comment button not found via selectors, continuing anyway...")
    except Exception as e:
        log_debug(f"Error clicking comment button: {e}")
    
    await asyncio.sleep(random.uniform(1, 2))
    
    # Perform registration
    account_info = await perform_registration_camoufox(page, geo_info)
    if account_info:
        log_info("✓ Registration flow completed")
    else:
        log_error("Registration flow failed")
    
    return browser, page, geo_info, account_info

async def register_account(gluetun_info: dict = None, headless: bool = False, container_name: str = None) -> dict:
    """Register Reddit account using Camoufox"""
    browser = None
    page = None
    
    try:
        browser, page, geo_info, account_info = await create_browser_with_camoufox(
            gluetun_info=gluetun_info,
            headless=headless,
            container_name=container_name
        )
        
        return account_info
    except Exception as e:
        log_error(f"Failed to register account: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        try:
            if page:
                await page.close()
                log_info("Page closed")
        except Exception as e:
            log_debug(f"Error closing page: {e}")
        
        try:
            if browser:
                await browser.stop()
                log_info("Browser closed")
        except Exception as e:
            log_debug(f"Error closing browser: {e}")
        
        await asyncio.sleep(2)

async def main():
    """Main registration loop"""
    global logger
    logger = setup_logging()
    
    log_info("=" * 60)
    log_info(f"Reddit Account Registration Service - Instance {INSTANCE_ID}")
    log_info(f"Using: Camoufox + Playwright (Anti-Detection)")
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
                headless=True,
                container_name=container_name
            )
            
            # Clean up resources after each attempt
            try:
                log_debug("Cleaning up resources...")
                import gc
                import subprocess
                
                # Force garbage collection
                gc.collect()
                
                # Clear temp files
                subprocess.run(['rm', '-rf', '/tmp/.mozilla*'], shell=True, timeout=5)
                subprocess.run(['rm', '-rf', '/tmp/camoufox*'], shell=True, timeout=5)
                
                log_debug("✓ Resources cleaned")
            except Exception as e:
                log_debug(f"Resource cleanup error: {e}")
            
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
    parser = argparse.ArgumentParser(description="Reddit Account Registration with Camoufox Anti-Detect Browser")
    parser.add_argument('--instance', type=int, default=1, help='Instance ID (1, 2, 3, etc.)')
    args = parser.parse_args()
    
    INSTANCE_ID = args.instance
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        sys.exit(0)
