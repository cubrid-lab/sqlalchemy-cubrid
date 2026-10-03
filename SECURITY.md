# Security Policy

## Supported Versions

sqlalchemy-cubrid is released from a single rolling line on `main` (see
[RELEASING.md](RELEASING.md)): there are no parallel long-term-maintenance
branches for older minor/patch releases. Only the **latest published release**
on [PyPI](https://pypi.org/project/sqlalchemy-cubrid/#history) receives
security fixes; a report against an older release is evaluated and, if it
still reproduces, fixed by releasing a new latest version rather than
backporting to the version originally reported against.

Security patches will be applied to the latest version only. Users are
strongly encouraged to always run the latest release.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in sqlalchemy-cubrid, please report it responsibly by emailing:

**Email:** paikend@gmail.com

**Do not** open a public GitHub issue for security vulnerabilities. Responsible disclosure allows us to address the issue before public disclosure.

### Response Timeline

- **48 hours:** Initial acknowledgment of your report
- **7 days:** Security assessment and initial response with remediation plan
- **Ongoing:** Regular updates on progress until resolution

## What Qualifies as a Security Issue

A security issue is any vulnerability that could:

- Allow unauthorized access to data
- Enable authentication bypass or privilege escalation
- Permit SQL injection or other code execution attacks
- Compromise confidentiality, integrity, or availability of the system
- Allow denial of service (DoS) attacks
- Expose sensitive information (credentials, tokens, private data)
- Bypass security controls or safety mechanisms
- Affect the security posture of applications using sqlalchemy-cubrid

Examples include:
- SQL injection vulnerabilities in query construction
- Authentication/authorization flaws
- Insecure credential handling
- Cryptographic weaknesses
- Session management issues
- Input validation bypass

## What to Include in Your Report

Please provide the following information with your vulnerability report:

1. **Description:** Clear explanation of the vulnerability and its impact
2. **Affected Versions:** Which version(s) of sqlalchemy-cubrid are vulnerable
3. **Steps to Reproduce:** Detailed instructions to reproduce the issue
4. **Proof of Concept:** Code sample, script, or test case demonstrating the vulnerability
5. **Impact Assessment:** Severity assessment (Critical, High, Medium, Low) and potential consequences
6. **Suggested Fix:** If you have a proposed patch or remediation strategy (optional but helpful)
7. **Your Contact Information:** Name, email, and PGP key (if applicable)

## Security Best Practices for Users

When using sqlalchemy-cubrid, follow these security best practices:

- Always use parameterized queries (the default in SQLAlchemy) to prevent SQL injection
- Keep sqlalchemy-cubrid and SQLAlchemy updated to the latest versions
- Use secure connection parameters when connecting to CUBRID databases
- Follow the principle of least privilege for database credentials
- Regularly audit and monitor database access logs
- Never hardcode credentials in your application code
- Use environment variables or secure credential management systems

## Disclosure Policy

Once a security vulnerability is fixed:

1. A security patch will be released
2. The vulnerability will be disclosed in release notes
3. An advisory may be published on GitHub Security Advisories
4. Credit will be given to the reporter (if requested)

We appreciate your responsible disclosure and help in keeping sqlalchemy-cubrid secure.
