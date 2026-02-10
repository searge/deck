---
tags:
  - cache
  - snippets
aliases:
  - Varnish
title: Varnish
description: Varnish HTTP cache — config testing, cache purge, and troubleshooting.
---

# varnish

## Basics

```bash
# Check version
varnishd -V

# Test configuration before reload
varnishd -C -f /etc/varnish/default.vcl

# Reload (after config test passes)
systemctl reload varnish
```

## Cache management

Purge a URL:

```bash
curl -X PURGE http://localhost/path/to/page
```

Purge everything (ban):

```bash
varnishadm "ban req.url ~ ."
```

Purge by pattern:

```bash
varnishadm "ban req.url ~ ^/images/"
```

## Monitoring

Live request log:

```bash
varnishlog
```

Statistics:

```bash
varnishstat
```

Top requests:

```bash
varnishtop -i ReqURL
```

Hit rate:

```bash
varnishstat -f MAIN.cache_hit -f MAIN.cache_miss
```

## Troubleshooting

### Check if response comes from cache

```bash
curl -sI http://localhost/page | grep -E 'X-Cache|Age|Via'
```

### Varnish panics

Check panic log:

```bash
varnishadm panic.show
```

Clear panic after investigation:

```bash
varnishadm panic.clear
```

### Backend health

```bash
varnishadm backend.list
```

### Service management

```bash
systemctl status varnish
systemctl restart varnish
journalctl -u varnish -f
```

## Configuration example

Minimal `/etc/varnish/default.vcl`:

```vcl
vcl 4.0;

backend default {
    .host = "127.0.0.1";
    .port = "8080";
}

sub vcl_recv {
    # Strip cookies for static files
    if (req.url ~ "\.(css|js|png|jpg|gif|ico|svg|woff2?)$") {
        unset req.http.Cookie;
    }
}

sub vcl_backend_response {
    # Cache static files for 1 day
    if (bereq.url ~ "\.(css|js|png|jpg|gif|ico|svg|woff2?)$") {
        set beresp.ttl = 1d;
        unset beresp.http.Set-Cookie;
    }
}
```

## References

- [Troubleshooting Varnish](https://www.varnish-software.com/developers/tutorials/troubleshooting-varnish/)
