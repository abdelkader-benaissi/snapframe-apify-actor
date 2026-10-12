"""Snapframe actor: capture website screenshots (PNG/JPEG) and print-ready PDFs.

Each public URL is loaded in a real headless Chromium browser and captured.
Pay-per-event charges are emitted only for successful captures, right after the
file is stored and before the dataset item is pushed.
"""

import asyncio
import ipaddress
import os
import re
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from apify import Actor
from playwright.async_api import async_playwright

EVENT_SCREENSHOT = 'screenshot-captured'
EVENT_PDF = 'pdf-captured'

DEVICE_PRESETS = {
    'desktop': {'width': 1920, 'height': 1080, 'scale': 1},
    'laptop': {'width': 1366, 'height': 768, 'scale': 1},
    'tablet': {'width': 768, 'height': 1024, 'scale': 2},
    'mobile': {'width': 390, 'height': 844, 'scale': 3},
}

CONTENT_TYPES = {'png': 'image/png', 'jpeg': 'image/jpeg', 'pdf': 'application/pdf'}


def check_public_url(url: str) -> tuple[bool, str]:
    """SSRF guard: only allow http(s) URLs that resolve to public IPs."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, 'malformed URL'
    if parsed.scheme not in ('http', 'https'):
        return False, f"unsupported scheme '{parsed.scheme}' (only http/https allowed)"
    host = parsed.hostname
    if not host:
        return False, 'missing hostname'
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False, 'DNS resolution failed'
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False, 'unparseable resolved address'
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast \
                or ip.is_reserved or ip.is_unspecified:
            return False, f'blocked: {host} resolves to non-public IP {ip}'
    return True, ''


def slugify(url: str) -> str:
    parsed = urlparse(url)
    base = (parsed.hostname or 'page') + parsed.path.rstrip('/')
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', base).strip('-').lower()
    return (slug or 'page')[:80]


async def charge_event(event_name: str) -> None:
    """Bill one pay-per-event charge. Never let billing break the run."""
    try:
        await Actor.charge(event_name=event_name)
    except Exception as exc:  # noqa: BLE001 - billing must not crash captures
        Actor.log.warning(f'Pay-per-event charge {event_name!r} failed: {exc}')


def resolve_viewport(cfg: dict) -> tuple[int, int, float]:
    preset = cfg.get('devicePreset', 'desktop')
    if preset in DEVICE_PRESETS:
        p = DEVICE_PRESETS[preset]
        return p['width'], p['height'], p['scale']
    return (
        int(cfg.get('viewportWidth', 1920)),
        int(cfg.get('viewportHeight', 1080)),
        float(cfg.get('deviceScaleFactor', 1)),
    )


async def file_url(store, key: str) -> str | None:
    """Direct download URL for a stored file, or None when unavailable."""
    try:
        return await store.get_public_url(key)
    except Exception:  # noqa: BLE001
        pass
    store_id = getattr(store, 'id', None) or os.environ.get('APIFY_DEFAULT_KEY_VALUE_STORE_ID')
    if not store_id:
        return None
    base = os.environ.get('APIFY_API_BASE_URL', 'https://api.apify.com')
    return f'{base}/v2/key-value-stores/{store_id}/records/{key}'


async def capture_url(page, url: str, index: int, cfg: dict, store) -> dict:
    """Capture one URL. Returns the dataset item (ok or failed)."""
    started = time.monotonic()
    ok, reason = check_public_url(url)
    if not ok:
        Actor.log.warning(f'Skipping {url}: {reason}')
        return {'url': url, 'ok': False, 'reason': reason}

    output_format = cfg.get('outputFormat', 'png')
    timeout_ms = int(cfg.get('timeoutMs', 60000))
    try:
        response = await page.goto(
            url,
            wait_until=cfg.get('waitUntil', 'networkidle'),
            timeout=timeout_ms,
        )
        delay_ms = int(cfg.get('delayMs', 1000))
        if delay_ms:
            await page.wait_for_timeout(delay_ms)

        ext = output_format
        key = f'{index:04d}-{slugify(url)}.{ext}'

        if output_format == 'pdf':
            margin = str(cfg.get('pdfMargin', '0.4in'))
            buffer = await page.pdf(
                format=str(cfg.get('pdfFormat', 'A4')),
                landscape=bool(cfg.get('pdfLandscape', False)),
                print_background=bool(cfg.get('printBackground', True)),
                margin={'top': margin, 'right': margin, 'bottom': margin, 'left': margin},
                display_header_footer=bool(cfg.get('displayHeaderFooter', False)),
                header_template=str(cfg.get('headerTemplate', '') or ''),
                footer_template=str(cfg.get('footerTemplate', '') or ''),
            )
            event_name = EVENT_PDF
        else:
            shot_kwargs = {
                'full_page': bool(cfg.get('fullPage', True)),
                'type': 'jpeg' if output_format == 'jpeg' else 'png',
            }
            if output_format == 'jpeg':
                shot_kwargs['quality'] = int(cfg.get('jpegQuality', 85))
            buffer = await page.screenshot(**shot_kwargs)
            event_name = EVENT_SCREENSHOT

        await Actor.set_value(key, buffer, content_type=CONTENT_TYPES[output_format])

        # Charge only for successful captures, before the dataset push.
        await charge_event(event_name)

        title = ''
        try:
            title = await page.title()
        except Exception:  # noqa: BLE001
            pass

        item = {
            'url': url,
            'ok': True,
            'outputFormat': output_format,
            'fileName': key,
            'fileUrl': await file_url(store, key),
            'bytes': len(buffer),
            'title': title,
            'statusCode': response.status if response else None,
            'loadTimeMs': int((time.monotonic() - started) * 1000),
        }
        Actor.log.info(f'Captured {url} -> {key} ({len(buffer)} bytes)')
        return item
    except Exception as exc:  # noqa: BLE001 - one bad URL must not kill the batch
        reason = f'{type(exc).__name__}: {exc}'
        Actor.log.warning(f'Failed {url}: {reason}')
        return {
            'url': url,
            'ok': False,
            'reason': reason,
            'loadTimeMs': int((time.monotonic() - started) * 1000),
        }


async def main() -> None:
    async with Actor:
        cfg = await Actor.get_input() or {}
        urls = [u.strip() for u in cfg.get('urls', []) if isinstance(u, str) and u.strip()]
        if not urls:
            raise ValueError('Provide at least one URL in "urls".')
        urls = urls[:50]

        width, height, scale = resolve_viewport(cfg)
        headers = cfg.get('headers') or {}
        cookies = cfg.get('cookies') or []

        store = await Actor.open_key_value_store()

        succeeded = 0
        async with async_playwright() as pw:
            launch_kwargs: dict = {
                'headless': True,
                'args': ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            }
            # Respect standard proxy env vars (corporate egress, test sandboxes).
            # Apify's own proxy product is configured per run via ProxyConfiguration,
            # which is separate; this only applies when the env explicitly sets one.
            proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
            if proxy_url:
                proxy_cfg: dict = {'server': proxy_url}
                bypass = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
                if bypass:
                    proxy_cfg['bypass'] = bypass
                launch_kwargs['proxy'] = proxy_cfg
                Actor.log.info('Using egress proxy from HTTPS_PROXY.')
            browser = await pw.chromium.launch(**launch_kwargs)
            try:
                context = await browser.new_context(
                    viewport={'width': width, 'height': height},
                    device_scale_factor=scale,
                    extra_http_headers=headers or None,
                )
                if cookies:
                    await context.add_cookies(cookies)
                page = await context.new_page()
                for index, url in enumerate(urls):
                    item = await capture_url(page, url, index, cfg, store)
                    await Actor.push_data(item)
                    if item.get('ok'):
                        succeeded += 1
                await context.close()
            finally:
                await browser.close()

        summary = {
            'total': len(urls),
            'succeeded': succeeded,
            'failed': len(urls) - succeeded,
            'outputFormat': cfg.get('outputFormat', 'png'),
            'finishedAt': datetime.now(timezone.utc).isoformat(),
        }
        await Actor.set_value('OUTPUT', summary)
        Actor.log.info(f"Done: {succeeded}/{len(urls)} captures succeeded.")
