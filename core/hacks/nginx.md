---
tags:
  - nginx
  - troubleshooting
  - linux
title: Nginx
aliases:
  - Nginx
description: Nginx troubleshooting and configuration.

---

# nginx

## Port conflict

Kill processes holding ports 80/443:

```bash
fuser -k 80/tcp && fuser -k 443/tcp
service nginx restart
```

## server_names_hash_bucket_size

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
