"""
SSL Certificate Automation

Automatic SSL certificate generation and renewal using Let's Encrypt.
"""

import subprocess
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SSLCertificate:
    """SSL certificate information."""
    domain: str
    issuer: str
    valid_from: datetime
    valid_until: datetime
    path: str
    key_path: str
    
    @property
    def days_remaining(self) -> int:
        """Days until certificate expires."""
        return (self.valid_until - datetime.utcnow()).days
    
    @property
    def is_valid(self) -> bool:
        """Check if certificate is currently valid."""
        now = datetime.utcnow()
        return self.valid_from <= now <= self.valid_until
    
    @property
    def needs_renewal(self) -> bool:
        """Check if certificate needs renewal (< 30 days)."""
        return self.days_remaining < 30


class SSLManager:
    """
    Manage SSL certificates for deployed applications.
    
    Supports:
    - Let's Encrypt (certbot)
    - Self-signed certificates for development
    - Certificate status checking
    - Automatic renewal
    """
    
    def __init__(self, cert_dir: str = "/etc/letsencrypt/live"):
        self.cert_dir = Path(cert_dir)
        self.renewal_threshold_days = 30
    
    def generate_certificate(
        self,
        domain: str,
        email: str,
        staging: bool = False,
        webroot: str = None,
    ) -> Tuple[bool, str]:
        """
        Generate SSL certificate using Let's Encrypt.
        
        Args:
            domain: Domain to generate certificate for
            email: Email for Let's Encrypt notifications
            staging: Use staging server (for testing)
            webroot: Webroot path for HTTP validation
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = [
                "certbot", "certonly",
                "--non-interactive",
                "--agree-tos",
                "--email", email,
                "-d", domain,
            ]
            
            if staging:
                cmd.append("--staging")
            
            if webroot:
                cmd.extend(["--webroot", "-w", webroot])
            else:
                cmd.append("--standalone")
            
            logger.info(f"Generating SSL certificate for {domain}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"SSL certificate generated for {domain}")
                return True, f"Certificate generated for {domain}"
            else:
                logger.error(f"Failed to generate certificate: {result.stderr}")
                return False, result.stderr
                
        except FileNotFoundError:
            return False, "certbot not installed. Install with: apt install certbot"
        except Exception as e:
            logger.error(f"SSL generation error: {e}")
            return False, str(e)
    
    def generate_self_signed(
        self,
        domain: str,
        output_dir: str,
        days: int = 365,
    ) -> Tuple[bool, str]:
        """
        Generate self-signed certificate for development.
        
        Args:
            domain: Domain for certificate
            output_dir: Directory to store certificate files
            days: Validity period in days
            
        Returns:
            Tuple of (success, message)
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            key_path = output_path / "privkey.pem"
            cert_path = output_path / "fullchain.pem"
            
            # Generate private key
            subprocess.run([
                "openssl", "genrsa",
                "-out", str(key_path),
                "2048"
            ], check=True, capture_output=True)
            
            # Generate self-signed certificate
            subprocess.run([
                "openssl", "req",
                "-new", "-x509",
                "-key", str(key_path),
                "-out", str(cert_path),
                "-days", str(days),
                "-subj", f"/CN={domain}"
            ], check=True, capture_output=True)
            
            logger.info(f"Self-signed certificate generated for {domain}")
            return True, f"Self-signed certificate generated at {output_path}"
            
        except subprocess.CalledProcessError as e:
            return False, f"OpenSSL error: {e.stderr}"
        except Exception as e:
            return False, str(e)
    
    def get_certificate_info(self, domain: str) -> Optional[SSLCertificate]:
        """
        Get information about an existing certificate.
        
        Args:
            domain: Domain to check
            
        Returns:
            SSLCertificate info or None if not found
        """
        cert_path = self.cert_dir / domain / "fullchain.pem"
        key_path = self.cert_dir / domain / "privkey.pem"
        
        if not cert_path.exists():
            return None
        
        try:
            result = subprocess.run([
                "openssl", "x509",
                "-in", str(cert_path),
                "-noout",
                "-dates",
                "-issuer"
            ], capture_output=True, text=True, check=True)
            
            # Parse output
            lines = result.stdout.strip().split("\n")
            issuer = ""
            valid_from = None
            valid_until = None
            
            for line in lines:
                if line.startswith("issuer="):
                    issuer = line.split("=", 1)[1]
                elif line.startswith("notBefore="):
                    date_str = line.split("=", 1)[1]
                    valid_from = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                elif line.startswith("notAfter="):
                    date_str = line.split("=", 1)[1]
                    valid_until = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            
            return SSLCertificate(
                domain=domain,
                issuer=issuer,
                valid_from=valid_from,
                valid_until=valid_until,
                path=str(cert_path),
                key_path=str(key_path),
            )
            
        except Exception as e:
            logger.error(f"Error reading certificate for {domain}: {e}")
            return None
    
    def renew_certificate(self, domain: str = None) -> Tuple[bool, str]:
        """
        Renew SSL certificates.
        
        Args:
            domain: Specific domain to renew, or None for all
            
        Returns:
            Tuple of (success, message)
        """
        try:
            cmd = ["certbot", "renew", "--non-interactive"]
            
            if domain:
                cmd.extend(["--cert-name", domain])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Certificate renewal completed")
                return True, "Certificates renewed successfully"
            else:
                return False, result.stderr
                
        except FileNotFoundError:
            return False, "certbot not installed"
        except Exception as e:
            return False, str(e)
    
    def check_all_certificates(self) -> List[Dict]:
        """
        Check status of all certificates.
        
        Returns:
            List of certificate status dictionaries
        """
        results = []
        
        if not self.cert_dir.exists():
            return results
        
        for domain_dir in self.cert_dir.iterdir():
            if domain_dir.is_dir():
                cert_info = self.get_certificate_info(domain_dir.name)
                if cert_info:
                    results.append({
                        "domain": cert_info.domain,
                        "valid": cert_info.is_valid,
                        "days_remaining": cert_info.days_remaining,
                        "needs_renewal": cert_info.needs_renewal,
                        "issuer": cert_info.issuer,
                        "expires": cert_info.valid_until.isoformat(),
                    })
        
        return results
    
    def setup_auto_renewal(self) -> Tuple[bool, str]:
        """
        Setup automatic certificate renewal via cron.
        
        Returns:
            Tuple of (success, message)
        """
        cron_job = "0 0,12 * * * certbot renew --quiet --post-hook 'nginx -s reload'"
        cron_file = "/etc/cron.d/certbot-renew"
        
        try:
            with open(cron_file, "w") as f:
                f.write(f"# Auto-generated by LaunchForge\n{cron_job}\n")
            
            logger.info("Auto-renewal cron job configured")
            return True, f"Auto-renewal configured in {cron_file}"
            
        except PermissionError:
            return False, "Permission denied. Run with sudo."
        except Exception as e:
            return False, str(e)


# Convenience functions
def generate_ssl(domain: str, email: str, staging: bool = False) -> Tuple[bool, str]:
    """Generate SSL certificate for a domain."""
    manager = SSLManager()
    return manager.generate_certificate(domain, email, staging)


def check_ssl(domain: str) -> Optional[Dict]:
    """Check SSL certificate status for a domain."""
    manager = SSLManager()
    cert = manager.get_certificate_info(domain)
    if cert:
        return {
            "domain": cert.domain,
            "valid": cert.is_valid,
            "days_remaining": cert.days_remaining,
            "needs_renewal": cert.needs_renewal,
        }
    return None


def renew_all_ssl() -> Tuple[bool, str]:
    """Renew all SSL certificates."""
    manager = SSLManager()
    return manager.renew_certificate()
