#!/usr/bin/env python3
"""
Reddit Account Registration with Camoufox Anti-Detect Browser
Uses proxy.txt for IP rotation (no gluetun/VPN containers needed)
Uses Camoufox + Playwright for superior anti-detection capabilities
"""
# Installation:
#     pip install camoufox playwright beautifulsoup4 requests

# Usage:
#     python reddit_register.py --instance 1 (or 2, 3, etc.)


import sys
import asyncio
import time
import json
import random
import string
import re
from typing import List, Optional
import requests
from requests import get
import os
import argparse
import logging
from pathlib import Path
import warnings
import shutil


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
import subprocess

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

# Proxy test URL
PROXY_TEST_URL = "https://api.ipify.org?format=json"

# Global instance ID (set via CLI)
INSTANCE_ID = 1
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CAMOUFOX_USER_DATA_DIR = BASE_DIR / "user-data-dir"
WARMED_SESSION_DIR = BASE_DIR / "warmed-session"  # Pre-warmed session template
PROXY_FILE = BASE_DIR / "proxy.txt"
BAD_PROXY_FILE = BASE_DIR / "bad_proxy.txt"

# SSH upload configuration
SSH_HOST = "your-server.com"  # Change this to your server
SSH_USER = "your-username"     # Change this to your SSH username
SSH_REMOTE_PATH = "/path/to/remote/accounts.txt"  # Change this to remote path
SSH_KEY_PATH = Path.home() / ".ssh" / "id_rsa"  # Path to SSH private key
UPLOAD_EVERY_N_ACCOUNTS = 10  # Upload after every N successful accounts
SLEEP_AFTER_ACCOUNT = 15  # Seconds to sleep after each account creation

# Reddit posts to visit during warm-up (before registration)
WARMUP_POSTS = [
    "https://www.reddit.com/r/AskReddit/",
    "https://www.reddit.com/r/pics/",
    "https://www.reddit.com/r/funny/",
    "https://www.reddit.com/r/todayilearned/",
    "https://www.reddit.com/r/movies/",
    "https://www.reddit.com/r/gaming/",
    "https://www.reddit.com/r/aww/",
    "https://www.reddit.com/r/music/",
    "https://www.reddit.com/r/videos/",
    "https://www.reddit.com/r/news/",
    "https://www.reddit.com/r/worldnews/",
    "https://www.reddit.com/r/science/",
    "https://www.reddit.com/r/sports/",
    "https://www.reddit.com/r/food/",
    "https://www.reddit.com/r/technology/",
]
WARMUP_BROWSE_TIME = 15  # Seconds to spend on each warmup post
WARMUP_POST_COUNT = 3    # Number of posts to visit before registration

# Setup logging
def setup_logging():
    """Setup logging with instance-specific log file"""
    logs_dir = LOGS_DIR
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"instance_{INSTANCE_ID}.log"
    
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


def generate_machine_id() -> str:
    """Generate a random machine ID (32 hex characters)."""
    return ''.join(random.choices('0123456789abcdef', k=32))

def spoof_machine_id():
    """Spoof system machine IDs by setting environment variables and creating temp files."""
    new_machine_id = generate_machine_id()
    new_boot_id = generate_machine_id()
    
    # Set environment variables that some fingerprinting might check
    os.environ['MACHINE_ID'] = new_machine_id
    os.environ['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path=/tmp/dbus-{new_machine_id[:8]}'
    
    # Create spoofed machine-id file in temp location
    try:
        temp_machine_id = Path('/tmp/.machine-id-spoof')
        temp_machine_id.write_text(new_machine_id + '\n')
    except Exception:
        pass
    
    log_info(f"✓ Spoofed machine ID: {new_machine_id[:16]}...")
    return new_machine_id


def copy_warmed_session():
    """Copy the warmed session to user-data-dir instead of creating empty one."""
    try:
        # Remove existing user data dir
        if CAMOUFOX_USER_DATA_DIR.exists():
            shutil.rmtree(CAMOUFOX_USER_DATA_DIR)
        
        # Copy warmed session if it exists
        if WARMED_SESSION_DIR.exists():
            shutil.copytree(WARMED_SESSION_DIR, CAMOUFOX_USER_DATA_DIR)
            log_info(f"✓ Copied warmed session to {CAMOUFOX_USER_DATA_DIR}")
        else:
            # Create empty dir if no warmed session exists
            CAMOUFOX_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            log_info(f"No warmed session found, created empty dir: {CAMOUFOX_USER_DATA_DIR}")
    except Exception as e:
        log_error(f"Failed to copy warmed session: {e}")
        # Fallback to creating empty dir
        CAMOUFOX_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)


