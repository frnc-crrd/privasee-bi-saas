# Cloudflare Turnstile Setup Guide

Free, user-friendly bot protection for authentication endpoints without traditional CAPTCHA friction.

## Overview

Cloudflare Turnstile provides invisible bot detection that:
- Runs silently in the background (no user interaction in 99% of cases)
- Blocks automated attacks (account creation, login brute force, password reset spam)
- Works seamlessly across devices and browsers
- **Completely free** (unlimited requests)
- Privacy-focused (no user tracking)

Unlike traditional CAPTCHA, Turnstile rarely challenges legitimate users, improving UX while maintaining strong security.

## Quick Start

### 1. Get Turnstile Keys

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to **Turnstile** section
3. Click **Add Site**
4. Configure:
   - **Site name**: Privasee BI SaaS
   - **Domain**: your-domain.com (or localhost for testing)
   - **Widget mode**: Managed (recommended)
5. Copy keys:
   - **Site Key** (public, for frontend)
   - **Secret Key** (private, for backend)

### 2. Configure Environment Variables

Update `.env.production`:

```bash
# Cloudflare Turnstile
TURNSTILE_ENABLED=true
TURNSTILE_SITE_KEY=0x4AAAAAAA...  # From Cloudflare dashboard
TURNSTILE_SECRET_KEY=0x4AAAAAAA...  # From Cloudflare dashboard
```

For development (skip verification):

```bash
# .env (development)
TURNSTILE_ENABLED=false
TURNSTILE_SITE_KEY=  # Not required when disabled
TURNSTILE_SECRET_KEY=
```

### 3. Frontend Integration

Turnstile is currently configured for **backend verification only**. Frontend integration is required for production use.

#### HTML Form Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
</head>
<body>
    <form id="loginForm" action="/api/v1/auth/login" method="POST">
        <input type="email" name="email" placeholder="Email" required>
        <input type="password" name="password" placeholder="Password" required>

        <!-- Turnstile widget (invisible, renders automatically) -->
        <div class="cf-turnstile"
             data-sitekey="your-site-key-here"
             data-callback="onTurnstileSuccess"></div>

        <button type="submit">Login</button>
    </form>

    <script>
        function onTurnstileSuccess(token) {
            // Token automatically added to form submission
            console.log('Turnstile verified');
        }

        // Submit form with Turnstile token
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const turnstileToken = document.querySelector('[name="cf-turnstile-response"]').value;

            const payload = {
                email: formData.get('email'),
                password: formData.get('password'),
                'cf-turnstile-response': turnstileToken
            };

            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            // Handle response...
        });
    </script>
</body>
</html>
```

#### React/JavaScript Example

```javascript
import { useRef, useEffect } from 'react';

function LoginForm() {
  const turnstileRef = useRef(null);
  const [turnstileToken, setTurnstileToken] = useState('');

  useEffect(() => {
    // Load Turnstile script
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    document.body.appendChild(script);

    script.onload = () => {
      window.turnstile.render(turnstileRef.current, {
        sitekey: 'your-site-key-here',
        callback: (token) => setTurnstileToken(token),
      });
    };

    return () => document.body.removeChild(script);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        email: email,
        password: password,
        'cf-turnstile-response': turnstileToken
      })
    });

    // Handle response...
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="email" name="email" required />
      <input type="password" name="password" required />
      <div ref={turnstileRef}></div>
      <button type="submit">Login</button>
    </form>
  );
}
```

### 4. Test Integration

#### Development Testing (Turnstile Disabled)

```bash
# Login without Turnstile token (accepted in dev mode)
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}'

# Expected: 200 OK (verification skipped)
```

#### Production Testing (Turnstile Enabled)

```bash
# Login without token (rejected)
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}'

# Expected: 403 Forbidden
# {"success": false, "message": "Verification failed. Please try again."}

# Login with valid token (accepted)
curl -X POST https://your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"admin@example.com",
    "password":"password",
    "cf-turnstile-response":"<token-from-widget>"
  }'

