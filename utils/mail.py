import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_otp_email(email, otp):
    """Sends OTP via SMTP with SSL using dynamic site settings or configuration fallback."""
    from models import SiteSettings
    try:
        settings_map = {s.key: s.value for s in SiteSettings.query.all()}
    except Exception:
        settings_map = {}

    smtp_server = settings_map.get('smtp_server') or current_app.config.get('SMTP_SERVER', 'alphatex.bd')
    try:
        smtp_port = int(settings_map.get('smtp_port') or current_app.config.get('SMTP_PORT', 465))
    except (ValueError, TypeError):
        smtp_port = 465
    sender_email = settings_map.get('smtp_username') or current_app.config.get('SMTP_USERNAME', 'no-reply@alphatex.bd')
    sender_password = settings_map.get('smtp_password') or current_app.config.get('SMTP_PASSWORD', 'Hacktanha@24')
    sender_name = settings_map.get('smtp_sender_name') or 'alphatex'
    
    # Create HTML/plain multipart email message
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{sender_name} <{sender_email}>"
    msg['To'] = email
    msg['Subject'] = f"Your alphatex OTP Code: {otp}"
    
    plain_text = f"Your One-Time Password (OTP) for alphatex registration/login is: {otp}\nThis code is valid for 10 minutes. Please do not share it with anyone."
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f6f8;">
        <div style="max-width: 600px; margin: 30px auto; padding: 30px; background-color: #ffffff; border-radius: 8px; border: 1px solid #e1e8ed; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
          <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #111111; font-family: 'Century Gothic', sans-serif; font-size: 1.8rem; font-weight: bold; letter-spacing: 0.12em; text-transform: uppercase; margin: 0;">alphatex</h1>
          </div>
          <h2 style="color: #2c3e50; font-size: 1.4rem; border-bottom: 2px solid #eaeaea; padding-bottom: 10px; margin-top: 0;">One-Time Password (OTP)</h2>
          <p style="font-size: 1rem; color: #555555;">Hello,</p>
          <p style="font-size: 1rem; color: #555555;">You are receiving this email because a request was made for an OTP code for registration, login, or password reset on your account.</p>
          <div style="text-align: center; margin: 35px 0;">
            <span style="font-size: 28px; font-weight: bold; letter-spacing: 6px; background-color: #f7f9fa; padding: 12px 28px; border: 1px solid #dce4ec; border-radius: 6px; color: #111111; display: inline-block;">{otp}</span>
          </div>
          <p style="font-size: 0.9rem; color: #7f8c8d; text-align: center;">This code is valid for <strong>10 minutes</strong>. If you did not request this code, you can safely ignore this email.</p>
          <hr style="border: none; border-top: 1px solid #eaeaea; margin: 30px 0;">
          <p style="font-size: 0.9rem; color: #95a5a6; text-align: center; margin: 0;">&copy; 2026 alphatex. All rights reserved.</p>
        </div>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(plain_text, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        current_app.logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
        current_app.logger.info(f"OTP Email sent successfully to {email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending email: {e}")
        # Always output to console/logs as development fallback
        print(f"\n[EMAIL OTP FALLBACK MOCK] To: {email} -> OTP: {otp}\n", flush=True)
        return False
