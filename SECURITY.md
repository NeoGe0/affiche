# Security policy

## Reporting a vulnerability

**Please don't open a public issue for a security problem.**

Use GitHub's private reporting instead:
[Security → Report a vulnerability](https://github.com/neoge0/affiche/security/advisories/new).
It's private between you and the maintainer until a fix ships.

Include what you'd expect: what the issue is, how to reproduce it, and what an attacker gets out of
it. A proof of concept is welcome.

Affiche is a small project maintained by one person — expect a first reply within a few days, not
within the hour.

## Supported versions

During the beta, only the latest release gets fixes. There is no backporting to earlier betas.

## Threat model

Affiche is a **self-hosted, single-admin** application. It assumes:

- A small set of trusted accounts. There are two roles: **admin** and **operator**. Admins manage
  accounts, media servers and library settings; operators can run poster work but cannot do those
  things, and webhook tokens are hidden from them. There is no multi-tenancy and no isolation
  otherwise — every account sees every server and library, so treat any account as trusted.
- It runs on a **trusted network**. It ships plain HTTP; put it behind a reverse proxy with TLS if
  it is reachable from anywhere but your LAN. **Don't expose it directly to the internet.**
- The `/data/config` volume is trusted storage. It holds the database, the session secret and the
  encryption key that protects your media-server and provider tokens. Anyone who can read that
  volume owns every token in it.

Things that *are* in scope and worth reporting: authentication or session bypass, SSRF through the
image proxy or custom-poster download, path traversal in poster/font serving, token leakage in
responses or logs, and privilege escalation through the webhook endpoint.

## Note on webhooks

`POST /affiche/webhooks/{token}` is deliberately unauthenticated apart from its token — media
servers can't perform a login. The token is the credential: keep the URL private, and regenerate it
from *Settings → Media Servers* if it leaks.
