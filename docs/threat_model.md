# Threat Model - AI Support Fabric Lab

## Scope

This threat model covers the AI Support Fabric Lab as an **educational/research environment**. While the lab demonstrates security best practices, it is **not designed for production use** without significant hardening.

## Trust Boundaries

```
┌────────────────────────────────────────────────┐
│         Untrusted External Network             │
└──────────────────┬─────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  Gateway (8080)    │ ← Trust Boundary 1
         └─────────┬──────────┘
                   │
    ┌──────────────┴──────────────┐
    │    Internal Docker Network   │ ← Trust Boundary 2
    │                              │
    │  ┌──────────┐  ┌──────────┐ │
    │  │Telemetry │  │Agentic AI│ │
    │  │Collector │  │  Engine  │ │
    │  └──────────┘  └──────────┘ │
    └──────────────────────────────┘
```

### Trust Boundary 1: Gateway

- **Exposure**: Public-facing (localhost in lab)
- **Trust Level**: Untrusted
- **Controls**: Input validation, rate limiting (future)

### Trust Boundary 2: Internal Services

- **Exposure**: Docker network only
- **Trust Level**: Semi-trusted
- **Controls**: Network isolation, service-to-service auth (future)

## Assets

### High Value Assets

1. **Telemetry Data**
   - Value: Potentially contains sensitive operational data
   - Confidentiality: MEDIUM
   - Integrity: HIGH (affects detection accuracy)
   - Availability: MEDIUM

2. **Detection Logic**
   - Value: Intellectual property, effectiveness depends on secrecy
   - Confidentiality: MEDIUM
   - Integrity: CRITICAL (false positives/negatives)
   - Availability: HIGH

3. **Remediation Plans**
   - Value: Could reveal infrastructure details
   - Confidentiality: MEDIUM
   - Integrity: CRITICAL (wrong remediation causes damage)
   - Availability: HIGH

### Medium Value Assets

4. **Configuration Data**
   - Value: System configuration baselines
   - Confidentiality: LOW (in lab)
   - Integrity: HIGH
   - Availability: MEDIUM

5. **System Availability**
   - Value: Lab must be available for learning
   - Availability: MEDIUM

## Threat Actors

### In-Scope for Lab

1. **Curious Learner**
   - Motivation: Understanding, learning
   - Capability: Low to Medium
   - Intent: Generally benign
   - Threat: Accidental misconfiguration

2. **Security Researcher**
   - Motivation: Find vulnerabilities
   - Capability: Medium to High
   - Intent: Improve security
   - Threat: Discovery of exploitable flaws

### Out-of-Scope (Production Would Consider)

3. **Malicious Insider** (not relevant for isolated lab)
4. **Advanced Persistent Threat** (not relevant for educational tool)
5. **Ransomware Operator** (not relevant for local lab)

## Threat Analysis (STRIDE)

### Spoofing

**T1: Service Impersonation**
- **Threat**: Attacker spoofs telemetry collector or AI engine
- **Impact**: Malicious data injection, false findings
- **Likelihood**: MEDIUM (no service authentication)
- **Severity**: MEDIUM
- **Mitigations**:
  - [ ] Implement service-to-service authentication (mTLS)
  - [ ] Add request signing
  - [x] Docker network isolation (partial mitigation)

**T2: Request ID Spoofing**
- **Threat**: Attacker reuses request IDs for correlation confusion
- **Impact**: Audit trail corruption
- **Likelihood**: LOW
- **Severity**: LOW
- **Mitigations**:
  - [x] Gateway generates UUIDs
  - [x] Validates format

### Tampering

**T3: Telemetry Data Tampering**
- **Threat**: Modify telemetry in transit or at rest
- **Impact**: False detections, missed attacks
- **Likelihood**: LOW (Docker network)
- **Severity**: HIGH
- **Mitigations**:
  - [x] Docker network isolation
  - [ ] TLS for service-to-service (future)
  - [ ] Telemetry signing (future)
  - [ ] Database encryption at rest