# Expected: 200 OK with JWT tokens
```

## Protected Endpoints

The following endpoints require Turnstile verification in production:

| Endpoint                       | Method | Token Required | Rate Limit   |
|--------------------------------|--------|----------------|--------------|
| `/api/v1/auth/login`           | POST   | Yes            | 5/minute     |
| `/api/v1/auth/register`        | POST   | Yes            | 10/hour      |
| `/api/v1/auth/password/reset-request` | POST | Yes      | 3/hour       |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                        │
├─────────────────────────────────────────────────────────────────┤
│  1. User visits login page                                      │
│  2. Turnstile widget loads and challenges user (if suspicious)  │
│  3. User solves challenge (or auto-passes if legitimate)        │
│  4. Widget generates token                                      │
│  5. Form submitted with token in 'cf-turnstile-response' field  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ├─ HTTP POST with token
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Nginx (Reverse Proxy)                         │
├─────────────────────────────────────────────────────────────────┤
│  - Extract real IP (X-Real-IP, X-Forwarded-For)                │
│  - Rate limiting                                                 │
│  - Forward request to Flask                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Application                            │
├─────────────────────────────────────────────────────────────────┤
│  @require_turnstile_json()  ◄─ Decorator extracts token        │
│  TurnstileService.verify_token() ◄─ Verifies with Cloudflare   │
│  - POST to siteverify endpoint                                  │
│  - Send: secret, token, remoteip                                │
│  - Receive: {success: true/false, error-codes: [...]}          │
│  - Log verification attempt                                     │
│  - Return 403 if failed, or proceed if success                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ├─ HTTPS POST to Cloudflare
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│          Cloudflare Turnstile Verification API                  │
├─────────────────────────────────────────────────────────────────┤
│  - Validate token signature                                     │
│  - Check token expiration (5 minutes)                           │
│  - Verify token hasn't been used before                        │
│  - Analyze request patterns                                     │
│  - Return success/failure                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### Settings (`app/core/config.py`)

| Variable               | Type   | Default     | Description                      |
|------------------------|--------|-------------|----------------------------------|
| TURNSTILE_ENABLED      | bool   | false       | Enable/disable verification      |
| TURNSTILE_SITE_KEY     | string | ""          | Public site key (frontend)       |
| TURNSTILE_SECRET_KEY   | string | ""          | Private secret key (backend)     |
| TURNSTILE_VERIFY_URL   | string | cloudflare  | Verification API endpoint        |
| TURNSTILE_TIMEOUT      | int    | 5           | Verification request timeout (s) |

### Widget Modes

Cloudflare Turnstile offers three widget modes:

1. **Managed (Recommended)**
   - Automatically determines challenge difficulty
   - Invisible for most users
   - Best balance of security and UX

2. **Non-Interactive**
   - Never shows a challenge
   - Blocks only obvious bots
   - Highest UX, moderate security

3. **Invisible**
   - Runs completely invisible
   - May silently reject suspicious requests
   - Good for high-security applications

Configure mode in Cloudflare dashboard when creating the site.

## Security Considerations

### Fail-Closed Strategy

The service implements **fail-closed** security:

```python
# Verification timeout → Reject request (403 Forbidden)
# Cloudflare API error → Reject request (403 Forbidden)
# Network failure → Reject request (403 Forbidden)
# Invalid token → Reject request (403 Forbidden)
```

This ensures bot protection cannot be bypassed by causing verification failures.

### Token Replay Protection

Turnstile tokens:
- Are single-use (cannot be replayed)
- Expire after 5 minutes
- Are tied to the original client IP
- Are validated by Cloudflare's backend

Attempting to reuse a token results in verification failure.

### Real IP Extraction

The service extracts the real client IP considering reverse proxy headers:

1. **X-Real-IP** (set by nginx for Cloudflare integration)
2. **X-Forwarded-For** (first IP in chain)
3. **request.remote_addr** (fallback for direct connections)

This ensures verification is tied to the actual client, not the proxy server.

### Rate Limiting Interaction

Turnstile works **in addition** to rate limiting, not as a replacement:

```python
@limiter.limit("5/minute")  # Rate limiting
@require_turnstile_json()   # Bot verification
def login():
    # Both checks must pass
    pass
```

Layered security: even if Turnstile is bypassed, rate limiting prevents brute force.

## Troubleshooting

### Issue: 403 "Verification failed" in Production

**Diagnosis:**

```bash
# Check application logs
docker-compose -f docker-compose.prod.yml logs app | grep Turnstile

