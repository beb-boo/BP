"""Notification delivery safeguards for test and dummy recipients."""

from app.utils import notification


class TestEmailDeliveryGuards:
    def test_mock_email_for_reserved_test_domain(self, monkeypatch):
        monkeypatch.setenv("DISABLE_EMAIL_DELIVERY", "false")
        monkeypatch.setenv("TESTING", "false")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setattr(notification, "EMAIL_USER", "sender@gmail.com")
        monkeypatch.setattr(notification, "EMAIL_PASSWORD", "secret")
        called = {"smtp": False}

        def fail_if_called(*_args, **_kwargs):
            called["smtp"] = True
            raise AssertionError("SMTP should not be used for reserved test domains")

        monkeypatch.setattr(notification.smtplib, "SMTP", fail_if_called)

        assert notification.send_email_otp("demo@test.com", "1234", "registration") is True
        assert called["smtp"] is False

    def test_allow_real_domain_when_guards_are_off(self, monkeypatch):
        monkeypatch.setenv("DISABLE_EMAIL_DELIVERY", "false")
        monkeypatch.setenv("TESTING", "false")
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setattr(notification, "EMAIL_USER", "sender@gmail.com")
        monkeypatch.setattr(notification, "EMAIL_PASSWORD", "secret")
        called = {"smtp": False}

        class DummySMTP:
            def __init__(self, *_args, **_kwargs):
                called["smtp"] = True

            def starttls(self):
                return None

            def login(self, *_args, **_kwargs):
                return None

            def sendmail(self, *_args, **_kwargs):
                return None

            def quit(self):
                return None

        monkeypatch.setattr(notification.smtplib, "SMTP", DummySMTP)

        assert notification.send_email_otp("realuser@gmail.com", "1234", "registration") is True
        assert called["smtp"] is True

    def test_send_email_otp_skips_smtp_during_tests(self, monkeypatch):
        called = {"smtp": False}

        def fail_if_called(*_args, **_kwargs):
            called["smtp"] = True
            raise AssertionError("SMTP should not be used during tests")

        monkeypatch.setattr(notification.smtplib, "SMTP", fail_if_called)

        assert notification.send_email_otp("someone@gmail.com", "1234", "registration") is True
        assert called["smtp"] is False