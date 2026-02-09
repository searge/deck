---
tags:
  - networking
  - http
aliases:
  - HTTP
  - HTTPS
title: HTTP
description: HTTP methods, status codes, and protocol versions.
---

# http

Hypertext Transfer Protocol — the language of the web.
HTTPS is HTTP over [[tls]].

## Request structure

```text
METHOD /path HTTP/1.1
Host: example.com
Header: value

body (optional)
```

## Methods

| Method | Purpose | Idempotent | Safe |
|--------|---------|-----------|------|
| GET | Read | Yes | Yes |
| POST | Create | No | No |
| PUT | Replace | Yes | No |
| PATCH | Partial update | No | No |
| DELETE | Remove | Yes | No |
| HEAD | Headers only | Yes | Yes |
| OPTIONS | Supported methods | Yes | Yes |

## Status codes

| Range | Category | Common codes |
|-------|----------|-------------|
| 1xx | Informational | 101 Switching Protocols |
| 2xx | Success | 200 OK, 201 Created, 204 No Content |
| 3xx | Redirect | 301 Moved Permanently, 302 Found, 304 Not Modified |
| 4xx | Client error | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Too Many Requests |
| 5xx | Server error | 500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout |

## Diagnostic commands

```bash
# Basic request with headers
curl -v https://example.com

# Headers only
curl -I https://example.com

# Follow redirects
curl -L https://example.com

# POST with JSON
curl -X POST https://api.example.com/data \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# Show timing
curl -o /dev/null -s -w "\
  DNS:      %{time_namelookup}s\n\
  Connect:  %{time_connect}s\n\
  TLS:      %{time_appconnect}s\n\
  TTFB:     %{time_starttransfer}s\n\
  Total:    %{time_total}s\n" \
  https://example.com
```

## HTTP/1.1 vs HTTP/2 vs HTTP/3

| Feature | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---------|----------|--------|--------|
| Multiplexing | No (one request per connection) | Yes (streams) | Yes (streams) |
| Header compression | No | HPACK | QPACK |
| Transport | TCP | TCP | QUIC (UDP) |
| Head-of-line blocking | Yes | At TCP level | No |

## See also

- [[tls]]
- [[dns]]
- [[nginx]]