async def create_warmed_session(proxy_config: dict = None):
    """Create a warmed browser session by visiting Reddit posts.
    
    The session is saved directly to user-data-dir for immediate use.
    """
    log_info("Creating warmed browser session...")
    
    try:
        # Clean user data dir for fresh start
        if CAMOUFOX_USER_DATA_DIR.exists():
            shutil.rmtree(CAMOUFOX_USER_DATA_DIR)
        CAMOUFOX_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Launch browser with proxy
        browser, page = await launch_camoufox_browser(proxy_config=proxy_config, headless=False)
        
        try:
            # Visit each warmup post
            for i, url in enumerate(WARMUP_POSTS, 1):
                log_info(f"[WARMUP {i}/{len(WARMUP_POSTS)}] Visiting: {url}")
                try:
                    await page.goto(url, timeout=30000)
                    # Random delay to simulate human browsing
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    # Scroll down a bit
                    await page.evaluate("window.scrollBy(0, 500)")
                    await asyncio.sleep(random.uniform(1, 2))
                    
                    # Scroll more
                    await page.evaluate("window.scrollBy(0, 300)")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    log_error(f"Failed to visit {url}: {e}")
                    continue
            
            log_info("✓ Finished warmup - session ready in user-data-dir")
            
        finally:
            await browser.close()
        
        return True
        
    except Exception as e:
        log_error(f"Failed to create warmed session: {e}")
    
    return False


def clean_user_data_dir():
    """Remove and recreate the Camoufox user data directory before running."""
    try:
        if CAMOUFOX_USER_DATA_DIR.exists():
            shutil.rmtree(CAMOUFOX_USER_DATA_DIR)
            log_info(f"Cleared Camoufox user data dir: {CAMOUFOX_USER_DATA_DIR}")
        CAMOUFOX_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_error(f"Failed to reset user data dir {CAMOUFOX_USER_DATA_DIR}: {e}")

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


