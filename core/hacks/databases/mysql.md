---
tags:
  - databases
  - mysql
aliases:
  - MySQL
title: MySQL
---

# mysql

## Users

List users:

```sql
SELECT user,host FROM mysql.user;
```

Create user with grants:

```sql
CREATE USER 'username'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER,
  CREATE TEMPORARY TABLES ON dbname.* TO 'username'@'%' IDENTIFIED BY 'password';
```

Full admin user:

```sql
CREATE USER 'admin'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost' WITH GRANT OPTION;
CREATE USER 'admin'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
```

Change password:

```sql
ALTER USER 'user'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

Delete user:

```sql
DROP USER 'user'@'host';
```

## Databases

```sql
CREATE DATABASE dbname CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
