import pytest
from pydantic import ValidationError

from application.schemas.moderation_schemas import (
    ReasonSchema,
    UserIdSchema,
    DeleteMessageDaysSchema,
    DurationSchema,
    BanCommandSchema,
    WarnCommandSchema,
    KickCommandSchema,
)


class TestReasonSchema:
    def test_valid_reason_en(self):
        schema = ReasonSchema(value="Test reason for violation")
        assert schema.value == "Test reason for violation"

    def test_valid_reason_ru(self):
        schema = ReasonSchema(value="Тестовая причина нарушения правил")
        assert schema.value == "Тестовая причина нарушения правил"

    def test_invalid_reason_empty(self):
        with pytest.raises(ValidationError):
            ReasonSchema(value="")

    def test_invalid_reason_too_long(self):
        with pytest.raises(ValidationError):
            ReasonSchema(value="x" * 501)

    def test_invalid_reason_with_link(self):
        with pytest.raises(ValidationError):
            ReasonSchema(value="Check https://example.com for details")

    def test_invalid_reason_markdown(self):
        with pytest.raises(ValidationError):
            ReasonSchema(value="Reason with `markdown`")


class TestUserIdSchema:
    def test_valid_user_id(self):
        schema = UserIdSchema(user_id=123456789)
        assert schema.user_id == 123456789

    def test_invalid_user_id_zero(self):
        with pytest.raises(ValidationError):
            UserIdSchema(user_id=0)


class TestDeleteMessageDaysSchema:
    def test_valid_days_default(self):
        schema = DeleteMessageDaysSchema()
        assert schema.delete_message_days == 1

    def test_valid_days_min(self):
        schema = DeleteMessageDaysSchema(delete_message_days=1)
        assert schema.delete_message_days == 1

    def test_valid_days_max(self):
        schema = DeleteMessageDaysSchema(delete_message_days=7)
        assert schema.delete_message_days == 7

    def test_invalid_days_zero(self):
        with pytest.raises(ValidationError):
            DeleteMessageDaysSchema(delete_message_days=0)

    def test_invalid_days_eight(self):
        with pytest.raises(ValidationError):
            DeleteMessageDaysSchema(delete_message_days=8)


class TestDurationSchema:
    def test_valid_duration(self):
        schema = DurationSchema(duration_seconds=3600)
        assert schema.duration_seconds == 3600

    def test_valid_duration_none(self):
        schema = DurationSchema(duration_seconds=None)
        assert schema.duration_seconds is None

    def test_invalid_duration_zero(self):
        with pytest.raises(ValidationError):
            DurationSchema(duration_seconds=0)


class TestBanCommandSchema:
    def test_valid_ban_command(self):
        class MockUser:
            id = 123456789

        schema = BanCommandSchema(
            user=MockUser(),
            reason="Test ban reason",
            delete_message_days=3,
            duration_seconds=86400,
        )
        assert schema.reason == "Test ban reason"
        assert schema.delete_message_days == 3
        assert schema.duration_seconds == 86400

    def test_invalid_ban_reason_with_link(self):
        class MockUser:
            id = 123456789

        with pytest.raises(ValidationError):
            BanCommandSchema(
                user=MockUser(),
                reason="https://discord.gg/invite",
            )


class TestWarnCommandSchema:
    def test_valid_warn_command(self):
        class MockUser:
            id = 123456789

        schema = WarnCommandSchema(
            user=MockUser(),
            reason="Test warn reason",
            duration_seconds=3600,
        )
        assert schema.reason == "Test warn reason"
        assert schema.duration_seconds == 3600


class TestKickCommandSchema:
    def test_valid_kick_command(self):
        class MockUser:
            id = 123456789

        schema = KickCommandSchema(
            user=MockUser(),
            reason="Test kick reason",
        )
        assert schema.reason == "Test kick reason"