import os
import httpx
from typing import Dict, List, Optional

class DomainService:
    """Domain registration and DNS management service."""
    
    def __init__(self):
        self.namecheap_api_key = os.environ.get('NAMECHEAP_API_KEY')
        self.namecheap_user = os.environ.get('NAMECHEAP_USER')
        self.cloudflare_token = os.environ.get('CLOUDFLARE_API_TOKEN')
        self.cloudflare_api = 'https://api.cloudflare.com/client/v4'
    
    async def check_domain_availability(self, domain: str) -> Dict:
        """Check if a domain is available."""
        try:
            # Use Cloudflare's domain check or fallback to DNS lookup
            async with httpx.AsyncClient() as client:
                # Try a simple DNS lookup to check availability
                import socket
                try:
                    socket.gethostbyname(domain)
                    return {'available': False, 'domain': domain, 'message': 'Domain is already registered'}
                except socket.gaierror:
                    return {'available': True, 'domain': domain, 'message': 'Domain appears to be available'}
        except Exception as e:
            return {'available': None, 'domain': domain, 'error': str(e)}
    
    async def suggest_domains(self, business_name: str) -> List[Dict]:
        """Suggest available domain names based on business name."""
        import re
        # Clean the business name
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
        
        suggestions = []
        tlds = ['.com', '.io', '.co', '.app', '.dev', '.tech', '.ai']
        prefixes = ['', 'get', 'try', 'use', 'my']
        suffixes = ['', 'app', 'hq', 'io']
        
        for tld in tlds:
            for prefix in prefixes:
                for suffix in suffixes:
                    domain = f"{prefix}{clean_name}{suffix}{tld}"
                    if domain not in [s['domain'] for s in suggestions]:
                        suggestions.append({
                            'domain': domain,
                            'estimated_price': self._estimate_price(tld)
                        })
        
        return suggestions[:20]  # Return top 20 suggestions
    
    def _estimate_price(self, tld: str) -> float:
        """Estimate domain price based on TLD."""
        prices = {
            '.com': 12.99,
            '.io': 39.99,
            '.co': 29.99,
            '.app': 14.99,
            '.dev': 12.99,
            '.tech': 9.99,
            '.ai': 79.99
        }
        return prices.get(tld, 19.99)
    
    async def setup_cloudflare_dns(self, domain: str, target_ip: str = None, cname_target: str = None) -> Dict:
        """Set up Cloudflare DNS for a domain."""
        if not self.cloudflare_token:
            return {'success': False, 'error': 'Cloudflare not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                # First, get or create the zone
                zone_response = await client.post(
                    f'{self.cloudflare_api}/zones',
                    headers={
                        'Authorization': f'Bearer {self.cloudflare_token}',
                        'Content-Type': 'application/json'
                    },
                    json={'name': domain, 'jump_start': True}
                )
                
                if zone_response.status_code in [200, 201]:
                    zone_data = zone_response.json()
                    zone_id = zone_data['result']['id']
                    
                    # Add DNS records
                    records = []
                    
                    if cname_target:
                        # Add CNAME record for Railway/Vercel
                        record_response = await client.post(
                            f'{self.cloudflare_api}/zones/{zone_id}/dns_records',
                            headers={
                                'Authorization': f'Bearer {self.cloudflare_token}',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'type': 'CNAME',
                                'name': '@',
                                'content': cname_target,
                                'proxied': True
                            }
                        )
                        records.append(record_response.json())
                    
                    if target_ip:
                        # Add A record
                        record_response = await client.post(
                            f'{self.cloudflare_api}/zones/{zone_id}/dns_records',
                            headers={
                                'Authorization': f'Bearer {self.cloudflare_token}',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'type': 'A',
                                'name': '@',
                                'content': target_ip,
                                'proxied': True
                            }
                        )
                        records.append(record_response.json())
                    
                    return {
                        'success': True,
                        'zone_id': zone_id,
                        'nameservers': zone_data['result'].get('name_servers', []),
                        'records': records
                    }
                
                return {'success': False, 'error': zone_response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def configure_ssl(self, zone_id: str) -> Dict:
        """Enable SSL for a Cloudflare zone."""
        if not self.cloudflare_token:
            return {'success': False, 'error': 'Cloudflare not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f'{self.cloudflare_api}/zones/{zone_id}/settings/ssl',
                    headers={
                        'Authorization': f'Bearer {self.cloudflare_token}',
                        'Content-Type': 'application/json'
                    },
                    json={'value': 'full'}
                )
                
                return {'success': response.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_dns_records(self, zone_id: str) -> Dict:
        """Get all DNS records for a zone."""
        if not self.cloudflare_token:
            return {'success': False, 'error': 'Cloudflare not configured'}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'{self.cloudflare_api}/zones/{zone_id}/dns_records',
                    headers={
                        'Authorization': f'Bearer {self.cloudflare_token}'
                    }
                )
                
                if response.status_code == 200:
                    return {'success': True, 'records': response.json()['result']}
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
