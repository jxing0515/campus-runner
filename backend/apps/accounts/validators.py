import re

from django.core.exceptions import ValidationError


class HasLetterAndDigitValidator:
    """密码策略：≥8 位且同时包含字母与数字。"""

    def __call__(self, value):
        self.validate(value)

    def validate(self, password, user=None):
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise ValidationError("密码需同时包含字母和数字。", code="password_no_mix")

    def get_help_text(self):
        return "密码至少 8 位，且需同时包含字母和数字。"
