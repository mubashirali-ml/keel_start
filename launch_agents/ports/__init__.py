"""Ports (protocols) for every outside service, with fakes (ADR-0011, ADR-0028..ADR-0030, ADR-0038)."""

from .domain_check import DEFAULT_FAKE_TAKEN, DomainChecker, FakeDomainChecker
from .email import EmailSender, FakeEmailSender, Mailer, RecordingMailer, SentEmail
from .entitlements import EntitlementsProvider, StaticEntitlements, UsageCounter
from .hosting import NOT_CONFIGURED_MESSAGE, FakeSiteHost, SiteHost, UnconfiguredSiteHost
from .jobs import InlineJobRunner, JobRegistry, JobRunner
from .notifications import NotificationEvent, Notifier, RecordingNotifier
from .payments import FAKE_WEBHOOK_SECRET, FakePaymentGateway, PaymentGateway, fake_price_id

__all__ = [
    "DEFAULT_FAKE_TAKEN",
    "FAKE_WEBHOOK_SECRET",
    "NOT_CONFIGURED_MESSAGE",
    "DomainChecker",
    "EmailSender",
    "EntitlementsProvider",
    "FakeDomainChecker",
    "FakeEmailSender",
    "FakePaymentGateway",
    "FakeSiteHost",
    "InlineJobRunner",
    "JobRegistry",
    "JobRunner",
    "Mailer",
    "NotificationEvent",
    "Notifier",
    "PaymentGateway",
    "RecordingMailer",
    "RecordingNotifier",
    "SentEmail",
    "SiteHost",
    "StaticEntitlements",
    "UnconfiguredSiteHost",
    "UsageCounter",
    "fake_price_id",
]
