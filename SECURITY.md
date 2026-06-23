# Security Policy

## Supported Versions

This repository maintains the current `master` branch only. Older generated patch outputs are not distributed by this project and are not supported.

## Reporting a Vulnerability

Please report security, credential, or copyright-sensitive concerns through GitHub private vulnerability reporting:

```text
https://github.com/mordekasiser/fallout-shelter-zh-cn-patch/security/advisories/new
```

If GitHub private vulnerability reporting is unavailable, open a public issue without sensitive details and ask for a private reporting channel.

Do not post credentials, tokens, private paths, or exploit details in a public issue.

Maintainers will try to acknowledge valid sensitive reports within 7 days. Response time may vary because this is a small community project.

## What To Include

- A short description of the issue.
- Steps to reproduce, when safe to share.
- Affected script, command, or documentation page.
- Redacted logs or error text.

Do not attach official game files, generated full patch packages, full `data.unity3d` files, cracked content, account credentials, API keys, tokens, or private local configuration.

## Scope

In scope:

- Tooling bugs that could expose local paths, credentials, or private configuration.
- Unsafe handling of user-supplied paths or generated files.
- GitHub workflow, dependency, or repository configuration issues.

Out of scope:

- Requests for official game files or complete generated patch packages.
- Cracks, DRM bypasses, account sharing, or runtime injection tooling.
- Vulnerabilities in Fallout Shelter, Steam, Windows, Python, UnityPy, or other upstream software. Please report those to the relevant upstream project or vendor.
