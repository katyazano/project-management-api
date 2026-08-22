import boto3
from botocore.exceptions import ClientError

from app.config import settings

ses_client = boto3.client(
    "ses",
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def send_share_invite_email(to_email: str, project_name: str, join_link: str) -> None:
    subject = f'You\'ve been invited to the project "{project_name}"'
    body_text = (
        f'You\'ve been invited to collaborate on the project "{project_name}".\n\n'
        f"Click the link below to join (this link expires in 48 hours):\n{join_link}\n\n"
        "If you weren't expecting this invite, you can safely ignore this email."
    )
    body_html = f"""
    <html>
      <body>
        <p>You've been invited to collaborate on the project <strong>{project_name}</strong>.</p>
        <p><a href="{join_link}">Click here to join</a> (this link expires in 48 hours).</p>
        <p>If you weren't expecting this invite, you can safely ignore this email.</p>
      </body>
    </html>
    """

    try:
        ses_client.send_email(
            Source=settings.SES_SENDER_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                    "Html": {"Data": body_html, "Charset": "UTF-8"},
                },
            },
        )
    except ClientError as e:
        # SES failures shouldn't crash the request — the link is still valid
        # and returned in the response even if the email didn't go out.
        print(
            f"[SES] Failed to send invite email to {to_email}: {e.response['Error']['Message']}"
        )