**T4: Detection Logic Tampering**
- **Threat**: Modify detector thresholds or logic
- **Impact**: Blind to attacks or excessive false positives
- **Likelihood**: LOW (requires container access)
- **Severity**: CRITICAL
- **Mitigations**:
  - [x] Read-only container filesystems (future)
  - [x] Version control for code
  - [ ] Integrity monitoring

**T5: Remediation Plan Injection**
- **Threat**: Inject malicious commands into remediation plans
- **Impact**: Arbitrary command execution if auto-executed
- **Likelihood**: LOW
- **Severity**: CRITICAL (if automated)
- **Mitigations**:
  - [x] No automatic execution (by design)
  - [x] Human approval required for high-risk steps
  - [ ] Command whitelisting

### Repudiation

**T6: Action Repudiation**
- **Threat**: User denies executing remediation
- **Impact**: Accountability gap
- **Likelihood**: MEDIUM
- **Severity**: LOW (lab context)
- **Mitigations**:
  - [x] Timestamps on all telemetry
  - [ ] Audit logging
  - [ ] User authentication (future)

### Information Disclosure

**T7: Telemetry Data Leakage**
- **Threat**: Unauthorized access to telemetry database
- **Impact**: Exposure of operational data
- **Likelihood**: LOW (local lab)
- **Severity**: MEDIUM
- **Mitigations**:
  - [x] Docker volume isolation
  - [ ] Database encryption
  - [ ] Access controls

**T8: Finding/Remediation Leakage**
- **Threat**: Findings reveal infrastructure details
- **Impact**: Attack surface mapping
- **Likelihood**: LOW
- **Severity**: MEDIUM
- **Mitigations**:
  - [ ] Authentication on API endpoints
  - [ ] Redact sensitive details
  - [x] Network isolation

**T9: API Response Information Leakage**
- **Threat**: Error messages reveal internal details
- **Impact**: Reconnaissance aid
- **Likelihood**: MEDIUM
- **Severity**: LOW
- **Mitigations**:
  - [ ] Generic error messages
  - [ ] Detailed errors only in debug mode

### Denial of Service

**T10: Telemetry Flood**
- **Threat**: Overwhelm collector with telemetry
- **Impact**: Service degradation, detection failures
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM
- **Mitigations**:
  - [ ] Rate limiting
  - [ ] Request size limits
  - [ ] Resource quotas in Docker

**T11: Analysis DoS**
- **Threat**: Trigger expensive analysis repeatedly
- **Impact**: CPU exhaustion
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM
- **Mitigations**:
  - [ ] Rate limit analysis endpoint
  - [ ] Async processing
  - [ ] Request throttling

**T12: Database Exhaustion**
- **Threat**: Fill SQLite database
- **Impact**: Loss of new telemetry
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM
- **Mitigations**:
  - [ ] Automatic telemetry rotation
  - [ ] Disk quotas
  - [ ] Monitoring alerts

### Elevation of Privilege

**T13: Container Escape**
- **Threat**: Escape Docker container to host
- **Impact**: Host compromise
- **Likelihood**: LOW (requires vulnerability)
- **Severity**: CRITICAL
- **Mitigations**:
  - [x] Run containers as non-root (future)
  - [x] AppArmor/SELinux profiles (future)
  - [x] Minimal base images
  - [x] Regular updates

**T14: Privilege Escalation via Remediation**
- **Threat**: Use remediation commands for privilege escalation
- **Impact**: Unauthorized system access
- **Likelihood**: LOW
- **Severity**: HIGH
- **Mitigations**:
  - [x] No automatic execution
  - [x] Approval required flags
  - [ ] Command validation/sanitization

## AI-Specific Threats (OWASP AI Top 10)

### AI01: Prompt Injection

**Not directly applicable** - This lab uses rule-based detection, not LLMs. Future LLM integration must address:
- Telemetry containing prompt injection payloads
- Malicious instructions in telemetry data

### AI02: Insecure Output Handling

