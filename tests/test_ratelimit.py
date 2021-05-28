# coding=utf-8
# Python 2 source containing unicode https://www.python.org/dev/peps/pep-0263/
"""
Tests for SMTP server rate limit feature.

Andrew DeOrio <awdeorio@umich.edu>
"""
import textwrap
import time
import sh
import future.backports.email as email
import future.backports.email.parser  # pylint: disable=unused-import
from mailmerge import SendmailClient, MailmergeError

try:
    from unittest import mock  # Python 3
except ImportError:
    import mock  # Python 2

# Python 2 pathlib support requires backport
try:
    from pathlib2 import Path
except ImportError:
    from pathlib import Path

# The sh library triggers lot of false no-member errors
# pylint: disable=no-member


@mock.patch('smtplib.SMTP')
def test_sendmail_ratelimit(mock_SMTP, tmp_path):
    """Verify SMTP library calls."""
    config_path = tmp_path/"server.conf"
    config_path.write_text(textwrap.dedent(u"""\
        [smtp_server]
        host = open-smtp.example.com
        port = 25
        ratelimit = 60
    """))
    sendmail_client = SendmailClient(
        config_path,
        dry_run=False,
    )
    message = email.message_from_string(u"""
        TO: to@test.com
        SUBJECT: Testing mailmerge
        FROM: from@test.com

        Hello world
    """)

    # First message
    retval = sendmail_client.sendmail(
        sender="from@test.com",
        recipients=["to@test.com"],
        message=message,
    )
    assert retval == 0

    # Second message exceeds the rate limit
    retval = sendmail_client.sendmail(
        sender="from@test.com",
        recipients=["to@test.com"],
        message=message,
    )
    assert retval == 1

    # Retry the second message after 1 s because the rate limit is 60 messages
    # per minute
    # FIXME a better way to do this is to mock datetime.datetime.now()
    time.sleep(1.1)
    retval = sendmail_client.sendmail(
        sender="from@test.com",
        recipients=["to@test.com"],
        message=message,
    )
    assert retval == 0


def test_rate_limit(tmpdir):
    """Verify SMTP server ratelimit parameter."""
    # Simple template
    template_path = Path(tmpdir/"mailmerge_template.txt")
    template_path.write_text(textwrap.dedent(u"""\
        TO: {{email}}
        FROM: from@test.com

        Hello world
    """))

    # Simple database with two entries
    database_path = Path(tmpdir/"mailmerge_database.csv")
    database_path.write_text(textwrap.dedent(u"""\
        email
        one@test.com
        two@test.com
    """))

    # Simple unsecure server config
    config_path = Path(tmpdir/"mailmerge_server.conf")
    config_path.write_text(textwrap.dedent(u"""\
        [smtp_server]
        host = open-smtp.example.com
        port = 25
        ratelimit = 1
    """))

    # Run mailmerge
    with tmpdir.as_cwd():
        output = sh.mailmerge("--no-limit")
    assert output.stderr.decode("utf-8") == ""
    assert "message 1 sent" in output
    assert "Rate limit of 1 message per minute hit" in output
    assert "message 2 sent" in output
    assert "This was a dry run" in output
