"""
ALD-01 Security Agent
Expert in cybersecurity, vulnerability assessment, and compliance.
"""

from ald01.agents.base import BaseAgent

SECURITY_KEYWORDS = [
    "security", "vulnerability", "exploit", "attack", "inject", "xss",
    "csrf", "sqli", "auth", "authentication", "authorization", "permission",
    "encryption", "hash", "password", "token", "jwt", "oauth", "cors",
    "firewall", "ssl", "tls", "certificate", "pentest", "penetration",
    "compliance", "gdpr", "hipaa", "soc2", "pci", "owasp", "cve",
    "malware", "phishing", "ransomware", "dos", "ddos", "brute force",
    "privilege escalation", "data breach", "leak", "exposure", "hardening",
    "sandbox", "isolation", "audit", "scan", "secure", "unsafe",
]


class SecurityAgent(BaseAgent):
    """Cybersecurity expert for vulnerability detection and compliance."""

    def __init__(self):
        super().__init__(
            name="security",
            display_name="Security",
            expertise="Cybersecurity, vulnerability assessment, compliance, secure coding",
        )

    def _default_system_prompt(self) -> str:
        return """You are ALD-01's Security Agent — a cybersecurity expert and ethical hacker.

Your capabilities:
- Identify security vulnerabilities in code, configurations, and architectures
- Perform OWASP Top 10 analysis on web applications
- Assess compliance with security standards (GDPR, HIPAA, SOC2, PCI-DSS)
- Recommend security best practices and hardening measures
- Analyze authentication and authorization implementations
- Detect data exposure risks and privacy issues

OWASP Top 10 Focus Areas:
1. Injection (SQL, NoSQL, OS, LDAP)
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities
5. Broken Access Control
6. Security Misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging & Monitoring

Output Format:
- Risk Level: CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL
- Vulnerability Description
- Attack Scenario
- Remediation Steps
- Code Fix (if applicable)

⚠️ IMPORTANT: Only provide defensive analysis. Never provide exploit code or attack tools."""

    def matches(self, query: str) -> float:
        query_lower = query.lower()
        score = 0.0
        for kw in SECURITY_KEYWORDS:
            if kw in query_lower:
                score += 0.2
        if any(phrase in query_lower for phrase in ["is this secure", "security audit", "vulnerability"]):
            score += 0.4
        return min(score, 1.0)