# Typical errors:
# - "Turnstile token missing" → Frontend not sending token
# - "Turnstile verification failed. Error codes: [...]" → See error codes below
```

**Common Error Codes:**

| Error Code             | Meaning                        | Solution                          |
|------------------------|--------------------------------|-----------------------------------|
| `missing-input-secret` | Secret key not configured      | Set TURNSTILE_SECRET_KEY in .env  |
| `invalid-input-secret` | Secret key is incorrect        | Verify key matches dashboard      |
| `missing-input-response` | Token not provided           | Frontend must send token          |
| `invalid-input-response` | Token is invalid/expired     | Token must be fresh (<5 min)      |
| `timeout-or-duplicate` | Token already used             | Frontend must generate new token  |

**Resolution:**

1. Verify environment variables:
   ```bash
   docker-compose -f docker-compose.prod.yml exec app env | grep TURNSTILE
   ```

2. Check frontend sends token:
   ```bash
   # In browser DevTools Network tab
   # POST /api/v1/auth/login
   # Payload should include: "cf-turnstile-response": "0.ABC..."
   ```

3. Test with Cloudflare staging keys:
   ```bash
   # Use staging keys from Cloudflare dashboard
   # These always pass verification for testing
   ```

### Issue: Verification Skipped (Development Mode)

**Diagnosis:**

```bash
# Check TURNSTILE_ENABLED setting
grep TURNSTILE_ENABLED .env

# Expected in development:
# TURNSTILE_ENABLED=false
```

**Resolution:**

This is expected behavior in development. To test Turnstile locally:

```bash
# Enable Turnstile
echo "TURNSTILE_ENABLED=true" >> .env

# Add localhost to Turnstile site in Cloudflare dashboard
# Use testing keys for localhost domain
```

### Issue: Timeout Errors

**Diagnosis:**

```bash
# Application logs show:
# "Turnstile verification timeout (5s) for IP: x.x.x.x"
```

**Resolution:**

1. Increase timeout:
   ```bash
   # .env.production
   TURNSTILE_TIMEOUT=10  # Increase to 10 seconds
   ```

2. Check network connectivity:
   ```bash
   # Test from app container
   docker-compose -f docker-compose.prod.yml exec app \
     curl -I https://challenges.cloudflare.com/turnstile/v0/siteverify
   ```

3. Verify firewall allows outbound HTTPS:
   ```bash
   # Ensure port 443 outbound is open
   sudo firewall-cmd --list-all
   ```

### Issue: Wrong IP Logged

**Diagnosis:**

```bash
# Logs show proxy IP instead of real client IP
# "Turnstile verification succeeded for IP: 172.18.0.1"  # Docker bridge IP
```

**Resolution:**

Verify nginx is configured to pass real IP:

```nginx
# nginx/conf.d/00-cloudflare-real-ip.conf
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

## Performance Impact

### Latency

Turnstile verification adds ~100-300ms latency per request:

- Cloudflare API call: ~50-150ms
- Network overhead: ~50-150ms
- Widget rendering (frontend): ~100-200ms

**Mitigation:**
- Use CDN (Cloudflare) for widget script
- Implement async verification (if UX allows)
- Cache verification status (not recommended for security)

### Request Volume

Free tier supports **unlimited requests** with no rate limits.

### Monitoring

Monitor verification success rate:

```bash
# Check application logs for verification stats
docker-compose -f docker-compose.prod.yml logs app | \
  grep "Turnstile verification" | \
  awk '{print $NF}' | \
  sort | uniq -c

# Example output:
# 1523 succeeded
# 12 failed
```

## Best Practices

1. **Enable Only in Production**: Keep `TURNSTILE_ENABLED=false` in development
2. **Rotate Secret Keys**: Rotate keys every 90 days (generate new in Cloudflare dashboard)
3. **Monitor Failure Rate**: High failure rate (>5%) may indicate UX issues
4. **Use Managed Mode**: Best balance of security and user experience
5. **Test Before Deploy**: Use staging keys to test integration
6. **Log Verification Events**: Monitor for attack patterns
7. **Combine with Rate Limiting**: Layered defense is stronger
8. **Set Proper Timeout**: Balance security (fail-closed) and UX (fast response)

## Migration from CAPTCHA

If migrating from traditional CAPTCHA:

1. **Frontend**: Replace CAPTCHA widget with Turnstile widget
2. **Backend**: Replace CAPTCHA verification with `@require_turnstile_json()`
3. **Configuration**: Update environment variables
4. **Testing**: Verify all flows work with new widget
5. **Monitoring**: Compare bot detection rates

Turnstile typically blocks 90%+ of bots with 99%+ of legitimate users never seeing a challenge.

## References

- [Cloudflare Turnstile Documentation](https://developers.cloudflare.com/turnstile/)
- [Widget Configuration](https://developers.cloudflare.com/turnstile/get-started/)
- [Server-side Validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/)
- [Error Codes Reference](https://developers.cloudflare.com/turnstile/reference/error-codes/)
