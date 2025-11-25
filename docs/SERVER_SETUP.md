# Linux Server Setup and Security Hardening Guide

Complete guide for setting up a production-grade, highly secure Linux server for Privasee BI SaaS deployment.

## Table of Contents

1. [Recommended Linux Distribution](#recommended-linux-distribution)
2. [Initial Server Setup](#initial-server-setup)
3. [Security Hardening](#security-hardening)
4. [Docker Installation](#docker-installation)
5. [Application Deployment](#application-deployment)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Backup Strategy](#backup-strategy)
8. [Incident Response](#incident-response)

---

## Recommended Linux Distribution

### Primary Recommendation: Ubuntu Server 22.04 LTS

**Why Ubuntu Server 22.04 LTS?**

- Long-term support (5 years of security updates until April 2027)
- Excellent Docker support and documentation
- Large community and extensive package repositories
- APT package manager is straightforward and reliable
- Well-tested for production workloads
- Good balance between stability and modern features

**Alternative Options:**

1. **Debian 12 (Bookworm)** - More conservative, extremely stable
2. **Rocky Linux 9** - RHEL-compatible, enterprise-focused
3. **AlmaLinux 9** - RHEL clone, community-driven
4. **Alpine Linux** - Ultra-lightweight (for containers only, not recommended for host OS)

**NOT Recommended:**

- Ubuntu Desktop (unnecessary GUI overhead)
- CentOS (discontinued)
- Fedora (short support cycle)
- Arch Linux (rolling release, less stable)

---

## Initial Server Setup

### 1. Server Specifications (Minimum for Production)

**Small Deployment (< 100 users):**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 100 GB SSD
- Network: 1 Gbps

**Medium Deployment (100-1000 users):**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 250 GB SSD
- Network: 1 Gbps

**Large Deployment (1000+ users):**
- CPU: 16+ cores
- RAM: 32+ GB
- Storage: 500+ GB SSD (RAID 10 recommended)
- Network: 10 Gbps

### 2. Initial OS Installation

```bash
# After fresh Ubuntu Server 22.04 installation

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ufw \
    fail2ban \
    unattended-upgrades \
    apt-transport-https \
    ca-certificates \
    software-properties-common \
    gnupg \
    lsb-release

# Set timezone
sudo timedatectl set-timezone America/New_York  # Adjust to your timezone
timedatectl status

# Set hostname
sudo hostnamectl set-hostname privasee-prod-01
```

### 3. Create Non-Root User

```bash
# Create deployment user
sudo adduser privasee
sudo usermod -aG sudo privasee

# Set strong password
sudo passwd privasee
```

### 4. SSH Key Setup

**On your local machine:**

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "admin@privasee.com" -f ~/.ssh/privasee_prod

# Copy public key to server
ssh-copy-id -i ~/.ssh/privasee_prod.pub privasee@your-server-ip
```

**On the server:**

```bash
# Set correct permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

---

## Security Hardening

### 1. SSH Hardening

**Edit SSH configuration:**

```bash
sudo vim /etc/ssh/sshd_config
```

**Apply these settings:**

```ini
# Privasee SSH Hardening Configuration

# Disable root login
PermitRootLogin no

# Disable password authentication (keys only)
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no

# Allowed users
AllowUsers privasee

# SSH Protocol
Protocol 2

# Port (change from default 22 to reduce automated attacks)
Port 2222

# Connection settings
ClientAliveInterval 300
ClientAliveCountMax 2
MaxAuthTries 3
MaxSessions 2
LoginGraceTime 60

# Disable forwarding
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no

# Logging
LogLevel VERBOSE
SyslogFacility AUTH

# Host keys
HostKey /etc/ssh/ssh_host_ed25519_key
HostKey /etc/ssh/ssh_host_rsa_key

# Ciphers and algorithms (modern, secure only)
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
```

**Restart SSH:**

```bash
sudo systemctl restart sshd

# Test new configuration BEFORE closing current session
ssh -p 2222 privasee@your-server-ip
```

### 2. Firewall Configuration (UFW)

```bash
# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (use your custom port)
sudo ufw allow 2222/tcp comment 'SSH'

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Allow from trusted IPs only (recommended for admin interfaces)
# sudo ufw allow from 203.0.113.0/24 to any port 9090 comment 'Prometheus from office'

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 3. Fail2Ban Configuration

```bash
# Install Fail2Ban
sudo apt install fail2ban -y

# Create local configuration
sudo vim /etc/fail2ban/jail.local
```

**Add configuration:**

```ini
[DEFAULT]
# Ban time: 1 hour
bantime = 3600

# Find time window: 10 minutes
findtime = 600

# Max retries before ban
maxretry = 3

# Destination email for alerts
destemail = admin@privasee.com
sender = noreply@privasee.com
action = %(action_mwl)s

[sshd]
enabled = true
port = 2222
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/privasee_error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/privasee_error.log
maxretry = 10
findtime = 60
bantime = 3600
```

**Start Fail2Ban:**

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Check status
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

### 4. Kernel Hardening (Sysctl)

```bash
# Edit sysctl configuration
sudo vim /etc/sysctl.d/99-privasee-hardening.conf
```

**Add these settings:**

```ini
# IP Forwarding (disable if not using Docker bridge)
net.ipv4.ip_forward = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Log Martians (packets with impossible addresses)
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_all = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore bogus ICMP errors
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Enable TCP SYN Cookies (DDoS protection)
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_syn_retries = 2
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_max_syn_backlog = 4096

# Enable IP spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# TCP hardening
net.ipv4.tcp_timestamps = 0
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# Increase system file descriptor limit
fs.file-max = 2097152

# Increase network buffer sizes
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864

# Connection tracking
net.netfilter.nf_conntrack_max = 1000000

# Kernel hardening
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
kernel.kexec_load_disabled = 1
```

**Apply settings:**

```bash
sudo sysctl -p /etc/sysctl.d/99-privasee-hardening.conf
```

### 5. Automatic Security Updates

```bash
# Configure unattended upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Edit configuration
sudo vim /etc/apt/apt.conf.d/50unattended-upgrades
```

**Enable security updates:**

```conf
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";
Unattended-Upgrade::Mail "admin@privasee.com";
```

### 6. Disable Unnecessary Services

```bash
# List all services
systemctl list-unit-files --type=service | grep enabled

# Disable unnecessary services (example)
sudo systemctl disable bluetooth.service
sudo systemctl disable avahi-daemon.service
sudo systemctl disable cups.service

# Remove unnecessary packages
sudo apt remove --purge snapd
sudo apt autoremove -y
```

### 7. Install and Configure AppArmor

```bash
# Install AppArmor utilities
sudo apt install apparmor-utils apparmor-profiles apparmor-profiles-extra -y

# Check AppArmor status
sudo aa-status

# Set all profiles to enforce mode
sudo aa-enforce /etc/apparmor.d/*

# Check AppArmor is enabled
sudo systemctl status apparmor
```

### 8. Install and Configure Auditd

```bash
# Install auditd
sudo apt install auditd audispd-plugins -y

# Add audit rules
sudo vim /etc/audit/rules.d/privasee.rules
```

**Add audit rules:**

```bash
# Delete all existing rules
-D

# Buffer size
-b 8192

# Failure mode (0=silent 1=printk 2=panic)
-f 1

# Audit authentication events
-w /var/log/auth.log -p wa -k auth_log
-w /etc/passwd -p wa -k passwd_changes
-w /etc/group -p wa -k group_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/sudoers -p wa -k sudoers_changes

# Audit SSH configuration
-w /etc/ssh/sshd_config -p wa -k sshd_config_changes

# Audit Docker
-w /usr/bin/docker -p wa -k docker_execution
-w /var/lib/docker -p wa -k docker_data

# Audit application files
-w /opt/privasee -p wa -k privasee_app_changes

# Audit network changes
-a always,exit -F arch=b64 -S socket -S connect -k network_connections

# Audit file deletions
-a always,exit -F arch=b64 -S unlink -S unlinkat -S rename -S renameat -k delete

# Make configuration immutable
-e 2
```

**Restart auditd:**

```bash
sudo service auditd restart

# Search audit logs
sudo ausearch -k passwd_changes
sudo ausearch -ts today -k sshd_config_changes
```

### 9. Implement Intrusion Detection (AIDE)

```bash
# Install AIDE
sudo apt install aide -y

# Initialize AIDE database (takes 5-10 minutes)
sudo aideinit

# Move database to proper location
sudo mv /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Run daily checks via cron
sudo crontab -e
```

**Add cron job:**

```bash
# AIDE integrity check daily at 3 AM
0 3 * * * /usr/bin/aide --check | mail -s "AIDE Report for $(hostname)" admin@privasee.com
```

### 10. Secure Shared Memory

```bash
# Edit fstab
sudo vim /etc/fstab
```

**Add line:**

```
tmpfs /run/shm tmpfs defaults,noexec,nosuid,nodev 0 0
```

**Remount:**

```bash
sudo mount -o remount /run/shm
```

### 11. Disable USB Storage (Optional, High Security Environments)

```bash
# Blacklist USB storage modules
sudo vim /etc/modprobe.d/blacklist-usb-storage.conf
```

**Add:**

```
blacklist usb-storage
```

---

## Docker Installation

### 1. Install Docker Engine

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Verify installation
sudo docker --version
sudo docker compose version
```

### 2. Docker Security Hardening

```bash
# Add privasee user to docker group (allows non-root Docker usage)
sudo usermod -aG docker privasee
newgrp docker

# Create Docker daemon configuration
sudo vim /etc/docker/daemon.json
```

**Add secure configuration:**

```json
{
  "icc": false,
  "userns-remap": "default",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp.json",
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

**Restart Docker:**

```bash
sudo systemctl restart docker
sudo systemctl enable docker
```

### 3. Install Docker Bench for Security

```bash
# Clone Docker Bench Security
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security

# Run security audit
sudo sh docker-bench-security.sh
```

---

## Application Deployment

### 1. Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/privasee
sudo chown privasee:privasee /opt/privasee

# Clone repository
cd /opt/privasee
git clone https://github.com/your-org/privasee-bi-saas.git .
```

### 2. Set Up Environment Variables

```bash
# Create production environment file
cp .env.example .env.production

# Edit with secure values
vim .env.production
```

**Generate secure secrets:**

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate strong passwords
openssl rand -base64 32
```

### 3. SSL Certificate Setup (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot -y

# Obtain certificate (standalone mode - run before starting Nginx)
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com --email admin@privasee.com --agree-tos --no-eff-email

# Certificates will be at:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem

# Copy certificates to nginx volume
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/

# Set up auto-renewal
sudo crontab -e
```

**Add cron job:**

```bash
0 3 * * * certbot renew --quiet --deploy-hook "docker exec privasee-nginx nginx -s reload"
```

### 4. Deploy with Docker Compose

```bash
# Build and start all services
docker compose -f docker-compose.production.yml up -d

# Check logs
docker compose -f docker-compose.production.yml logs -f app

# Verify all containers are healthy
docker compose -f docker-compose.production.yml ps
```

### 5. Initialize Application

```bash
# Run database migrations
docker compose -f docker-compose.production.yml exec app alembic upgrade head

# Create admin user (interactive)
docker compose -f docker-compose.production.yml exec app python -c "
from app import create_app
from app.models import User
from app.extensions import db

app = create_app()
with app.app_context():
    admin = User(username='admin', email='admin@privasee.com', role='admin')
    admin.set_password(input('Admin password: '))
    db.session.add(admin)
    db.session.commit()
    print('Admin user created successfully')
"
```

---

## Monitoring and Maintenance

### 1. Log Management

```bash
# Configure log rotation
sudo vim /etc/logrotate.d/privasee
```

**Add:**

```
/opt/privasee/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 privasee privasee
    sharedscripts
    postrotate
        docker compose -f /opt/privasee/docker-compose.production.yml exec app kill -USR1 1
    endscript
}
```

### 2. System Monitoring

```bash
# Install monitoring tools
sudo apt install sysstat iotop nethogs -y

# Enable sysstat
sudo systemctl enable sysstat
sudo systemctl start sysstat

# View system stats
sar -u 1 10   # CPU usage
sar -r 1 10   # Memory usage
sar -n DEV 1 10  # Network usage
```

### 3. Prometheus and Grafana

Access dashboards:

- Prometheus: `https://your-domain.com:9090`
- Grafana: `https://your-domain.com:3000`

Default login:
- Username: admin
- Password: (set via GRAFANA_PASSWORD env var)

### 4. Alerts Configuration

Set up alerts for:

- High CPU usage (> 80%)
- High memory usage (> 90%)
- Disk space low (< 10%)
- High error rate (> 1%)
- Database connection failures
- Container restarts

---

## Backup Strategy

### 1. Automated Database Backups

```bash
# Create backup script
sudo vim /opt/privasee/scripts/backup.sh
```

**Backup script:**

```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/privasee/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# PostgreSQL backup
docker compose -f /opt/privasee/docker-compose.production.yml exec -T db \
    pg_dump -U privasee privasee_users | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# DuckDB backup
docker compose -f /opt/privasee/docker-compose.production.yml exec -T app \
    cp /app/data/analytical_cube.duckdb /backups/duckdb_$DATE.duckdb

# Delete old backups
find "$BACKUP_DIR" -name "postgres_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "duckdb_*.duckdb" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

**Make executable and schedule:**

```bash
chmod +x /opt/privasee/scripts/backup.sh

# Add to crontab
crontab -e
```

**Add:**

```bash
0 2 * * * /opt/privasee/scripts/backup.sh >> /opt/privasee/logs/backup.log 2>&1
```

### 2. Offsite Backup (S3/Wasabi)

```bash
# Install AWS CLI
sudo apt install awscli -y

# Configure AWS credentials
aws configure

# Create sync script
vim /opt/privasee/scripts/sync-to-s3.sh
```

**S3 sync script:**

```bash
#!/bin/bash
aws s3 sync /opt/privasee/backups s3://your-bucket/privasee-backups/ \
    --storage-class STANDARD_IA \
    --exclude "*" \
    --include "*.sql.gz" \
    --include "*.duckdb"
```

---

## Incident Response

### 1. Security Incident Checklist

If you suspect a security breach:

1. **Isolate the server:**
   ```bash
   sudo ufw deny in
   ```

2. **Capture memory dump:**
   ```bash
   sudo dd if=/dev/mem of=/tmp/memory_dump.img bs=1M
   ```

3. **Check for unauthorized access:**
   ```bash
   sudo last
   sudo lastb
   sudo grep -i "failed\|failure\|unauthorized" /var/log/auth.log
   ```

4. **Check running processes:**
   ```bash
   ps aux | grep -v "\[" | sort -k3 -r | head -20
   ```

5. **Check network connections:**
   ```bash
   sudo netstat -tulpn
   sudo ss -tulpn
   ```

6. **Check Docker containers:**
   ```bash
   docker ps -a
   docker inspect <container_id>
   ```

7. **Review audit logs:**
   ```bash
   sudo ausearch -ts today
   ```

8. **Contact security team and preserve evidence**

### 2. Recovery Procedures

**Restore from backup:**

```bash
# Stop application
docker compose -f /opt/privasee/docker-compose.production.yml down

# Restore PostgreSQL
gunzip < /opt/privasee/backups/postgres_YYYYMMDD_HHMMSS.sql.gz | \
    docker compose exec -T db psql -U privasee privasee_users

# Restore DuckDB
docker compose exec app cp /backups/duckdb_YYYYMMDD_HHMMSS.duckdb /app/data/analytical_cube.duckdb

# Restart application
docker compose -f /opt/privasee/docker-compose.production.yml up -d
```

---

## Additional Security Measures

### 1. Two-Factor Authentication for SSH

```bash
# Install Google Authenticator
sudo apt install libpam-google-authenticator -y

# Configure for user
google-authenticator

# Edit PAM configuration
sudo vim /etc/pam.d/sshd
```

**Add:**

```
auth required pam_google_authenticator.so
```

**Edit SSH config:**

```bash
sudo vim /etc/ssh/sshd_config
```

**Add:**

```
ChallengeResponseAuthentication yes
AuthenticationMethods publickey,keyboard-interactive
```

### 2. Implement Web Application Firewall (ModSecurity)

```bash
# Install ModSecurity with Nginx
# This requires compiling Nginx with ModSecurity module
# See: https://github.com/SpiderLabs/ModSecurity-nginx

# Alternatively, use Cloudflare or AWS WAF
```

### 3. DDoS Protection

**CloudFlare (Recommended):**

1. Sign up for Cloudflare
2. Add your domain
3. Update DNS to point to Cloudflare nameservers
4. Enable DDoS protection in Cloudflare dashboard

**AWS Shield (if using AWS):**

1. Enable AWS Shield Standard (free)
2. Consider AWS Shield Advanced for enterprise

### 4. Regular Security Audits

```bash
# Run Lynis security audit
sudo apt install lynis -y
sudo lynis audit system

# Run OpenVAS vulnerability scanner
# Install from: https://www.openvas.org/

# Run Nmap scan (from external machine)
nmap -sV -sC -A your-server-ip
```

---

## Compliance Checklist

- [ ] All services running as non-root users
- [ ] SSH hardened (keys only, no root, custom port)
- [ ] Firewall configured and enabled
- [ ] Fail2Ban active and monitoring
- [ ] Automatic security updates enabled
- [ ] Auditd logging all security events
- [ ] AIDE integrity monitoring enabled
- [ ] SSL/TLS certificates valid and auto-renewing
- [ ] Database backups automated and tested
- [ ] Offsite backups configured
- [ ] Monitoring and alerting active
- [ ] Incident response plan documented
- [ ] Security audit passed (Lynis score > 80)
- [ ] All default passwords changed
- [ ] Docker security hardening applied
- [ ] Log rotation configured
- [ ] Intrusion detection active (AIDE, fail2ban)

---

## Conclusion

This server setup provides enterprise-grade security for the Privasee BI SaaS application. While no system is 100% "unhackeable," this configuration implements defense-in-depth principles with multiple layers of security:

1. **Perimeter Security**: Firewall, fail2ban, rate limiting
2. **Access Control**: SSH hardening, key-based auth, 2FA
3. **System Hardening**: Kernel tuning, service lockdown, AppArmor
4. **Monitoring**: Auditd, AIDE, Prometheus, logging
5. **Incident Response**: Backups, recovery procedures, audit trails
6. **Application Security**: Docker isolation, security headers, HTTPS

Regular maintenance, monitoring, and security updates are critical to maintaining this security posture over time.

**Estimated Setup Time**: 4-6 hours for complete implementation

**Maintenance Time**: 2-4 hours per month

**Security Review**: Quarterly (every 3 months)
