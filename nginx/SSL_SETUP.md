# SSL/TLS Setup Guide

Complete guide for configuring HTTPS with Let's Encrypt certificates.

## Quick Start

### 1. Prerequisites

- Domain name pointing to server IP
- Ports 80 and 443 accessible
- Docker and docker-compose installed
- Nginx container running

### 2. Update Configuration

Edit `nginx/conf.d/privasee.conf` and replace `your-domain.com` with your actual domain:

```nginx
server_name privasee.com;  # Line 39

# SSL paths (lines 43-45)
ssl_certificate /etc/nginx/ssl/live/privasee.com/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/live/privasee.com/privkey.pem;
ssl_trusted_certificate /etc/nginx/ssl/live/privasee.com/chain.pem;
```

### 3. Initialize SSL Certificates

Run the initialization script:

```bash
./scripts/init-letsencrypt.sh privasee.com admin@privasee.com
```

For testing (uses Let's Encrypt staging server):

```bash
./scripts/init-letsencrypt.sh test.privasee.com admin@example.com --staging
```

### 4. Verify HTTPS

Test HTTPS access:

```bash
curl -I https://privasee.com
```

Expected output:
```
HTTP/2 200
server: nginx
strict-transport-security: max-age=63072000; includeSubDomains; preload
```

## Certificate Management

### Automatic Renewal

Certificates are automatically renewed by the certbot container:
- **Frequency:** Every 12 hours
- **Renewal threshold:** 30 days before expiry
- **Post-renewal:** Nginx automatically reloads

Monitor renewal logs:

```bash
docker logs privasee-certbot
```

### Manual Renewal

Force certificate renewal:

```bash
docker-compose -f docker-compose.prod.yml exec certbot certbot renew --force-renewal
```

### View Certificate Details

```bash
docker-compose -f docker-compose.prod.yml run --rm certbot certbot certificates
```

Example output:
```
Certificate Name: privasee.com
  Domains: privasee.com
  Expiry Date: 2025-04-15 12:00:00+00:00 (VALID: 89 days)
  Certificate Path: /etc/letsencrypt/live/privasee.com/fullchain.pem
  Private Key Path: /etc/letsencrypt/live/privasee.com/privkey.pem
```

## Troubleshooting

### Certificate Not Found

**Error:** `SSL: error:02001002:system library:fopen:No such file or directory`

**Solution:**
1. Verify certificate exists:
   ```bash
   docker-compose -f docker-compose.prod.yml exec nginx ls -la /etc/nginx/ssl/live/
   ```

2. If missing, re-run initialization:
   ```bash
   ./scripts/init-letsencrypt.sh your-domain.com admin@your-domain.com
   ```

### Nginx Fails to Reload

**Error:** `nginx: [emerg] cannot load certificate`

**Solution:**
Check nginx logs:
```bash
docker-compose -f docker-compose.prod.yml logs nginx
```

Verify certificate paths in configuration match your domain.

### Rate Limit Exceeded

**Error:** `too many certificates already issued for: your-domain.com`

**Solution:**
Let's Encrypt has rate limits (50 certificates/week per domain).

For testing, use staging server:
```bash
./scripts/init-letsencrypt.sh test.example.com admin@example.com --staging
```

Wait 7 days for rate limit to reset for production certificates.

### Domain Validation Failed

**Error:** `Timeout during connect (likely firewall problem)`

**Solution:**
1. Verify port 80 is accessible:
   ```bash
   curl http://your-domain.com/.well-known/acme-challenge/test
   ```

2. Check firewall rules:
   ```bash
   sudo firewall-cmd --list-all
   ```

3. Ensure nginx is proxying ACME challenges (already configured in privasee.conf).

## Security Best Practices

### HSTS Preload

Submit domain to HSTS preload list:
https://hstspreload.org/

Requirements:
- HSTS header with `preload` directive (already configured)
- Valid HTTPS certificate
- Redirect HTTP to HTTPS (already configured)
- HTTPS works on all subdomains

### Certificate Transparency Monitoring

Monitor certificate issuance:
- https://crt.sh/?q=your-domain.com
- Alerts you to unauthorized certificate issuance

### TLS Configuration Test

Test SSL/TLS configuration:
```bash
docker run --rm -it nmap/nmap --script ssl-enum-ciphers -p 443 your-domain.com
```

Or use online tools:
- https://www.ssllabs.com/ssltest/
- https://securityheaders.com/

Expected rating: **A+**

## Advanced Configuration

### Multiple Domains

To add additional domains:

1. Update `server_name` in nginx configuration:
   ```nginx
   server_name privasee.com www.privasee.com api.privasee.com;
   ```

2. Request multi-domain certificate:
   ```bash
   docker-compose -f docker-compose.prod.yml run --rm certbot \
     certonly --webroot --webroot-path=/var/www/certbot \
     --email admin@privasee.com \
     --agree-tos \
     -d privasee.com \
     -d www.privasee.com \
     -d api.privasee.com
   ```

### Wildcard Certificates

Wildcard certificates require DNS validation (not supported with webroot):

```bash
docker-compose -f docker-compose.prod.yml run --rm certbot \
  certonly --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  --email admin@privasee.com \
  --agree-tos \
  -d privasee.com \
  -d *.privasee.com
```

Requires Cloudflare API token in `cloudflare.ini`.

### Custom Renewal Script

Create custom post-renewal script:

```bash
#!/bin/bash
# /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

docker-compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload
echo "$(date): Nginx reloaded after certificate renewal" >> /var/log/cert-renewal.log
```

Make executable:
```bash
chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

## Certificate Lifecycle

```
Day 0:    Certificate issued (valid for 90 days)
Day 60:   Certbot begins attempting renewal (30 days before expiry)
Day 89:   Last day before expiry
Day 90:   Certificate expires (if not renewed)
```

Renewal attempts occur **twice daily** at random times.

## References

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot User Guide](https://eff-certbot.readthedocs.io/)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
