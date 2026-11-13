---
icon: fa-solid fa-toolbox
order: 5
---

# Reset Docker ports on Windows

If Docker container ports are reserved on Windows, run these commands to reset:

```powershell
net stop winnat
net start winnat
```

## List PowerShell variables

```powershell
gci env:* | sort-object name

```
