# services.py
from utils import APP_BASE_URL

def send_verification_email(to_email: str, token: str):
    """
    Dev helper: prints the verification URL.
    Replace with SMTP or an email provider in production.
    """
    verify_url = f"{APP_BASE_URL}/api/verify-email?token={token}"
    # In production: send email via SMTP / provider.
    print("=== VERIFICATION EMAIL ===")
    print(f"To: {to_email}")
    print("Subject: Verify your email")
    print("Body:")
    print(f"Click to verify: {verify_url}")
    print("==========================")
