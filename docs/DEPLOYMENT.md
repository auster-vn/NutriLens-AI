# Deployment

Recommended free-tier split:

- Vercel for `apps/web`;
- Render for `apps/api`;
- Supabase Postgres for production database;
- Supabase Auth and RLS for real users;
- Upstash Redis for rate limiting when public traffic starts.

Production checklist:

- Set `NUTRILENS_ADMIN_KEY` to a strong secret.
- Replace SQLite with Supabase Postgres.
- Enable RLS for profile, pantry, scan history, and meal plans.
- Add rate limits for scan, chat, and admin mutation endpoints.
- Restrict CORS to production web origins.
