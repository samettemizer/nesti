---
title: Application Security Engineering
slug: senior-security
source: https://github.com/alirezarezvani/claude-skills/tree/main/engineering-team/senior-security
triggers: security review, threat model, vulnerability, owasp, sql injection, xss, secure coding, attack surface, mass assignment, sensitive data
vendored_by: scripts/fetch_skills.py
---

# Senior Security Engineer

Security engineering tools for threat modeling, vulnerability analysis, secure architecture design, and penetration testing.

---

## Table of Contents

- [Threat Modeling Workflow](#threat-modeling-workflow)
- [Security Architecture Workflow](#security-architecture-workflow)
- [Vulnerability Assessment Workflow](#vulnerability-assessment-workflow)
- [Secure Code Review Workflow](#secure-code-review-workflow)
- [Incident Response Workflow](#incident-response-workflow)
- [Security Tools Reference](#security-tools-reference)
- [Tools and References](#tools-and-references)

---

## Threat Modeling Workflow

Identify and analyze security threats using STRIDE methodology.

### Workflow: Conduct Threat Model

1. Define system scope and boundaries:
   - Identify assets to protect
   - Map trust boundaries
   - Document data flows
2. Create data flow diagram:
   - External entities (users, services)
   - Processes (application components)
   - Data stores (databases, caches)
   - Data flows (APIs, network connections)
3. Apply STRIDE to each DFD element (see [STRIDE per Element Matrix](#stride-per-element-matrix) below)
4. Score risks using DREAD:
   - Damage potential (1-10)
   - Reproducibility (1-10)
   - Exploitability (1-10)
   - Affected users (1-10)
   - Discoverability (1-10)
5. Prioritize threats by risk score
6. Define mitigations for each threat
7. Document in threat model report
8. **Validation:** All DFD elements analyzed; STRIDE applied; threats scored; mitigations mapped

### STRIDE Threat Categories

| Category | Security Property | Mitigation Focus |
|----------|-------------------|------------------|
| Spoofing | Authentication | MFA, certificates, strong auth |
| Tampering | Integrity | Signing, checksums, validation |
| Repudiation | Non-repudiation | Audit logs, digital signatures |
| Information Disclosure | Confidentiality | Encryption, access controls |
| Denial of Service | Availability | Rate limiting, redundancy |
| Elevation of Privilege | Authorization | RBAC, least privilege |

### STRIDE per Element Matrix

| DFD Element | S | T | R | I | D | E |
|-------------|---|---|---|---|---|---|
| External Entity | X | | X | | | |
| Process | X | X | X | X | X | X |
| Data Store | | X | X | X | X | |
| Data Flow | | X | | X | X | |

See: [references/threat-modeling-guide.md](references/threat-modeling-guide.md)

---

## Security Architecture Workflow

Design secure systems using defense-in-depth principles.

### Workflow: Design Secure Architecture

1. Define security requirements:
   - Compliance requirements (GDPR, HIPAA, PCI-DSS)
   - Data classification (public, internal, confidential, restricted)
   - Threat model inputs
2. Apply defense-in-depth layers:
   - Perimeter: WAF, DDoS protection, rate limiting
   - Network: Segmentation, IDS/IPS, mTLS
   - Host: Patching, EDR, hardening
   - Application: Input validation, authentication, secure coding
   - Data: Encryption at rest and in transit
3. Implement Zero Trust principles:
   - Verify explicitly (every request)
   - Least privilege access (JIT/JEA)
   - Assume breach (segment, monitor)
4. Configure authentication and authorization:
   - Identity provider selection
   - MFA requirements
   - RBAC/ABAC model
5. Design encryption strategy:
   - Key management approach
   - Algorithm selection
   - Certificate lifecycle
6. Plan security monitoring:
   - Log aggregation
   - SIEM integration
   - Alerting rules
7. Document architecture decisions
8. **Validation:** Defense-in-depth layers defined; Zero Trust applied; encryption strategy documented; monitoring planned

### Defense-in-Depth Layers

```
Layer 1: PERIMETER
  WAF, DDoS mitigation, DNS filtering, rate limiting

Layer 2: NETWORK
  Segmentation, IDS/IPS, network monitoring, VPN, mTLS

Layer 3: HOST
  Endpoint protection, OS hardening, patching, logging

Layer 4: APPLICATION
  Input validation, authentication, secure coding, SAST

Layer 5: DATA
  Encryption at rest/transit, access controls, DLP, backup
```

### Authentication Pattern Selection

| Use Case | Recommended Pattern |
|----------|---------------------|
| Web application | OAuth 2.0 + PKCE with OIDC |
| API authentication | JWT with short expiration + refresh tokens |
| Service-to-service | mTLS with certificate rotation |
| CLI/Automation | API keys with IP allowlisting |
| High security | FIDO2/WebAuthn hardware keys |

See: [references/security-architecture-patterns.md](references/security-architecture-patterns.md)

---

## Vulnerability Assessment Workflow

Identify and remediate security vulnerabilities in applications.

### Workflow: Conduct Vulnerability Assessment

1. Define assessment scope:
   - In-scope systems and applications
   - Testing methodology (black box, gray box, white box)
   - Rules of engagement
2. Gather information:
   - Technology stack inventory
   - Architecture documentation
   - Previous vulnerability reports
3. Perform automated scanning:
   - SAST (static analysis)
   - DAST (dynamic analysis)
   - Dependency scanning
   - Secret detection
4. Conduct manual testing:
   - Business logic flaws
   - Authentication bypass
   - Authorization issues
   - Injection vulnerabilities
5. Classify findings by severity:
   - Critical: Immediate exploitation risk
   - High: Significant impact, easier to exploit
   - Medium: Moderate impact or difficulty
   - Low: Minor impact
6. Develop remediation plan:
   - Prioritize by risk
   - Assign owners
   - Set deadlines
7. Verify fixes and document
8. **Validation:** Scope defined; automated and manual testing complete; findings classified; remediation tracked

For OWASP Top 10 vulnerability descriptions and testing guidance, refer to [owasp.org/Top10](https://owasp.org/Top10).

### Vulnerability Severity Matrix

| Impact \ Exploitability | Easy | Moderate | Difficult |
|-------------------------|------|----------|-----------|
| Critical | Critical | Critical | High |
| High | Critical | High | Medium |
| Medium | High | Medium | Low |
| Low | Medium | Low | Low |

---

## Secure Code Review Workflow

Review code for security vulnerabilities before deployment.

### Workflow: Conduct Security Code Review

1. Establish review scope:
   - Changed files and functions
   - Security-sensitive areas (auth, crypto, input handling)
   - Third-party integrations
2. Run automated analysis:
   - SAST tools (Semgrep, CodeQL, Bandit)
   - Secret scanning
   - Dependency vulnerability check
3. Review authentication code:
   - Password handling (hashing, storage)
   - Session management
   - Token validation
4. Review authorization code:
   - Access control checks
   - RBAC implementation
   - Privilege boundaries
5. Review data handling:
   - Input validation
   - Output encoding
   - SQL query construction
   - File path handling
6. Review cryptographic code:
   - Algorithm selection
   - Key management
   - Random number generation
7. Document findings with severity
8. **Validation:** Automated scans passed; auth/authz reviewed; data handling checked; crypto verified; findings documented

### Security Code Review Checklist

| Category | Check | Risk |
|----------|-------|------|
| Input Validation | All user input validated and sanitized | Injection |
| Output Encoding | Context-appropriate encoding applied | XSS |
| Authentication | Passwords hashed with Argon2/bcrypt | Credential theft |
| Session | Secure cookie flags set (HttpOnly, Secure, SameSite) | Session hijacking |
| Authorization | Server-side permission checks on all endpoints | Privilege escalation |
| SQL | Parameterized queries used exclusively | SQL injection |
| File Access | Path traversal sequences rejected | Path traversal |
| Secrets | No hardcoded credentials or keys | Information disclosure |
| Dependencies | Known vulnerable packages updated | Supply chain |
| Logging | Sensitive data not logged | Information disclosure |

### Secure vs Insecure Patterns

| Pattern | Issue | Secure Alternative |
|---------|-------|-------------------|
| SQL string formatting | SQL injection | Use parameterized queries with placeholders |
| Shell command building | Command injection | Use subprocess with argument lists, no shell |
| Path concatenation | Path traversal | Validate and canonicalize paths |
| MD5/SHA1 for passwords | Weak hashing | Use Argon2id or bcrypt |
| Math.random for tokens | Predictable values | Use crypto.getRandomValues |

### Inline Code Examples

**SQL Injection — insecure vs. secure (Python):**

```python
# ❌ Insecure: string formatting allows SQL injection
query = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(query)

# ✅ Secure: parameterized query — user input never interpreted as SQL
query = "SELECT * FROM users WHERE username = %s"
cursor.execute(query, (username,))
```

**Password Hashing with Argon2id (Python):**

```python
from argon2 import PasswordHasher

ph = PasswordHasher()          # uses secure defaults (time_cost, memory_cost)

# On registration
hashed = ph.hash(plain_password)

# On login — raises argon2.exceptions.VerifyMismatchError on failure
ph.verify(hashed, plain_password)
```

**Secret Scanning — core pattern matching (Python):**

```python
import re, pathlib

SECRET_PATTERNS = {
    "aws_access_key":  re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token":    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "private_key":     re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
    "generic_secret":  re.compile(r'(?i)(password|secret|api_key)\s*=\s*["\']?\S{8,}'),
}

def scan_file(path: pathlib.Path) -> list[dict]:
    findings = []
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                findings.append({"file": str(path), "line": lineno, "type": name})
    return findings
```

---

## Incident Response Workflow

Respond to and contain security incidents.

### Workflow: Handle Security Incident

1. Identify and triage:
   - Validate incident is genuine
   - Assess initial scope and severity
   - Activate incident response team
2. Contain the threat:
   - Isolate affected systems
   - Block malicious IPs/accounts
   - Disable compromised credentials
3. Eradicate root cause:
   - Remove malware/backdoors
   - Patch vulnerabilities
   - Update configurations
4. Recover operations:
   - Restore from clean backups
   - Verify system integrity
   - Monitor for recurrence
5. Conduct post-mortem:
   - Timeline reconstruction
   - Root cause analysis
   - Lessons learned
6. Implement improvements:
   - Update detection rules
   - Enhance controls
   - Update runbooks
7. Document and report
8. **Validation:** Threat contained; root cause eliminated; systems recovered; post-mortem complete; improvements implemented

### Incident Severity Levels

| Level | Response Time | Escalation |
|-------|---------------|------------|
| P1 - Critical (active breach/exfiltration) | Immediate | CISO, Legal, Executive |
| P2 - High (confirmed, contained) | 1 hour | Security Lead, IT Director |
| P3 - Medium (potential, under investigation) | 4 hours | Security Team |
| P4 - Low (suspicious, low impact) | 24 hours | On-call engineer |

### Incident Response Checklist

| Phase | Actions |
|-------|---------|
| Identification | Validate alert, assess scope, determine severity |
| Containment | Isolate systems, preserve evidence, block access |
| Eradication | Remove threat, patch vulnerabilities, reset credentials |
| Recovery | Restore services, verify integrity, increase monitoring |
| Lessons Learned | Document timeline, identify gaps, update procedures |

---

## Security Tools Reference

### Recommended Security Tools

| Category | Tools |
|----------|-------|
| SAST | Semgrep, CodeQL, Bandit (Python), ESLint security plugins |
| DAST | OWASP ZAP, Burp Suite, Nikto |
| Dependency Scanning | Snyk, Dependabot, npm audit, pip-audit |
| Secret Detection | GitLeaks, TruffleHog, detect-secrets |
| Container Security | Trivy, Clair, Anchore |
| Infrastructure | Checkov, tfsec, ScoutSuite |
| Network | Wireshark, Nmap, Masscan |
| Penetration | Metasploit, sqlmap, Burp Suite Pro |

### Cryptographic Algorithm Selection

| Use Case | Algorithm | Key Size |
|----------|-----------|----------|
| Symmetric encryption | AES-256-GCM | 256 bits |
| Password hashing | Argon2id | N/A (use defaults) |
| Message authentication | HMAC-SHA256 | 256 bits |
| Digital signatures | Ed25519 | 256 bits |
| Key exchange | X25519 | 256 bits |
| TLS | TLS 1.3 | N/A |

See: [references/cryptography-implementation.md](references/cryptography-implementation.md)

---

## Tools and References

### Scripts

| Script | Purpose |
|--------|---------|
| [threat_modeler.py](scripts/threat_modeler.py) | STRIDE threat analysis with DREAD risk scoring; JSON and text output; interactive guided mode |
| [secret_scanner.py](scripts/secret_scanner.py) | Detect hardcoded secrets and credentials across 20+ patterns; CI/CD integration ready |

For usage, see the inline code examples in [Secure Code Review Workflow](#inline-code-examples) and the script source files directly.

### References

| Document | Content |
|----------|---------|
| [security-architecture-patterns.md](references/security-architecture-patterns.md) | Zero Trust, defense-in-depth, authentication patterns, API security |
| [threat-modeling-guide.md](references/threat-modeling-guide.md) | STRIDE methodology, attack trees, DREAD scoring, DFD creation |
| [cryptography-implementation.md](references/cryptography-implementation.md) | AES-GCM, RSA, Ed25519, password hashing, key management |

---

## Security Standards Reference

### Security Headers Checklist

| Header | Recommended Value |
|--------|-------------------|
| Content-Security-Policy | default-src self; script-src self |
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| Strict-Transport-Security | max-age=31536000; includeSubDomains |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | geolocation=(), microphone=(), camera=() |

For compliance framework requirements (OWASP ASVS, CIS Benchmarks, NIST CSF, PCI-DSS, HIPAA, SOC 2), refer to the respective official documentation.

---

## Related Skills

| Skill | Integration Point |
|-------|-------------------|
| [senior-devops](../senior-devops/) | CI/CD security, infrastructure hardening |
| [senior-secops](../senior-secops/) | Security monitoring, incident response |
| [senior-backend](../senior-backend/) | Secure API development |
| [senior-architect](../senior-architect/) | Security architecture decisions |

---

## Threat Modeling Guide

Systematic approaches for identifying, analyzing, and mitigating security threats.

---

### Table of Contents

- [Threat Modeling Process](#threat-modeling-process)
- [STRIDE Framework](#stride-framework)
- [Attack Trees](#attack-trees)
- [DREAD Risk Scoring](#dread-risk-scoring)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Common Attack Patterns](#common-attack-patterns)

---

### Threat Modeling Process

#### Workflow: Conduct Threat Model

1. Define the scope and objectives:
   - System boundaries
   - Assets to protect
   - Trust levels
2. Create data flow diagram:
   - External entities
   - Processes
   - Data stores
   - Data flows
   - Trust boundaries
3. Identify threats using STRIDE:
   - Apply STRIDE to each DFD element
   - Document threat scenarios
4. Analyze and prioritize risks:
   - Score using DREAD
   - Rank by severity
5. Define mitigations:
   - Map controls to threats
   - Identify gaps
6. Validate and iterate:
   - Review with team
   - Update as system evolves
7. Document in threat model report
8. **Validation:** All DFD elements analyzed; threats documented; mitigations mapped; residual risks accepted

#### Threat Model Template

```
THREAT MODEL REPORT

System: [System Name]
Version: [Version]
Date: [Date]
Author: [Name]

1. SYSTEM OVERVIEW
   - Purpose: [Description]
   - Users: [User types]
   - Data: [Data classification]

2. SCOPE
   - In Scope: [Components included]
   - Out of Scope: [Components excluded]
   - Assumptions: [Security assumptions]

3. DATA FLOW DIAGRAM
   [DFD image or ASCII representation]

4. THREATS IDENTIFIED
   | ID | Element | STRIDE | Threat | DREAD | Mitigation |
   |----|---------|--------|--------|-------|------------|

5. RESIDUAL RISKS
   [Accepted risks with justification]

6. RECOMMENDATIONS
   [Prioritized security improvements]
```

---

### STRIDE Framework

Categorization model for identifying threats.

#### STRIDE Categories

| Category | Description | Violated Property |
|----------|-------------|-------------------|
| **S**poofing | Pretending to be someone/something else | Authentication |
| **T**ampering | Modifying data or code | Integrity |
| **R**epudiation | Denying actions occurred | Non-repudiation |
| **I**nformation Disclosure | Exposing data to unauthorized parties | Confidentiality |
| **D**enial of Service | Making system unavailable | Availability |
| **E**levation of Privilege | Gaining unauthorized access | Authorization |

#### STRIDE per Element

| DFD Element | Applicable Threats |
|-------------|-------------------|
| External Entity | S, R |
| Process | S, T, R, I, D, E |
| Data Store | T, R, I, D |
| Data Flow | T, I, D |

#### STRIDE Analysis Template

```
STRIDE ANALYSIS

Element: User Authentication Service
Type: Process

┌─────────────────────────────────────────────────────────────────┐
│ SPOOFING                                                        │
├─────────────────────────────────────────────────────────────────┤
│ Threat: Attacker uses stolen credentials to impersonate user   │
│ Attack Vector: Phishing, credential stuffing, session hijack   │
│ Likelihood: High                                                │
│ Impact: High - Full account access                              │
│ Mitigation: MFA, session binding, anomaly detection             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TAMPERING                                                       │
├─────────────────────────────────────────────────────────────────┤
│ Threat: Attacker modifies authentication request in transit    │
│ Attack Vector: Man-in-the-middle, request manipulation         │
│ Likelihood: Medium                                              │
│ Impact: High - Bypass authentication                            │
│ Mitigation: TLS 1.3, request signing, HSTS                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ REPUDIATION                                                     │
├─────────────────────────────────────────────────────────────────┤
│ Threat: User denies performing privileged action               │
│ Attack Vector: Claim account was compromised                   │
│ Likelihood: Medium                                              │
│ Impact: Medium - Dispute resolution difficulty                  │
│ Mitigation: Comprehensive audit logging, log integrity         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ INFORMATION DISCLOSURE                                          │
├─────────────────────────────────────────────────────────────────┤
│ Threat: Password hashes exposed via SQL injection              │
│ Attack Vector: SQLi, backup exposure, error messages           │
│ Likelihood: Medium                                              │
│ Impact: Critical - Mass credential compromise                   │
│ Mitigation: Parameterized queries, encryption, error handling  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ DENIAL OF SERVICE                                               │
├─────────────────────────────────────────────────────────────────┤
│ Threat: Brute force attacks overwhelm authentication service   │
│ Attack Vector: Credential stuffing, distributed attacks        │
│ Likelihood: High                                                │
│ Impact: High - Users cannot authenticate                        │
│ Mitigation: Rate limiting, CAPTCHA, account lockout            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ ELEVATION OF PRIVILEGE                                          │
├─────────────────────────────────────────────────────────────────┤
│ Threat: Regular user gains admin privileges                    │
│ Attack Vector: JWT manipulation, IDOR, role confusion          │
│ Likelihood: Medium                                              │
│ Impact: Critical - Full system compromise                       │
│ Mitigation: Server-side authorization, signed tokens, RBAC     │
└─────────────────────────────────────────────────────────────────┘
```

#### Threat Mitigation Matrix

| STRIDE Category | Standard Mitigations |
|-----------------|---------------------|
| Spoofing | Authentication (passwords, MFA, certificates) |
| Tampering | Integrity controls (signing, hashing, checksums) |
| Repudiation | Audit logging, digital signatures, timestamps |
| Information Disclosure | Encryption, access controls, data masking |
| Denial of Service | Rate limiting, redundancy, filtering |
| Elevation of Privilege | Authorization, least privilege, input validation |

---

### Attack Trees

Visual representation of attack paths to a specific goal.

#### Attack Tree Structure

```
ATTACK TREE: Compromise User Account

                    ┌─────────────────────┐
                    │ GOAL: Access User   │
                    │      Account        │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────┴──────┐     ┌──────┴──────┐     ┌──────┴──────┐
    │   Obtain    │     │   Bypass    │     │   Exploit   │
    │ Credentials │     │    Auth     │     │   Session   │
    │    [OR]     │     │    [OR]     │     │    [OR]     │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
     ┌─────┼─────┐       ┌─────┼─────┐       ┌─────┼─────┐
     │     │     │       │     │     │       │     │     │
   ┌─┴─┐ ┌─┴─┐ ┌─┴─┐   ┌─┴─┐ ┌─┴─┐ ┌─┴─┐   ┌─┴─┐ ┌─┴─┐ ┌─┴─┐
   │Phi│ │Crd│ │Key│   │SQL│ │JWT│ │Pwd│   │XSS│ │Fix│ │Sid│
   │sh │ │Stf│ │Log│   │ i │ │Frg│ │Rst│   │   │ │tn │ │Hj │
   └───┘ └───┘ └───┘   └───┘ └───┘ └───┘   └───┘ └───┘ └───┘

Legend:
- Phi: Phishing
- CrdStf: Credential Stuffing
- KeyLog: Keylogger
- SQLi: SQL Injection
- JWTFrg: JWT Forgery
- PwdRst: Password Reset Flaw
- XSS: Cross-Site Scripting
- Fixtn: Session Fixation
- SidHj: Session Hijacking
```

#### Attack Tree Analysis

| Attack Path | Difficulty | Detection | Priority |
|-------------|------------|-----------|----------|
| Phishing → Credential theft | Low | Medium | High |
| SQL Injection → Auth bypass | Medium | High | Critical |
| XSS → Session steal | Medium | Medium | High |
| JWT forgery → Privilege escalation | High | Low | Critical |

#### Calculating Attack Probability

```python
def calculate_attack_probability(attack_tree_node):
    """
    Calculate cumulative probability of attack success.

    For OR nodes: P = 1 - (1-P1)(1-P2)...(1-Pn)
    For AND nodes: P = P1 * P2 * ... * Pn
    """
    if node.is_leaf:
        return node.probability

    child_probs = [calculate_attack_probability(c) for c in node.children]

    if node.operator == 'OR':
        # At least one path succeeds
        prob_all_fail = 1
        for p in child_probs:
            prob_all_fail *= (1 - p)
        return 1 - prob_all_fail

    elif node.operator == 'AND':
        # All paths must succeed
        prob_all_succeed = 1
        for p in child_probs:
            prob_all_succeed *= p
        return prob_all_succeed
```

---

### DREAD Risk Scoring

Quantitative risk assessment for prioritizing threats.

#### DREAD Components

| Factor | Description | Scale |
|--------|-------------|-------|
| **D**amage | How bad is the impact? | 1-10 |
| **R**eproducibility | How easy to reproduce? | 1-10 |
| **E**xploitability | How easy to exploit? | 1-10 |
| **A**ffected Users | How many users impacted? | 1-10 |
| **D**iscoverability | How easy to find? | 1-10 |

#### DREAD Scoring Guide

**Damage Potential:**
| Score | Description |
|-------|-------------|
| 10 | Complete system compromise, data destruction |
| 7-9 | Large data breach, significant financial loss |
| 4-6 | Partial data exposure, service degradation |
| 1-3 | Minor information disclosure, low impact |

**Reproducibility:**
| Score | Description |
|-------|-------------|
| 10 | Always reproducible, automated |
| 7-9 | Reproducible most of the time |
| 4-6 | Reproducible with some effort |
| 1-3 | Difficult to reproduce, timing dependent |

**Exploitability:**
| Score | Description |
|-------|-------------|
| 10 | No skills required, exploit exists |
| 7-9 | Basic skills, tools available |
| 4-6 | Moderate skills required |
| 1-3 | Advanced skills, custom exploit needed |

**Affected Users:**
| Score | Description |
|-------|-------------|
| 10 | All users |
| 7-9 | Large subset of users |
| 4-6 | Some users |
| 1-3 | Few or individual users |

**Discoverability:**
| Score | Description |
|-------|-------------|
| 10 | Publicly documented, obvious |
| 7-9 | Easy to find via scanning |
| 4-6 | Requires investigation |
| 1-3 | Obscure, requires insider knowledge |

#### DREAD Calculation

```python
def calculate_dread_score(damage, reproducibility, exploitability,
                           affected_users, discoverability):
    """
    Calculate DREAD risk score.

    Returns: Float between 1-10
    Risk Levels:
        8-10: Critical
        6-7.9: High
        4-5.9: Medium
        1-3.9: Low
    """
    score = (damage + reproducibility + exploitability +
             affected_users + discoverability) / 5
    return round(score, 1)

def get_risk_level(dread_score):
    if dread_score >= 8:
        return 'Critical'
    elif dread_score >= 6:
        return 'High'
    elif dread_score >= 4:
        return 'Medium'
    else:
        return 'Low'
```

#### DREAD Assessment Example

```
THREAT: SQL Injection in Login Form

| Factor | Score | Justification |
|--------|-------|---------------|
| Damage | 9 | Full database access, credential theft |
| Reproducibility | 9 | Consistent, automated tools exist |
| Exploitability | 8 | Well-documented attack, easy tools |
| Affected Users | 10 | All users with accounts |
| Discoverability | 7 | Scanners detect easily |

DREAD Score: (9+9+8+10+7)/5 = 8.6
Risk Level: CRITICAL
Priority: Immediate remediation required
```

---

### Data Flow Diagrams

Visual representation of system data movement for security analysis.

#### DFD Elements

| Symbol | Element | Security Considerations |
|--------|---------|------------------------|
| Rectangle | External Entity | Trust boundary crossing |
| Circle/Oval | Process | All STRIDE threats apply |
| Parallel Lines | Data Store | Tampering, disclosure, DoS |
| Arrow | Data Flow | Tampering, disclosure, DoS |
| Dashed Line | Trust Boundary | Authentication required |

#### DFD Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| Level 0 (Context) | Single process, external entities | Executive overview |
| Level 1 | Major processes expanded | Architecture review |
| Level 2 | Detailed subprocesses | Detailed threat modeling |

#### Example: E-Commerce DFD

```
LEVEL 0: CONTEXT DIAGRAM

                              ┌──────────────────┐
                              │                  │
     ┌────────────┐           │   E-Commerce     │           ┌────────────┐
     │            │  Orders   │    System        │  Payment  │            │
     │  Customer  │──────────▶│                  │──────────▶│  Payment   │
     │            │◀──────────│                  │◀──────────│  Gateway   │
     └────────────┘  Status   │                  │  Result   └────────────┘
                              │                  │
                              └──────────────────┘
                                      │
                                      │ Fulfillment
                                      ▼
                              ┌────────────────┐
                              │   Warehouse    │
                              │    System      │
                              └────────────────┘


LEVEL 1: EXPANDED VIEW

┌─────────────────────────────────────────────────────────────────────┐
│                         TRUST BOUNDARY                               │
│  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  │
│                                                                      │
│   ┌─────────┐       ┌─────────┐       ┌─────────┐       ┌─────────┐ │
│   │         │       │   Web   │       │  Order  │       │ Payment │ │
│   │   CDN   │──────▶│ Server  │──────▶│ Service │──────▶│ Service │ │
│   │         │       │         │       │         │       │         │ │
│   └─────────┘       └────┬────┘       └────┬────┘       └────┬────┘ │
│                          │                 │                 │      │
│                          │                 │                 │      │
│                          ▼                 ▼                 ▼      │
│                    ╔═══════════╗     ╔═══════════╗    ╔═══════════╗ │
│                    ║  Session  ║     ║  Orders   ║    ║  Payment  ║ │
│                    ║   Store   ║     ║    DB     ║    ║    DB     ║ │
│                    ╚═══════════╝     ╚═══════════╝    ╚═══════════╝ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          │ Crosses Trust Boundary
                          ▼
                    ┌───────────┐
                    │  Payment  │
                    │  Gateway  │
                    │ (External)│
                    └───────────┘
```

#### Trust Boundary Analysis

| Boundary Crossing | Authentication | Authorization | Encryption |
|-------------------|----------------|---------------|------------|
| Customer → Web Server | Session cookie | - | TLS 1.3 |
| Web Server → Order Service | mTLS | Service account | Internal TLS |
| Order Service → DB | Connection pool | DB user roles | TLS |
| Payment Service → Gateway | API key + HMAC | IP whitelist | TLS 1.3 |

---

### Common Attack Patterns

#### OWASP Top 10 Mapping

| Rank | Vulnerability | STRIDE | Common Attack |
|------|---------------|--------|---------------|
| A01 | Broken Access Control | E | IDOR, privilege escalation |
| A02 | Cryptographic Failures | I | Weak encryption, exposed keys |
| A03 | Injection | T, E | SQLi, XSS, command injection |
| A04 | Insecure Design | All | Logic flaws, missing controls |
| A05 | Security Misconfiguration | I, E | Default creds, verbose errors |
| A06 | Vulnerable Components | All | Outdated libraries, CVEs |
| A07 | Authentication Failures | S, E | Credential stuffing, weak passwords |
| A08 | Software/Data Integrity | T | Unsigned updates, CI/CD attacks |
| A09 | Logging Failures | R | Missing logs, log injection |
| A10 | SSRF | I, T | Internal service access |

#### Attack Pattern Catalog

```
ATTACK PATTERN: SQL Injection (A03)

Threat: T (Tampering), E (Elevation of Privilege)

Attack Vector:
1. Identify input fields that construct SQL queries
2. Test for injection: ' OR '1'='1' --
3. Extract data: UNION SELECT password FROM users
4. Escalate: Execute stored procedures, write files

Detection:
- WAF rules for SQL patterns
- Prepared statement verification
- Database query logging

Mitigation:
- Parameterized queries (primary)
- Input validation (secondary)
- Least privilege database accounts
- Web application firewall

Test Cases:
- Single quote injection: '
- Boolean-based: ' OR 1=1 --
- Time-based: '; WAITFOR DELAY '0:0:5' --
- UNION-based: ' UNION SELECT NULL, username, password FROM users --
```

#### Threat Intelligence Integration

| Source | Purpose | Update Frequency |
|--------|---------|------------------|
| CVE/NVD | Known vulnerabilities | Daily |
| MITRE ATT&CK | Attack techniques | Quarterly |
| OWASP | Web application threats | Annual |
| Industry ISACs | Sector-specific threats | Real-time |

---

## Security Architecture Patterns

Proven security architecture patterns for designing resilient systems.

---

### Table of Contents

- [Zero Trust Architecture](#zero-trust-architecture)
- [Defense in Depth](#defense-in-depth)
- [Secure Authentication Patterns](#secure-authentication-patterns)
- [API Security Patterns](#api-security-patterns)
- [Data Protection Patterns](#data-protection-patterns)
- [Security Anti-Patterns](#security-anti-patterns)

---

### Zero Trust Architecture

Never trust, always verify. Every request authenticated and authorized regardless of network location.

#### Core Principles

| Principle | Implementation |
|-----------|----------------|
| Verify explicitly | Authenticate every request with identity, location, device health |
| Least privilege | Just-in-time and just-enough access (JIT/JEA) |
| Assume breach | Segment access, encrypt end-to-end, use analytics |

#### Implementation Components

```
ZERO TRUST ARCHITECTURE

┌─────────────────────────────────────────────────────────────┐
│                        CONTROL PLANE                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Identity   │  │    Policy    │  │   Threat     │      │
│  │   Provider   │  │    Engine    │  │  Intelligence│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Policy Decision │
                    │   Point (PDP)     │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                        DATA PLANE                            │
│  ┌──────────────┐                      ┌──────────────┐     │
│  │    User      │──── PEP ────────────▶│   Resource   │     │
│  │   Device     │      │               │   (App/Data) │     │
│  └──────────────┘      │               └──────────────┘     │
│                   Policy Enforcement                         │
│                   Point (PEP)                               │
└─────────────────────────────────────────────────────────────┘
```

#### Authentication Flow

```python
# Zero Trust authentication middleware
import jwt
from functools import wraps

def zero_trust_auth(required_claims=None):
    """
    Verify every request against identity, device, and context.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')

            # 1. Verify token signature and expiration
            try:
                payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
            except jwt.InvalidTokenError:
                return {'error': 'Invalid token'}, 401

            # 2. Verify device compliance
            device_id = request.headers.get('X-Device-ID')
            if not verify_device_compliance(device_id, payload['user_id']):
                return {'error': 'Device not compliant'}, 403

            # 3. Verify location/network context
            client_ip = request.remote_addr
            if not verify_network_context(client_ip, payload['allowed_networks']):
                return {'error': 'Network context invalid'}, 403

            # 4. Verify required claims
            if required_claims:
                for claim in required_claims:
                    if claim not in payload:
                        return {'error': f'Missing claim: {claim}'}, 403

            # 5. Log access for analytics
            log_access_attempt(payload, request, 'allowed')

            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/api/sensitive-data')
@zero_trust_auth(required_claims=['data:read', 'clearance:secret'])
def get_sensitive_data():
    return fetch_data()
```

#### Network Segmentation

| Segment | Access Level | Controls |
|---------|--------------|----------|
| DMZ | Public | WAF, DDoS protection, rate limiting |
| Application | Authenticated users | mTLS, service mesh, RBAC |
| Data | Authorized services only | Encryption, audit logging, DLP |
| Management | Privileged admins | PAM, MFA, session recording |

---

### Defense in Depth

Multiple layers of security controls so failure of one doesn't compromise the system.

#### Security Layers

```
DEFENSE IN DEPTH LAYERS

┌─────────────────────────────────────────────────────────────┐
│  Layer 1: PERIMETER                                          │
│  - Firewall, WAF, DDoS mitigation, DNS filtering            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: NETWORK                                            │
│  - Segmentation, IDS/IPS, network monitoring, VPN           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: HOST                                               │
│  - Endpoint protection, hardening, patching, logging        │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: APPLICATION                                        │
│  - Input validation, authentication, secure coding, SAST    │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: DATA                                               │
│  - Encryption at rest/transit, access controls, DLP, backup │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation Checklist

| Layer | Control | Priority |
|-------|---------|----------|
| Perimeter | Web Application Firewall | Critical |
| Perimeter | Rate limiting | Critical |
| Network | Network segmentation (VLANs) | Critical |
| Network | Intrusion detection system | High |
| Host | Automated patching | Critical |
| Host | Endpoint Detection & Response | High |
| Application | Input validation | Critical |
| Application | Parameterized queries | Critical |
| Data | Encryption at rest (AES-256) | Critical |
| Data | TLS 1.3 for transit | Critical |

#### Fail-Safe Defaults

```python
# Secure default configuration
class SecurityConfig:
    # Authentication
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

    # Headers
    CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self'"
    X_FRAME_OPTIONS = 'DENY'
    X_CONTENT_TYPE_OPTIONS = 'nosniff'
    REFERRER_POLICY = 'strict-origin-when-cross-origin'

    # Timeouts
    SESSION_LIFETIME = 3600  # 1 hour
    TOKEN_EXPIRY = 900  # 15 minutes

    # Rate limiting
    RATE_LIMIT_DEFAULT = '100/hour'
    RATE_LIMIT_AUTH = '10/minute'
```

---

### Secure Authentication Patterns

#### OAuth 2.0 + PKCE Flow

```
OAUTH 2.0 AUTHORIZATION CODE FLOW WITH PKCE

┌──────────┐                                  ┌──────────────┐
│  Client  │                                  │    Auth      │
│  (SPA)   │                                  │   Server     │
└────┬─────┘                                  └──────┬───────┘
     │                                               │
     │ 1. Generate code_verifier (random string)     │
     │    code_challenge = SHA256(code_verifier)     │
     │                                               │
     │ 2. /authorize?                                │
     │    response_type=code&                        │
     │    client_id=xxx&                             │
     │    code_challenge=xxx&                        │
     │    code_challenge_method=S256                 │
     │──────────────────────────────────────────────▶│
     │                                               │
     │◀──────────────────────────────────────────────│
     │ 3. Redirect with authorization_code           │
     │                                               │
     │ 4. POST /token                                │
     │    grant_type=authorization_code&             │
     │    code=xxx&                                  │
     │    code_verifier=xxx  (proves possession)     │
     │──────────────────────────────────────────────▶│
     │                                               │
     │◀──────────────────────────────────────────────│
     │ 5. { access_token, refresh_token, id_token }  │
     │                                               │
```

#### JWT Token Structure

```python
# Secure JWT implementation
import jwt
import secrets
from datetime import datetime, timedelta

class JWTService:
    def __init__(self, private_key, public_key, issuer):
        self.private_key = private_key
        self.public_key = public_key
        self.issuer = issuer

    def create_access_token(self, user_id, roles, expires_minutes=15):
        """Create short-lived access token."""
        now = datetime.utcnow()
        payload = {
            'iss': self.issuer,
            'sub': str(user_id),
            'iat': now,
            'exp': now + timedelta(minutes=expires_minutes),
            'jti': secrets.token_hex(16),  # Unique token ID
            'roles': roles,
            'type': 'access'
        }
        return jwt.encode(payload, self.private_key, algorithm='RS256')

    def create_refresh_token(self, user_id, expires_days=7):
        """Create longer-lived refresh token (stored server-side)."""
        now = datetime.utcnow()
        jti = secrets.token_hex(32)
        payload = {
            'iss': self.issuer,
            'sub': str(user_id),
            'iat': now,
            'exp': now + timedelta(days=expires_days),
            'jti': jti,
            'type': 'refresh'
        }
        # Store jti in database for revocation capability
        store_refresh_token(jti, user_id, now + timedelta(days=expires_days))
        return jwt.encode(payload, self.private_key, algorithm='RS256')

    def verify_token(self, token, token_type='access'):
        """Verify token with all security checks."""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=['RS256'],
                issuer=self.issuer
            )

            # Verify token type
            if payload.get('type') != token_type:
                raise jwt.InvalidTokenError('Invalid token type')

            # For refresh tokens, check revocation
            if token_type == 'refresh':
                if is_token_revoked(payload['jti']):
                    raise jwt.InvalidTokenError('Token revoked')

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError('Token expired')
        except jwt.InvalidTokenError as e:
            raise AuthError(f'Invalid token: {e}')
```

#### Multi-Factor Authentication

| Factor | Examples | Strength |
|--------|----------|----------|
| Knowledge | Password, PIN, security questions | Low-Medium |
| Possession | TOTP app, hardware key, SMS | Medium-High |
| Inherence | Fingerprint, face, voice | High |

```python
# TOTP implementation
import pyotp
import qrcode

class TOTPService:
    def __init__(self, issuer_name):
        self.issuer = issuer_name

    def generate_secret(self):
        """Generate a new TOTP secret for user."""
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret, user_email):
        """Generate QR code URI for authenticator app."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer
        )

    def verify_code(self, secret, code, valid_window=1):
        """Verify TOTP code with time drift tolerance."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=valid_window)
```

---

### API Security Patterns

#### Input Validation

```python
from pydantic import BaseModel, validator, constr
import re

class UserCreateRequest(BaseModel):
    """Strict input validation for user creation."""

    email: constr(max_length=255)
    username: constr(min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
    password: constr(min_length=12, max_length=128)

    @validator('email')
    def validate_email(cls, v):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError('Invalid email format')
        return v.lower()

    @validator('password')
    def validate_password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')
        return v
```

#### Rate Limiting

```python
from redis import Redis
from functools import wraps
import time

class RateLimiter:
    """Token bucket rate limiter with Redis backend."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def is_allowed(self, key, limit, window_seconds):
        """Check if request is within rate limit."""
        pipe = self.redis.pipeline()
        now = time.time()
        window_start = now - window_seconds

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries
        pipe.zcard(key)
        # Add new entry
        pipe.zadd(key, {str(now): now})
        # Set expiry
        pipe.expire(key, window_seconds)

        results = pipe.execute()
        current_count = results[1]

        return current_count < limit

def rate_limit(limit=100, window=3600, key_func=None):
    """Rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if key_func:
                key = f"rate_limit:{key_func()}"
            else:
                key = f"rate_limit:{request.remote_addr}:{f.__name__}"

            if not rate_limiter.is_allowed(key, limit, window):
                return {
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }, 429

            return f(*args, **kwargs)
        return decorated
    return decorator
```

#### SQL Injection Prevention

```python
# NEVER: String concatenation
# query = f"SELECT * FROM users WHERE id = {user_id}"

# ALWAYS: Parameterized queries
from sqlalchemy import text

def get_user_secure(user_id):
    """Safe parameterized query."""
    query = text("SELECT * FROM users WHERE id = :user_id")
    result = db.execute(query, {'user_id': user_id})
    return result.fetchone()

# For dynamic queries, use ORM
def search_users(filters):
    """Safe dynamic query with ORM."""
    query = User.query

    if 'name' in filters:
        # ORM handles escaping
        query = query.filter(User.name.ilike(f"%{filters['name']}%"))

    if 'role' in filters:
        query = query.filter(User.role == filters['role'])

    return query.all()
```

---

### Data Protection Patterns

#### Encryption at Rest

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class FieldEncryption:
    """Encrypt sensitive database fields."""

    def __init__(self, master_key):
        self.fernet = Fernet(master_key)

    @staticmethod
    def derive_key(password, salt):
        """Derive encryption key from password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, plaintext):
        """Encrypt a field value."""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        return self.fernet.encrypt(plaintext).decode()

    def decrypt(self, ciphertext):
        """Decrypt a field value."""
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode()
        return self.fernet.decrypt(ciphertext).decode()

# Usage in ORM
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255))  # Not sensitive
    _ssn = db.Column('ssn', db.String(500))  # Encrypted

    @property
    def ssn(self):
        if self._ssn:
            return field_encryption.decrypt(self._ssn)
        return None

    @ssn.setter
    def ssn(self, value):
        if value:
            self._ssn = field_encryption.encrypt(value)
        else:
            self._ssn = None
```

#### Secret Management

| Storage Type | Use Case | Example |
|--------------|----------|---------|
| Environment variables | Container config | `DATABASE_URL` |
| Secret manager | Application secrets | AWS Secrets Manager, HashiCorp Vault |
| Hardware Security Module | Cryptographic keys | AWS CloudHSM |

```python
# HashiCorp Vault integration
import hvac

class VaultClient:
    def __init__(self, url, token):
        self.client = hvac.Client(url=url, token=token)

    def get_secret(self, path):
        """Retrieve secret from Vault."""
        secret = self.client.secrets.kv.v2.read_secret_version(path=path)
        return secret['data']['data']

    def get_database_credentials(self, role):
        """Get dynamic database credentials."""
        creds = self.client.secrets.database.generate_credentials(role)
        return {
            'username': creds['data']['username'],
            'password': creds['data']['password'],
            'ttl': creds['lease_duration']
        }
```

---

### Security Anti-Patterns

#### Anti-Pattern: Security Through Obscurity

| Bad Practice | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| Custom encryption algorithm | Untested, likely breakable | Use AES-256-GCM, ChaCha20-Poly1305 |
| Hidden admin URLs | Discovery via fuzzing | Proper authentication + authorization |
| Encoded (not encrypted) secrets | Base64 is reversible | Use proper encryption |

#### Anti-Pattern: Trusting Client Input

```python
# BAD: Trusting client-provided data
@app.route('/admin')
def admin_panel():
    # Client can forge this header!
    if request.headers.get('X-Is-Admin') == 'true':
        return render_admin()

# GOOD: Server-side verification
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.has_role('admin'):
        abort(403)
    return render_admin()
```

#### Anti-Pattern: Hardcoded Secrets

```python
# BAD: Hardcoded credentials
DATABASE_URL = "postgresql://admin:SuperSecret123@localhost/db"
API_KEY = "sk-1234567890abcdef"

# GOOD: Environment variables + secret management
import os
DATABASE_URL = os.environ['DATABASE_URL']
API_KEY = vault_client.get_secret('api/keys')['api_key']
```

#### Anti-Pattern: Verbose Error Messages

```python
# BAD: Reveals internal information
except Exception as e:
    return {'error': str(e), 'stack_trace': traceback.format_exc()}, 500

# GOOD: Generic message, detailed logging
except Exception as e:
    logger.exception(f"Internal error: {e}")
    return {'error': 'An internal error occurred', 'request_id': request_id}, 500
```

---

### Security Tools Reference

| Category | Tools |
|----------|-------|
| SAST (Static Analysis) | Semgrep, SonarQube, Bandit (Python), ESLint security plugins |
| DAST (Dynamic Analysis) | OWASP ZAP, Burp Suite, Nikto |
| Dependency Scanning | Snyk, Dependabot, npm audit, pip-audit |
| Secret Detection | GitLeaks, TruffleHog, detect-secrets |
| Container Security | Trivy, Clair, Anchore |
| Infrastructure | Terraform Sentinel, Checkov, tfsec |

---

## Cryptography Implementation Guide

Practical cryptographic patterns for securing data at rest, in transit, and in use.

---

### Table of Contents

- [Cryptographic Primitives](#cryptographic-primitives)
- [Symmetric Encryption](#symmetric-encryption)
- [Asymmetric Encryption](#asymmetric-encryption)
- [Hashing and Password Storage](#hashing-and-password-storage)
- [Key Management](#key-management)
- [Common Cryptographic Mistakes](#common-cryptographic-mistakes)

---

### Cryptographic Primitives

#### Algorithm Selection Guide

| Use Case | Recommended Algorithm | Avoid |
|----------|----------------------|-------|
| Symmetric encryption | AES-256-GCM, ChaCha20-Poly1305 | DES, 3DES, AES-ECB, RC4 |
| Asymmetric encryption | RSA-OAEP (2048+), ECIES | RSA-PKCS1v1.5 |
| Digital signatures | Ed25519, ECDSA P-256, RSA-PSS | RSA-PKCS1v1.5 |
| Key exchange | X25519, ECDH P-256 | RSA key transport |
| Password hashing | Argon2id, bcrypt, scrypt | MD5, SHA-1, plain SHA-256 |
| Message authentication | HMAC-SHA256, Poly1305 | MD5, SHA-1 |
| Random generation | OS CSPRNG | Math.random(), time-based |

#### Security Strength Comparison

| Key Size | Security Level | Equivalent Symmetric |
|----------|----------------|---------------------|
| RSA 2048 | 112 bits | AES-128 |
| RSA 3072 | 128 bits | AES-128 |
| RSA 4096 | 152 bits | AES-192 |
| ECDSA P-256 | 128 bits | AES-128 |
| ECDSA P-384 | 192 bits | AES-192 |
| Ed25519 | 128 bits | AES-128 |

---

### Symmetric Encryption

#### AES-256-GCM Implementation

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

class AESGCMEncryption:
    """
    AES-256-GCM authenticated encryption.

    Provides both confidentiality and integrity.
    GCM mode prevents tampering with authentication tag.
    """

    def __init__(self, key: bytes = None):
        if key is None:
            key = AESGCM.generate_key(bit_length=256)
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes (256 bits)")
        self.key = key
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """
        Encrypt with random nonce.

        Returns: nonce (12 bytes) + ciphertext + tag (16 bytes)
        """
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes, associated_data: bytes = None) -> bytes:
        """
        Decrypt and verify authentication tag.

        Raises InvalidTag if tampered.
        """
        nonce = ciphertext[:12]
        actual_ciphertext = ciphertext[12:]
        return self.aesgcm.decrypt(nonce, actual_ciphertext, associated_data)


# Usage
encryptor = AESGCMEncryption()
plaintext = b"Sensitive data to encrypt"
aad = b"user_id:12345"  # Authenticated but not encrypted

ciphertext = encryptor.encrypt(plaintext, associated_data=aad)
decrypted = encryptor.decrypt(ciphertext, associated_data=aad)
```

#### ChaCha20-Poly1305 Implementation

```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os

class ChaChaEncryption:
    """
    ChaCha20-Poly1305 authenticated encryption.

    Faster than AES on systems without hardware AES support.
    Resistant to timing attacks (constant-time implementation).
    """

    def __init__(self, key: bytes = None):
        if key is None:
            key = ChaCha20Poly1305.generate_key()
        self.key = key
        self.chacha = ChaCha20Poly1305(key)

    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        """Encrypt with random 96-bit nonce."""
        nonce = os.urandom(12)
        ciphertext = self.chacha.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt(self, ciphertext: bytes, associated_data: bytes = None) -> bytes:
        """Decrypt and verify Poly1305 authentication tag."""
        nonce = ciphertext[:12]
        actual_ciphertext = ciphertext[12:]
        return self.chacha.decrypt(nonce, actual_ciphertext, associated_data)
```

#### Envelope Encryption Pattern

```python
"""
Envelope Encryption: Encrypt data with a Data Encryption Key (DEK),
then encrypt DEK with a Key Encryption Key (KEK).

Benefits:
- KEK can be rotated without re-encrypting data
- DEK can be stored alongside encrypted data
- Enables per-record encryption with different DEKs
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import os
import json
import base64

class EnvelopeEncryption:
    def __init__(self, kek_public_key, kek_private_key=None):
        self.kek_public = kek_public_key
        self.kek_private = kek_private_key

    def encrypt(self, plaintext: bytes) -> dict:
        """
        1. Generate random DEK
        2. Encrypt plaintext with DEK
        3. Encrypt DEK with KEK
        4. Return encrypted DEK + encrypted data
        """
        # Generate Data Encryption Key
        dek = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(dek)

        # Encrypt data with DEK
        nonce = os.urandom(12)
        encrypted_data = aesgcm.encrypt(nonce, plaintext, None)

        # Encrypt DEK with KEK (RSA-OAEP)
        encrypted_dek = self.kek_public.encrypt(
            dek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return {
            'encrypted_dek': base64.b64encode(encrypted_dek).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'ciphertext': base64.b64encode(encrypted_data).decode()
        }

    def decrypt(self, envelope: dict) -> bytes:
        """
        1. Decrypt DEK with KEK
        2. Decrypt data with DEK
        """
        if self.kek_private is None:
            raise ValueError("Private key required for decryption")

        # Decrypt DEK
        encrypted_dek = base64.b64decode(envelope['encrypted_dek'])
        dek = self.kek_private.decrypt(
            encrypted_dek,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Decrypt data
        aesgcm = AESGCM(dek)
        nonce = base64.b64decode(envelope['nonce'])
        ciphertext = base64.b64decode(envelope['ciphertext'])

        return aesgcm.decrypt(nonce, ciphertext, None)
```

---

### Asymmetric Encryption

#### RSA Key Generation and Usage

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

def generate_rsa_keypair(key_size=4096):
    """Generate RSA key pair for encryption/signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size
    )
    public_key = private_key.public_key()

    return private_key, public_key

def serialize_keys(private_key, public_key, password=None):
    """Serialize keys for storage."""
    # Private key (encrypted with password)
    if password:
        encryption = serialization.BestAvailableEncryption(password.encode())
    else:
        encryption = serialization.NoEncryption()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )

    # Public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return private_pem, public_pem

def rsa_encrypt(public_key, plaintext: bytes) -> bytes:
    """RSA-OAEP encryption (for small data like keys)."""
    return public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def rsa_decrypt(private_key, ciphertext: bytes) -> bytes:
    """RSA-OAEP decryption."""
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
```

#### Digital Signatures (Ed25519)

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey
)

class Ed25519Signer:
    """
    Ed25519 digital signatures.

    Fast, secure, and deterministic.
    256-bit keys provide 128-bit security.
    """

    def __init__(self, private_key=None):
        if private_key is None:
            private_key = Ed25519PrivateKey.generate()
        self.private_key = private_key
        self.public_key = private_key.public_key()

    def sign(self, message: bytes) -> bytes:
        """Create digital signature."""
        return self.private_key.sign(message)

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify digital signature."""
        try:
            self.public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def get_public_key_bytes(self) -> bytes:
        """Export public key for verification."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )


# Usage for message signing
signer = Ed25519Signer()
message = b"Important document content"
signature = signer.sign(message)

# Verification (can be done with public key only)
is_valid = signer.verify(message, signature)
```

#### ECDH Key Exchange

```python
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

class X25519KeyExchange:
    """
    X25519 Diffie-Hellman key exchange.

    Used to establish shared secrets over insecure channels.
    """

    def __init__(self):
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

    def get_public_key_bytes(self) -> bytes:
        """Get public key to send to peer."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def derive_shared_key(self, peer_public_key_bytes: bytes,
                          info: bytes = b"") -> bytes:
        """
        Derive shared encryption key from peer's public key.

        Uses HKDF to derive a proper encryption key.
        """
        peer_public_key = x25519.X25519PublicKey.from_public_bytes(
            peer_public_key_bytes
        )

        shared_secret = self.private_key.exchange(peer_public_key)

        # Derive encryption key using HKDF
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=info,
        ).derive(shared_secret)

        return derived_key


# Key exchange example
alice = X25519KeyExchange()
bob = X25519KeyExchange()

# Exchange public keys (can be done over insecure channel)
alice_public = alice.get_public_key_bytes()
bob_public = bob.get_public_key_bytes()

# Both derive the same shared key
alice_shared = alice.derive_shared_key(bob_public, info=b"session-key")
bob_shared = bob.derive_shared_key(alice_public, info=b"session-key")

assert alice_shared == bob_shared  # Same key!
```

---

### Hashing and Password Storage

#### Password Hashing with Argon2

```python
import argon2
from argon2 import PasswordHasher, Type

class SecurePasswordHasher:
    """
    Argon2id password hashing.

    Argon2id combines resistance to:
    - GPU attacks (memory-hard)
    - Side-channel attacks (data-independent)
    """

    def __init__(self):
        # OWASP recommended parameters
        self.hasher = PasswordHasher(
            time_cost=3,        # Iterations
            memory_cost=65536,  # 64 MB
            parallelism=4,      # Threads
            hash_len=32,        # Output length
            type=Type.ID        # Argon2id variant
        )

    def hash_password(self, password: str) -> str:
        """
        Hash password for storage.

        Returns encoded string with algorithm parameters and salt.
        """
        return self.hasher.hash(password)

    def verify_password(self, password: str, hash: str) -> bool:
        """
        Verify password against stored hash.

        Automatically handles timing-safe comparison.
        """
        try:
            self.hasher.verify(hash, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False

    def needs_rehash(self, hash: str) -> bool:
        """Check if hash needs upgrading to current parameters."""
        return self.hasher.check_needs_rehash(hash)


# Usage
hasher = SecurePasswordHasher()

# During registration
password = "user_password_123!"
password_hash = hasher.hash_password(password)
# Store password_hash in database

# During login
stored_hash = password_hash  # From database
if hasher.verify_password("user_password_123!", stored_hash):
    print("Login successful")

    # Check if hash needs upgrading
    if hasher.needs_rehash(stored_hash):
        new_hash = hasher.hash_password(password)
        # Update stored hash
```

#### Bcrypt Alternative

```python
import bcrypt

class BcryptHasher:
    """
    Bcrypt password hashing.

    Well-established, widely supported.
    Use when Argon2 is not available.
    """

    def __init__(self, rounds=12):
        self.rounds = rounds

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self.rounds)
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password: str, hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), hash.encode())
```

#### HMAC for Message Authentication

```python
import hmac
import hashlib
import secrets

def create_hmac(key: bytes, message: bytes) -> bytes:
    """Create HMAC-SHA256 authentication tag."""
    return hmac.new(key, message, hashlib.sha256).digest()

def verify_hmac(key: bytes, message: bytes, tag: bytes) -> bool:
    """Verify HMAC in constant time."""
    expected = hmac.new(key, message, hashlib.sha256).digest()
    return hmac.compare_digest(expected, tag)

# API request signing example
def sign_api_request(secret_key: bytes, method: str, path: str,
                     body: bytes, timestamp: str) -> str:
    """Sign API request for authentication."""
    message = f"{method}\n{path}\n{timestamp}\n".encode() + body
    signature = create_hmac(secret_key, message)
    return signature.hex()
```

---

### Key Management

#### Key Derivation Functions

```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes
import os

def derive_key_pbkdf2(password: str, salt: bytes = None,
                       iterations: int = 600000) -> tuple:
    """
    Derive encryption key from password using PBKDF2.

    NIST recommends minimum 600,000 iterations for PBKDF2-SHA256.
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations
    )

    key = kdf.derive(password.encode())
    return key, salt

def derive_key_scrypt(password: str, salt: bytes = None) -> tuple:
    """
    Derive key using scrypt (memory-hard).

    More resistant to hardware attacks than PBKDF2.
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**17,  # CPU/memory cost
        r=8,      # Block size
        p=1       # Parallelization
    )

    key = kdf.derive(password.encode())
    return key, salt
```

#### Key Rotation Strategy

```python
from datetime import datetime, timedelta
from typing import Dict, Optional
import json

class KeyManager:
    """
    Manage encryption key lifecycle.

    Supports key rotation without data re-encryption.
    """

    def __init__(self, storage_backend):
        self.storage = storage_backend

    def generate_key(self, key_id: str, algorithm: str = 'AES-256-GCM') -> dict:
        """Generate and store new encryption key."""
        key_material = os.urandom(32)

        key_metadata = {
            'key_id': key_id,
            'algorithm': algorithm,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=365)).isoformat(),
            'status': 'active'
        }

        self.storage.store_key(key_id, key_material, key_metadata)
        return key_metadata

    def rotate_key(self, old_key_id: str) -> dict:
        """
        Rotate encryption key.

        1. Mark old key as 'decrypt-only'
        2. Generate new key as 'active'
        3. Old key can still decrypt, new key encrypts
        """
        # Mark old key as decrypt-only
        old_metadata = self.storage.get_key_metadata(old_key_id)
        old_metadata['status'] = 'decrypt-only'
        self.storage.update_key_metadata(old_key_id, old_metadata)

        # Generate new key
        new_key_id = f"{old_key_id.rsplit('_', 1)[0]}_{datetime.utcnow().strftime('%Y%m%d')}"
        return self.generate_key(new_key_id)

    def get_encryption_key(self) -> tuple:
        """Get current active key for encryption."""
        return self.storage.get_active_key()

    def get_decryption_key(self, key_id: str) -> bytes:
        """Get specific key for decryption."""
        return self.storage.get_key(key_id)
```

#### Hardware Security Module Integration

```python
# AWS CloudHSM / KMS integration pattern
import boto3

class AWSKMSProvider:
    """
    AWS KMS integration for key management.

    Keys never leave AWS infrastructure.
    """

    def __init__(self, key_id: str, region: str = 'us-east-1'):
        self.kms = boto3.client('kms', region_name=region)
        self.key_id = key_id

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt using KMS master key."""
        response = self.kms.encrypt(
            KeyId=self.key_id,
            Plaintext=plaintext
        )
        return response['CiphertextBlob']

    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt using KMS master key."""
        response = self.kms.decrypt(
            KeyId=self.key_id,
            CiphertextBlob=ciphertext
        )
        return response['Plaintext']

    def generate_data_key(self) -> tuple:
        """Generate data encryption key."""
        response = self.kms.generate_data_key(
            KeyId=self.key_id,
            KeySpec='AES_256'
        )
        return response['Plaintext'], response['CiphertextBlob']
```

---

### Common Cryptographic Mistakes

#### Mistake 1: Using ECB Mode

```python
# BAD: ECB mode reveals patterns
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def bad_ecb_encrypt(key, plaintext):
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()

# GOOD: Use authenticated encryption (GCM)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def good_gcm_encrypt(key, plaintext):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, None)
```

#### Mistake 2: Reusing Nonces

```python
# BAD: Static nonce
nonce = b"fixed_nonce!"  # NEVER DO THIS

# GOOD: Random nonce per encryption
nonce = os.urandom(12)

# ALSO GOOD: Counter-based nonce (if you can guarantee no repeats)
class NonceCounter:
    def __init__(self):
        self.counter = 0

    def get_nonce(self):
        self.counter += 1
        return self.counter.to_bytes(12, 'big')
```

#### Mistake 3: Rolling Your Own Crypto

```python
# BAD: Custom "encryption"
def bad_encrypt(data, key):
    return bytes([b ^ k for b, k in zip(data, key * len(data))])

# GOOD: Use established libraries
from cryptography.fernet import Fernet

def good_encrypt(data, key):
    f = Fernet(key)
    return f.encrypt(data)
```

#### Mistake 4: Weak Random Generation

```python
import random
import secrets

# BAD: Predictable random
def bad_generate_token():
    return ''.join(random.choices('abcdef0123456789', k=32))

# GOOD: Cryptographically secure
def good_generate_token():
    return secrets.token_hex(16)
```

#### Mistake 5: Timing Attacks in Comparison

```python
# BAD: Early exit reveals length
def bad_compare(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x != y:
            return False
    return True

# GOOD: Constant-time comparison
import hmac

def good_compare(a, b):
    return hmac.compare_digest(a, b)
```

---

### Quick Reference Card

| Operation | Algorithm | Key Size | Notes |
|-----------|-----------|----------|-------|
| Symmetric encryption | AES-256-GCM | 256 bits | Use random 96-bit nonce |
| Alternative encryption | ChaCha20-Poly1305 | 256 bits | Faster on non-AES hardware |
| Asymmetric encryption | RSA-OAEP | 2048+ bits | Only for small data/keys |
| Key exchange | X25519 | 256 bits | Derive key with HKDF |
| Digital signature | Ed25519 | 256 bits | Fast, deterministic |
| Password hashing | Argon2id | - | 64MB memory, 3 iterations |
| Message authentication | HMAC-SHA256 | 256 bits | Use for API signing |
| Key derivation | PBKDF2-SHA256 | - | 600,000+ iterations |
