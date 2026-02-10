---
tags:
  - nginx
  - snippets
aliases:
  - Nginx
title: Nginx
description: Nginx administration — config testing, logs, SSL, and troubleshooting.
---

# nginx

## Basics

```bash
# Test config before reload
nginx -t

# Reload (graceful, no downtime)
systemctl reload nginx

# Full restart
systemctl restart nginx

# Check version and build flags
nginx -V
```

## Config locations

```bash
/etc/nginx/nginx.conf           # Main config
/etc/nginx/conf.d/*.conf        # Server blocks (Debian/upstream)
/etc/nginx/sites-enabled/       # Server blocks (Ubuntu)
/var/log/nginx/access.log       # Access log
/var/log/nginx/error.log        # Error log
```

## Logs

Tail error log:

```bash
tail -f /var/log/nginx/error.log
```

Top requested URLs:

```bash
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20
```

Top IPs:

```bash
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20
```

Status codes distribution:

```bash
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn
```

## SSL/TLS

Check certificate expiry:

```bash
echo | openssl s_client -servername $HOST -connect $HOST:443 2>/dev/null | openssl x509 -noout -dates
```

Generate self-signed cert (testing):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt
```

## Troubleshooting

### Port conflict

Kill processes holding ports 80/443:

```bash
fuser -k 80/tcp && fuser -k 443/tcp
service nginx restart
```

### server_names_hash_bucket_size

Error:

```
nginx: [emerg] could not build the server_names_hash, you should increase server_names_hash_bucket_size: 64
```

Fix — double the reported value in `nginx.conf`:

```nginx
http {
    server_names_hash_bucket_size  128;
}
```

### 502 Bad Gateway

Backend is down or not responding:

```bash
# Check if backend is listening
ss -tulpn | grep $BACKEND_PORT

# Check nginx error log for upstream errors
grep upstream /var/log/nginx/error.log | tail -20
```

### Permission denied on logs/sockets

```bash
# Check nginx worker user
grep "^user" /etc/nginx/nginx.conf

# Fix socket permissions
chmod 660 /var/run/php-fpm.sock
chown www-data:www-data /var/run/php-fpm.sock
```

## Update GPG keys

```bash
curl https://nginx.org/keys/nginx_signing.key \
  | gpg --dearmor \
  | tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null

echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
  http://nginx.org/packages/debian bookworm nginx" \
  | tee /etc/apt/sources.list.d/nginx_org_packages_debian.list

apt update && apt list --upgradable
```
