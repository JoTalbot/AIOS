import re

ENHANCED_PATTERNS = [
    re.compile(r'(?:password|passwd|pwd|secret|token|api_key|apikey|bearer|auth_token)\s*[=:]\s*["\']?[A-Za-z0-9_\-+/=!@#$%^&*]{8,}', re.IGNORECASE),
    re.compile(r'(?:AIzaSy[A-Za-z0-9_\-]{33})'),
    re.compile(r'(?:ghp_[A-Za-z0-9]{36})'),
    re.compile(r'(?:sk-[A-Za-z0-9]{48})'),
    re.compile(r'(?:xox[bsp]-[A-Za-z0-9\-]{10,})'),
    re.compile(r'(?:-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----)', re.IGNORECASE),
    re.compile(r'(?:mongodb(?:\+srv)?:\/\/[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+@[A-Za-z0-9_\-\.]+)', re.IGNORECASE),
    re.compile(r'(?:postgres(?:ql)?:\/\/[A-Za-z0-9_\-]+:[A-Za-z0-9_\-]+@[A-Za-z0-9_\-\.]+)', re.IGNORECASE),
]