# Proxy file management (host:port:user:pass format)
def load_proxies() -> List[dict]:
    """Load proxies from proxy.txt file (format: host:port:user:pass)"""
    if not PROXY_FILE.exists():
        return []
    
    proxies = []
    try:
        with open(PROXY_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(':')
                if len(parts) >= 2:
                    proxy = {
                        'host': parts[0],
                        'port': parts[1],
                        'user': parts[2] if len(parts) > 2 else None,
                        'password': parts[3] if len(parts) > 3 else None,
                        'raw': line
                    }
                    proxies.append(proxy)
        log_info(f"Loaded {len(proxies)} proxies from {PROXY_FILE}")
        return proxies
    except Exception as e:
        log_error(f"Failed to load proxies: {e}")
        return []


def load_bad_proxies() -> set:
    """Load list of bad proxy entries"""
    if not BAD_PROXY_FILE.exists():
        return set()
    try:
        with open(BAD_PROXY_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()


def save_bad_proxies(bad_proxies: set):
    """Save bad proxies to file"""
    try:
        with open(BAD_PROXY_FILE, 'w') as f:
            for proxy in bad_proxies:
                f.write(f"{proxy}\n")
    except Exception as e:
        log_error(f"Failed to save bad proxies: {e}")


def mark_proxy_as_bad(proxy_raw: str, bad_set: set) -> set:
    """Add proxy to bad list"""
    bad_set.add(proxy_raw)
    save_bad_proxies(bad_set)
    log_info(f"Marked proxy as bad: {proxy_raw.split(':')[0]}:***")
    return bad_set


def upload_accounts_via_ssh(batch_file: Path) -> bool:
    """Upload a specific batch accounts file to remote server via SCP using SSH key."""
    
    if not batch_file.exists():
        log_error(f"No accounts file to upload: {batch_file}")
        return False
    
    if not SSH_KEY_PATH.exists():
        log_error(f"SSH key not found at {SSH_KEY_PATH}")
        return False
    
    try:
        # Determine remote filename - keep same name as local batch file
        remote_file = f"{SSH_REMOTE_PATH}/{batch_file.name}"
        
        # Build SCP command with SSH key
        scp_cmd = [
            "scp",
            "-i", str(SSH_KEY_PATH),
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            str(batch_file),
            f"{SSH_USER}@{SSH_HOST}:{remote_file}"
        ]
        
        log_info(f"Uploading {batch_file.name} to {SSH_USER}@{SSH_HOST}:{remote_file}...")
        result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            log_info(f"✓ {batch_file.name} uploaded successfully via SSH")
            return True
        else:
            log_error(f"SCP failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log_error("SSH upload timed out after 60 seconds")
        return False
    except Exception as e:
        log_error(f"Failed to upload accounts via SSH: {e}")
        return False


def get_next_batch_index() -> int:
    """Get the next batch index by checking existing batch files."""
    existing_batches = list(DATA_DIR.glob("accounts_*.csv"))
    if not existing_batches:
        return 1
    
    # Extract indices from filenames like accounts_1.csv, accounts_2.csv
    indices = []
    for f in existing_batches:
        try:
            # Extract number from accounts_N.csv
            idx = int(f.stem.split('_')[1])
            indices.append(idx)
        except (IndexError, ValueError):
            continue
    
    return max(indices) + 1 if indices else 1


def save_account_to_batch(account_info: dict, batch_accounts: list) -> list:
    """Add account to current batch list."""
    batch_accounts.append(f"{account_info['username']},{account_info['password']}")
    return batch_accounts


def create_and_upload_batch(batch_accounts: list, batch_index: int) -> bool:
    """Create a batch CSV file with accounts and upload it via SSH."""
    if not batch_accounts:
        log_error("No accounts in batch to save")
        return False
    
    DATA_DIR.mkdir(exist_ok=True)
    batch_file = DATA_DIR / f"accounts{batch_index}.csv"
    
    try:
        with open(batch_file, 'w', encoding='utf-8') as f:
            # Write CSV header
            f.write("username,password\n")
            for account in batch_accounts:
                f.write(f"{account}\n")
        
        log_info(f"✓ Created batch file: {batch_file.name} with {len(batch_accounts)} accounts")
        
        # Upload the batch file
        upload_success = upload_accounts_via_ssh(batch_file)
        return upload_success
        
    except Exception as e:
        log_error(f"Failed to create batch file: {e}")
        return False


def get_available_proxies(proxies: List[dict], bad_proxies: set) -> List[dict]:
    """Filter out bad proxies"""
    return [p for p in proxies if p['raw'] not in bad_proxies]


def build_proxy_url(proxy: dict) -> str:
    """Build proxy URL from proxy dict (for requests library)"""
    if proxy.get('user') and proxy.get('password'):
        return f"http://{proxy['user']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
    else:
        return f"http://{proxy['host']}:{proxy['port']}"


def build_proxy_config(proxy: dict) -> dict:
    """Build proxy config for Camoufox (separate server, username, password)"""
    server = f"http://{proxy['host']}:{proxy['port']}"
    config = {'server': server}
    if proxy.get('user') and proxy.get('password'):
        config['username'] = proxy['user']
        config['password'] = proxy['password']
    return config


async def test_proxy(proxy_url: str, timeout: int = 10) -> Optional[str]:
    """Test if proxy works and return the IP if successful"""
    proxies = {"http": proxy_url}
    
    def _test() -> Optional[str]:
        try:
            response = requests.get(PROXY_TEST_URL, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                return response.json().get("ip", "unknown")
        except Exception:
            pass
        return None
    
    return await asyncio.to_thread(_test)


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

def get_ip_geolocation(proxy_url: str = None) -> tuple:
    """Get IP geolocation"""
    proxies = None
    if proxy_url:
        proxies = {'http': proxy_url}
    
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

async def perform_registration_camoufox(page) -> dict:
    """Execute Reddit registration flow with Camoufox"""
    log_info("Completing registration form...")
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    email = generate_email()
    username = generate_username()
    password = "13123244"
    
    try:
        # Fill email field
        # Click accept all button if present
        try:
            await page.click('button:has-text("Accept All")', timeout=5000)
            log_info("✓ Accepted all cookies")
        except Exception:
            log_debug("Accept All button not found or not clickable")
        
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
        for _ in range(2):
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
        
        try:
            await page.click("button[type='submit']", timeout=100)
            signup_clicked = True
        except Exception as e:
            log_debug(f"Direct sign up button click failed: {e}")
        # Try multiple selectors for sign up button
        if not signup_clicked:
            signup_selectors = [
                '[data-testid="signup-button"]',
                'button[type="submit"]:has-text("Sign Up")',
                'button:has-text("Sign Up")',
                'button[type="submit"]',
            ]
            
            for selector in signup_selectors:
                try:
                    await page.click(selector, timeout=1000)
                    log_info(f"✓ Sign up button clicked (selector: {selector})")
                    await asyncio.sleep(1)
                    signup_clicked = True
                    break
                except Exception as e:
                    log_debug(f"Sign up selector '{selector}' failed: {e}")
        
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

        account_info = {
            'username': username,
            'password': password,
            'email': email,
            'instance': INSTANCE_ID,
        }
        
        log_info(f"✓ Registered account {username} ({email})")
        return account_info
        
    except Exception as e:
        log_error(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_finger_print_config():
    from camoufox.fingerprints import FingerprintConfig, ScreenConfig
    return FingerprintConfig(
        screen=ScreenConfig(
            width=1920,
            height=1080,
            avail_width=1920,
            avail_height=1040,
            color_depth=24,
            pixel_depth=24,
        ),
        language="en-US,en;q=0.9",
        hardware_concurrency=4,
        device_memory=8,
    )

async def launch_camoufox_browser(proxy_config: dict = None, headless: bool = False):
    """Launch Camoufox browser with optional proxy config
    
    Args:
        proxy_config: Dict with 'server', and optionally 'username' and 'password'
                      e.g. {'server': 'http://host:port', 'username': 'user', 'password': 'pass'}
    """
    try:
        if proxy_config:
            log_info(f"Launching Camoufox with proxy: {proxy_config.get('server', 'unknown')}")
        else:
            log_info("Launching Camoufox without proxy (direct connection)")

        # Build kwargs for Camoufox - only add proxy if provided
        camoufox_kwargs = {
            'headless': headless,
            'geoip': proxy_config is not None,  # Only use geoip with proxy
            'locale': 'en-US',
            'persistent_context': True,
            'user_data_dir': str(CAMOUFOX_USER_DATA_DIR),
            'os': random.choice(['windows', 'linux']),
            'block_images': False,
            'i_know_what_im_doing': True
        }
        
        # Only add proxy config if it's provided and not None
        if proxy_config:
            camoufox_kwargs['proxy'] = proxy_config
        
        camoufox = AsyncCamoufox(**camoufox_kwargs)
        
        browser = await camoufox.start()
        # Get existing page or create one if none exists
        pages = browser.pages
        if pages:
            page = pages[0]
        else:
            page = await browser.new_page()
        return browser, page
    except Exception as e:
        log_error(f"Failed to launch Camoufox browser: {e}")
        raise

async def verify_proxy_connectivity(proxy_url: str) -> bool:
    """Verify that the proxy can reach the outside world."""
    if not proxy_url:
        log_error("Proxy URL missing for connectivity test")
        return False

    proxies = {"http": proxy_url}
    log_info(f"Testing proxy connectivity via {PROXY_TEST_URL}...")

    try:
        def _probe() -> requests.Response:
            return requests.get(PROXY_TEST_URL, proxies=proxies, timeout=10)

        response = await asyncio.to_thread(_probe)
        if response.status_code == 200:
            try:
                data = response.json()
                ip_info = data.get("origin") or data.get("ip")
            except ValueError:
                ip_info = response.text.strip()
            log_info(f"✓ Proxy reachable. Reported IP: {ip_info or 'unknown'}")
            return True

        log_error(f"Proxy check returned status {response.status_code}")
    except Exception as exc:
        log_error(f"Proxy connectivity test failed: {exc}")

    return False

async def browse_warmup_posts(page) -> bool:
    """Browse random Reddit posts before registration to warm up the session."""
    posts_to_visit = random.sample(WARMUP_POSTS, min(WARMUP_POST_COUNT, len(WARMUP_POSTS)))
    
    log_info(f"\n[WARMUP] Browsing {len(posts_to_visit)} posts for {WARMUP_BROWSE_TIME}s each...")
    
    for i, url in enumerate(posts_to_visit, 1):
        try:
            log_info(f"[WARMUP {i}/{len(posts_to_visit)}] Visiting: {url}")
            await page.goto(url, timeout=30000)
            
            # Simulate human browsing behavior
            elapsed = 0
            while elapsed < WARMUP_BROWSE_TIME:
                # Random scroll
                scroll_amount = random.randint(200, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                
                # Random pause between scrolls
                pause = random.uniform(2, 4)
                await asyncio.sleep(pause)
                elapsed += pause
                
                # Sometimes scroll up a bit
                if random.random() < 0.3:
                    await page.evaluate(f"window.scrollBy(0, -{random.randint(50, 150)})")
                    await asyncio.sleep(random.uniform(0.5, 1))
                    elapsed += 1
            
            log_info(f"✓ Finished browsing {url.split('/r/')[1].split('/')[0] if '/r/' in url else url}")
            
        except Exception as e:
            log_error(f"Failed to visit {url}: {e}")
            continue
    
    log_info("[WARMUP] Completed warmup browsing")
    return True


def delete_all_browser_data():
    """Delete all browser data including user-data-dir completely."""
    try:
        if CAMOUFOX_USER_DATA_DIR.exists():
            shutil.rmtree(CAMOUFOX_USER_DATA_DIR)
            log_info(f"✓ Deleted all browser data: {CAMOUFOX_USER_DATA_DIR}")
        
        # Also clean warmed session if exists
        if WARMED_SESSION_DIR.exists():
            shutil.rmtree(WARMED_SESSION_DIR)
            log_info(f"✓ Deleted warmed session: {WARMED_SESSION_DIR}")
            
    except Exception as e:
        log_error(f"Failed to delete browser data: {e}")


async def register_account(proxy_url: str = None, proxy_config: dict = None, headless: bool = False, max_attempts: int = 2) -> Optional[dict]:
    """Create Reddit account with optional proxy and retry logic.
    
    Args:
        proxy_url: Full proxy URL for verification (e.g. http://user:pass@host:port). None for no proxy.
        proxy_config: Camoufox proxy config dict with 'server', 'username', 'password' keys. None for no proxy.
        max_attempts: Number of registration attempts with same browser session
    """
    try:
        # Only verify proxy if one is provided
        if proxy_url:
            proxy_ok = await verify_proxy_connectivity(proxy_url)
            if not proxy_ok:
                log_error("Skipping account attempt due to proxy failure")
                return None
        else:
            log_info("Running without proxy (direct connection)")

        browser, page = await launch_camoufox_browser(proxy_config=proxy_config, headless=headless)
        
        try:
            # Skip IP verification when running without proxy to avoid network issues
            if proxy_url:
                # Verify browser connection by checking IP (only with proxy)
                log_info("Verifying browser proxy connection...")
                try:
                    await page.goto("https://api.ipify.org", timeout=15000)
                    browser_ip = await page.inner_text("body")
                    log_info(f"✓ Browser IP via proxy: {browser_ip.strip()}")
                except Exception as e:
                    log_error(f"Failed to verify proxy IP: {e}")
                    return None
            else:
                log_info("Skipping IP verification (direct connection mode)")
            
            # === WARMUP PHASE - Browse posts before registration ===
            await browse_warmup_posts(page)
            
            # === RETRY LOOP - Try registration multiple times in same browser ===
            for attempt in range(1, max_attempts + 1):
                log_info(f"\n[Registration attempt {attempt}/{max_attempts}]")
                
                try:
                    # === REGISTRATION PHASE ===
                    log_info("Navigating to Reddit post for registration...")
                    await page.goto("https://www.reddit.com/r/StLouis/comments/1ozypnp/north_star_ice_cream_sandwiches/", timeout=60000)
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    # Click comment button to trigger login/signup
                    log_info("Clicking comment button to trigger signup...")
                    await page.locator('[name="comments-action-button"]').click()
                    await asyncio.sleep(random.uniform(2, 4))

                    # Perform registration
                    account_info = await perform_registration_camoufox(page)
                    
                    if account_info:
                        log_info(f"✓ Successfully created account: {account_info['username']}")
                        return account_info
                    else:
                        log_error(f"Registration attempt {attempt}/{max_attempts} failed")
                        
                        if attempt < max_attempts:
                            log_info("Retrying in same browser session...")
                            await page.reload()
                            await asyncio.sleep(2)
                            continue
                
                except Exception as e:
                    log_error(f"Exception in attempt {attempt}/{max_attempts}: {e}")
                    
                    if attempt < max_attempts:
                        log_info("Retrying in same browser session...")
                        try:
                            await page.context.clear_cookies()
                        except Exception:
                            pass
                        await page.goto("about:blank", timeout=5000)
                        await asyncio.sleep(2)
                        continue
            
            # All attempts failed
            log_error(f"All {max_attempts} registration attempts failed")
            return None
                
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            # Delete ALL browser data after registration attempt
            delete_all_browser_data()
        
    except Exception as e:
        log_error(f"Registration error: {e}")
        return None

async def main(): 
    global INSTANCE_ID
    global logger
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Reddit Account Registration')
    parser.add_argument('--instance', type=int, default=1, help='Instance ID (default: 1)')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--no-proxy', action='store_true', help='Run without proxy (direct connection)')
    parser.add_argument('--ssh-host', type=str, default=None, help='SSH server hostname for account uploads')
    parser.add_argument('--ssh-user', type=str, default=None, help='SSH username for account uploads')
    parser.add_argument('--ssh-path', type=str, default=None, help='Remote path for account uploads')
    parser.add_argument('--ssh-key', type=str, default=None, help='Path to SSH private key')
    args = parser.parse_args()
    
    INSTANCE_ID = args.instance
    logger = setup_logging()
    
    # Override SSH config from command line if provided
    global SSH_HOST, SSH_USER, SSH_REMOTE_PATH, SSH_KEY_PATH
    if args.ssh_host:
        SSH_HOST = args.ssh_host
    if args.ssh_user:
        SSH_USER = args.ssh_user
    if args.ssh_path:
        SSH_REMOTE_PATH = args.ssh_path
    if args.ssh_key:
        SSH_KEY_PATH = Path(args.ssh_key)
    
    log_info("=" * 60)
    log_info(f"Reddit Account Registration Service - Instance {INSTANCE_ID}")
    if args.no_proxy:
        log_info(f"Using: Camoufox + Playwright (Direct Connection - No Proxy)")
    else:
        log_info(f"Using: Camoufox + Playwright (Proxy-based)")
    log_info("=" * 60)
    
    # Load proxies from proxy.txt (unless --no-proxy is set)
    all_proxies = []
    bad_proxies = set()
    use_proxy = not args.no_proxy
    
    if use_proxy:
        all_proxies = load_proxies()
        bad_proxies = load_bad_proxies()
        log_info(f"Loaded {len(bad_proxies)} bad proxies to skip")

        if not all_proxies:
            log_error("No proxies found! Please add proxies to proxy.txt")
            log_error("Or use --no-proxy to run without proxies")
            log_error("Format: host:port or host:port:user:password")
            sys.exit(1)
    else:
        log_info("Running in no-proxy mode (direct connection)")

    # Ensure directories exist
    DATA_DIR.mkdir(exist_ok=True)
    
    account_count = 0
    successful_accounts = 0
    
    # Batch tracking
    current_batch_index = get_next_batch_index()
    current_batch_accounts = []  # List of accounts in current batch
    
    log_info(f"Starting account registration loop...")
    log_info(f"Sleep between accounts: {SLEEP_AFTER_ACCOUNT} seconds")
    log_info(f"Create & upload batch every: {UPLOAD_EVERY_N_ACCOUNTS} successful accounts")
    log_info(f"Starting with batch index: {current_batch_index}")
    
    while True:
        proxy_url = None
        proxy_config = None
        current_proxy = None
        
        # Handle proxy mode
        if use_proxy:
            # Get available proxies
            available_proxies = get_available_proxies(all_proxies, bad_proxies)
            
            if not available_proxies:
                log_error("No more proxies available. All have been marked as bad.")
                log_info("Please add more proxies to proxy.txt or clear bad_proxy.txt")
                # Save any remaining accounts before exit
                if current_batch_accounts:
                    log_info(f"Saving {len(current_batch_accounts)} remaining accounts before exit...")
                    create_and_upload_batch(current_batch_accounts, current_batch_index)
                break
            
            current_proxy = random.choice(available_proxies)
            proxy_url = build_proxy_url(current_proxy)
            proxy_config = build_proxy_config(current_proxy)
            log_info(f"\n[PROXY] Testing proxy {current_proxy['host']}:{current_proxy['port']}")
            log_info(f"Available proxies: {len(available_proxies)} / {len(all_proxies)}")
            
            # Test proxy connection
            test_ip = await test_proxy(proxy_url)
            if not test_ip:
                log_error(f"Proxy connection failed; marking as bad")
                bad_proxies = mark_proxy_as_bad(current_proxy['raw'], bad_proxies)
                continue
            
            log_info(f"✓ Proxy working with IP: {test_ip}")

        # Attempt registration (includes 2 retries in same browser session)
        account_count += 1
        log_info(f"\n[ATTEMPT #{account_count}] Creating account...")
        
        try:
            spoof_machine_id()
            copy_warmed_session()
            account_info = await register_account(
                proxy_url=proxy_url, 
                proxy_config=proxy_config, 
                headless=args.headless, 
                max_attempts=2
            )

            if account_info:
                successful_accounts += 1
                log_info(f"✓ Account #{account_count} created successfully! (Total successful: {successful_accounts})")
                log_info(f"  Username: {account_info['username']}")
                log_info(f"  Email: {account_info['email']}")
                
                # Add account to current batch
                current_batch_accounts = save_account_to_batch(account_info, current_batch_accounts)
                log_info(f"  Batch {current_batch_index}: {len(current_batch_accounts)}/{UPLOAD_EVERY_N_ACCOUNTS} accounts")
                
                # Create and upload batch every N successful accounts
                if len(current_batch_accounts) >= UPLOAD_EVERY_N_ACCOUNTS:
                    log_info(f"\n[BATCH] Creating accounts_{current_batch_index}.txt with {len(current_batch_accounts)} accounts...")
                    upload_success = create_and_upload_batch(current_batch_accounts, current_batch_index)
                    
                    if upload_success:
                        log_info(f"✓ Batch {current_batch_index} uploaded successfully!")
                    else:
                        log_error(f"Failed to upload batch {current_batch_index} - file saved locally")
                    
                    # Reset for next batch
                    current_batch_accounts = []
                    current_batch_index += 1
                    log_info(f"Starting new batch: {current_batch_index}")
                
                # Mark proxy as used and rotate (only if using proxies)
                if use_proxy and current_proxy:
                    log_info(f"Registration successful, rotating to next proxy...")
                    bad_proxies = mark_proxy_as_bad(current_proxy['raw'], bad_proxies)
            else:
                log_error(f"Account creation failed after all retries")
                # Mark proxy as bad (only if using proxies)
                if use_proxy and current_proxy:
                    bad_proxies = mark_proxy_as_bad(current_proxy['raw'], bad_proxies)

        except Exception as e:
            log_error(f"Exception in registration: {e}")
            if use_proxy and current_proxy:
                bad_proxies = mark_proxy_as_bad(current_proxy['raw'], bad_proxies)

        log_info(f"Waiting {SLEEP_AFTER_ACCOUNT} seconds before next attempt...")
        await asyncio.sleep(SLEEP_AFTER_ACCOUNT)


if __name__ == "__main__":  
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        sys.exit(0)