**T15: Malicious Remediation Commands**
- **Threat**: AI generates dangerous remediation commands
- **Impact**: System damage if auto-executed
- **Likelihood**: LOW (rules-based)
- **Severity**: CRITICAL
- **Mitigations**:
  - [x] Human-in-the-loop for execution
  - [x] Command review required
  - [ ] Command whitelisting

### AI03: Training Data Poisoning

**Not applicable** - No ML training in lab version

### AI04: Model Denial of Service

**T16: Adversarial Telemetry**
- **Threat**: Craft telemetry that causes detector errors
- **Impact**: Detection failures, crashes
- **Likelihood**: LOW
- **Severity**: MEDIUM
- **Mitigations**:
  - [x] Input validation
  - [x] Exception handling
  - [ ] Anomaly detection on telemetry itself

### AI05: Supply Chain Vulnerabilities

**T17: Malicious Dependencies**
- **Threat**: Compromised Python packages
- **Impact**: Arbitrary code execution
- **Likelihood**: LOW
- **Severity**: CRITICAL
- **Mitigations**:
  - [x] Pin dependency versions
  - [ ] Dependency scanning (Snyk, etc.)
  - [ ] Verify package signatures

### AI06: Sensitive Information Disclosure

**Covered by T7, T8** above

### AI07: Insecure Plugin Design

**Not applicable** - No plugin system

### AI08: Excessive Agency

**T18: Over-Automated Remediation**
- **Threat**: AI executes remediation without human oversight
- **Impact**: Unintended system changes
- **Likelihood**: LOW (by design)
- **Severity**: HIGH
- **Mitigations**:
  - [x] Remediation is guidance-only
  - [x] Approval required for high-risk actions
  - [x] No automatic execution

### AI09: Overreliance

**T19: Blind Trust in Findings**
- **Threat**: Users execute remediation without verification
- **Impact**: False positive damage
- **Likelihood**: MEDIUM
- **Severity**: MEDIUM
- **Mitigations**:
  - [x] Clear severity indicators
  - [x] Evidence provided with findings
  - [x] Educational documentation

### AI10: Model Theft

**Not applicable** - Rules are open-source by design

## Residual Risks

After implementing mitigations, these risks remain:

1. **Container Vulnerabilities**: Zero-day in Docker/kernel
2. **Dependency Vulnerabilities**: Unpatched Python packages
3. **User Error**: Misconfiguration or misuse
4. **Logic Bugs**: Flaws in detection/remediation logic

## Security Controls Summary

### Implemented (Lab)

- [x] Docker network isolation
- [x] Input validation on APIs
- [x] No automatic remediation execution
- [x] Approval flags on high-risk actions
- [x] Timestamps and audit trails
- [x] Health checks

### Recommended for Production

- [ ] Authentication (OAuth2/JWT)
- [ ] Authorization (RBAC)
- [ ] Service-to-service auth (mTLS)
- [ ] TLS/HTTPS everywhere
- [ ] Rate limiting
- [ ] WAF (Web Application Firewall)
- [ ] Database encryption
- [ ] Secrets management (Vault)
- [ ] Comprehensive audit logging
- [ ] SIEM integration
- [ ] Vulnerability scanning
- [ ] Penetration testing

## Incident Response

For the lab environment:

1. **Detection**: Monitor for anomalous behavior
2. **Containment**: Stop affected containers
3. **Eradication**: Rebuild from clean images
4. **Recovery**: Restore from backups
5. **Lessons Learned**: Update threat model

## Compliance Considerations

This lab is **not compliant** with:
- GDPR (if using real user data)
- SOC 2
- HIPAA
- PCI-DSS

**Do not use this lab with real production data or in regulated environments without significant hardening.**

## Assumptions

This threat model assumes:

1. Lab runs on trusted local machine
2. No production data is used
3. No external network access required
4. Users are authorized to run the lab
5. Docker is properly configured and updated

If any assumption is violated, reassess the threat model.

## Review Schedule

This threat model should be reviewed:

- When adding new features
- When integrating real LLMs
- Before any production deployment
- Annually for educational content updates

---

**Last Updated**: 2025-01-15
**Version**: 1.0
**Status**: Educational Lab (Not Production-Ready)
