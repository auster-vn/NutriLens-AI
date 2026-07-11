# Security Model

## Authentication

- Passwords use pwdlib's recommended Argon2 configuration.
- Signed JWT access tokens include subject, issued-at, expiry, and token type.
- Browsers receive tokens only through an HttpOnly, SameSite=Lax cookie.
- Bearer tokens are also accepted for automated clients and tests.
- Production startup rejects the default JWT secret and admin key.

## Authorization

- Personal data routes require an active Identity.
- Queries constrain both resource identifier and `user_id`.
- Admin routes accept an admin-role session or an explicitly configured admin key.
- Public product lookup, comparison, and knowledge chat do not expose personal records.

## Browser controls

- Credentialed CORS is restricted to configured origins.
- CSP, frame denial, content-type protection, referrer policy, and permissions policy are set.
- Camera permission is limited to the same origin.
- JSON requests plus CORS preflight and SameSite cookies reduce cross-site request risk. Production should deploy web and backend on the same site and keep HTTPS-only cookies enabled.

## Privacy

- Health-condition descriptions are not required by the profile model.
- Chat audit never stores raw questions.
- Admin audit payloads redact email, phone, token, secret, and key patterns.
- Product facts are shared cache data; user actions remain owner-scoped.

## Production checklist

1. Set `NUTRILENS_ENVIRONMENT=production`.
2. Generate a random `NUTRILENS_JWT_SECRET` of at least 32 characters.
3. Replace `NUTRILENS_ADMIN_KEY` or provision an admin-role user.
4. Set `NUTRILENS_AUTH_COOKIE_SECURE=true` and serve HTTPS.
5. Restrict `NUTRILENS_CORS_ORIGINS` to deployed web origins.
6. Replace in-memory rate limiting with a shared Redis-compatible adapter for multi-instance deployment.
7. Run PostgreSQL migrations and encrypted backups.
