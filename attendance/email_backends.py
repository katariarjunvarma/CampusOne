"""
Custom email backend to handle SSL certificate issues on macOS
"""
import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend


class NoVerifySMTPBackend(EmailBackend):
    """
    SMTP backend that doesn't verify SSL certificates.
    Use only for development/testing on systems with certificate issues.
    """
    def open(self):
        if self.connection:
            return False
        try:
            # Create a custom SMTP connection that doesn't verify SSL
            self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            self.connection.ehlo()
            if self.use_tls:
                # Create unverified context for STARTTLS
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.connection.starttls(context=context)
                self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
