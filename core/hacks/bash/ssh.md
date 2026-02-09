---
tags:
  - ssh
  - linux
  - security

---

# ssh

## Key operations

Create public key from private:

```bash
ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub
```

SHA256 fingerprint:

```bash
ssh-keygen -lf ~/.ssh/id_rsa.pub
```

MD5 fingerprint (GitHub format):

```bash
ssh-keygen -E md5 -lf ~/.ssh/id_rsa.pub
```

Add to agent:

```bash
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
```

## Regenerate host keys

```bash
sudo /bin/rm -v /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server
```

## Windows SSH agent

```powershell
# Check service status
Get-Service ssh-agent

# Enable manual start
Get-Service -Name ssh-agent | Set-Service -StartupType Manual

# Start and add key
Start-Service ssh-agent
ssh-add .\.ssh\id_rsa
```

## References

- [Limit access to openssh features with the Match option](https://raymii.org/s/tutorials/Limit_access_to_openssh_features_with_the_Match_keyword.html)
