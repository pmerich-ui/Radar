"""Read-only, feed-independent Awin joined-merchant discovery.

This does NOT prove product availability, prices, Swiss delivery, permission to
reuse images, affiliate deep-link attribution or commission rates. It does not
publish anything or expose API credentials or tracking URLs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

MAX_BODY_BYTES = 5 * 1024 * 1024
MAX_PROGRAMMES = 2000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _read_json(path: str):
    # Callers supply only the two fixed Awin routes. Never follow redirects,
    # which could otherwise leak the bearer token to a different host.
    if not (path == '/accounts?type=publisher' or
            re.fullmatch(r'/publishers/[0-9]+/programmes\?relationship=joined', path)):
        raise ValueError('AWIN_API_ROUTE_INVALID')
    token = os.environ.get('AWIN_API_TOKEN', '').strip()
    if not token:
        raise ValueError('AWIN_API_TOKEN_MISSING')
    request = Request('https://api.awin.com' + path, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
        'User-Agent': 'DealRadar-JoinedMerchantFallback/1.0',
    }, method='GET')
    opener = build_opener(HTTPSHandler(), NoRedirect())
    with opener.open(request, timeout=25) as response:
        raw = response.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        raise ValueError('AWIN_API_RESPONSE_TOO_LARGE')
    return json.loads(raw)


def _clean(value, limit=100):
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return ''
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(value)).strip()[:limit]


def discover(read_json=_read_json):
    if not os.environ.get('AWIN_API_TOKEN', '').strip():
        return {'status': 'BLOCKED', 'reason': 'AWIN_API_TOKEN_MISSING',
                'publishable_deals': 0, 'publishing_enabled': False}
    try:
        accounts = read_json('/accounts?type=publisher')
        if isinstance(accounts, dict):
            accounts = accounts.get('accounts')
        if not isinstance(accounts, list):
            raise ValueError('UNEXPECTED_ACCOUNTS_RESPONSE')
        publishers = [a for a in accounts if isinstance(a, dict)
                      and a.get('accountType') == 'publisher'
                      and str(a.get('accountId', '')).isdigit()]
        if len(publishers) != 1:
            raise ValueError('EXPECTED_ONE_PUBLISHER')
        publisher_id = str(publishers[0]['accountId'])
        programmes = read_json('/publishers/' + publisher_id + '/programmes?relationship=joined')
        if isinstance(programmes, dict):
            programmes = programmes.get('programmes')
        if not isinstance(programmes, list) or len(programmes) > MAX_PROGRAMMES or not all(
                isinstance(p, dict) for p in programmes):
            raise ValueError('UNEXPECTED_PROGRAMMES_RESPONSE')
        merchants = []
        for p in programmes:
            merchants.append({
                'advertiser_id': _clean(p.get('id') or p.get('advertiserId'), 24),
                'name': _clean(p.get('name') or p.get('advertiserName')),
                'region_hint': _clean(p.get('primaryRegion'), 40),
                'sector_hint': _clean(p.get('primarySector'), 60),
                'status_hint': _clean(p.get('status'), 40),
                'clickthrough_metadata_present': bool(p.get('clickThroughUrl')),
            })
        merchants.sort(key=lambda m: (m['region_hint'].upper() not in ('CH', 'CHE', 'SWITZERLAND', 'SCHWEIZ'), m['name'].casefold()))
        return {
            'status': 'COMPLETED', 'reason': 'JOINED_MERCHANT_METADATA_ONLY',
            'joined_merchants': len(merchants), 'merchants': merchants,
            'publishable_deals': 0, 'publishing_enabled': False,
            'verification_pending': ['product_price', 'Swiss_shipping', 'affiliate_attribution',
                                     'image_usage_rights', 'advertising_claims', 'commission_terms'],
        }
    except Exception as exc:
        # Never expose the exception text: URLs, headers or account identifiers
        # may be included by upstream libraries. Only allow known business codes.
        reason = str(exc) if isinstance(exc, ValueError) and str(exc) in {
            'UNEXPECTED_ACCOUNTS_RESPONSE', 'EXPECTED_ONE_PUBLISHER',
            'UNEXPECTED_PROGRAMMES_RESPONSE', 'AWIN_API_ROUTE_INVALID',
            'AWIN_API_RESPONSE_TOO_LARGE', 'AWIN_API_TOKEN_MISSING'} else 'AWIN_API_READ_FAILED'
        return {'status': 'BLOCKED', 'reason': reason,
                'publishable_deals': 0, 'publishing_enabled': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='reports/awin_api_fallback.json')
    args = parser.parse_args()
    result = discover()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'reason', 'publishable_deals', 'publishing_enabled')}))
    return 0 if result['status'] == 'COMPLETED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
