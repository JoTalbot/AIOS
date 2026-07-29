
import re


class PIIMasker:
    PHONE_RE = re.compile(r"(?:[+]7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
    EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    CARD_RE = re.compile(r"\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}")
    
    @classmethod
    def mask(cls, text: str) -> str:
        if not text: return text
        text = cls.PHONE_RE.sub("[PHONE]", text)
        text = cls.EMAIL_RE.sub("[EMAIL]", text)
        text = cls.CARD_RE.sub("[CARD]", text)
        return text

pii_masker = PIIMasker()
