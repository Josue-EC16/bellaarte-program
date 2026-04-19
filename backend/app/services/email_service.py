import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_welcome_email(recipient_email: str, full_name: str, username: str, initial_password: str) -> None:
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning(f"SMTP credentials not configured. Email to {recipient_email} aborted.")
        print(f"--- MOCK EMAIL TO: {recipient_email} ---")
        print(f"Username: {username}\nPassword: {initial_password}")
        print("-----------------------------------------")
        return

    subject = "🎉 ¡BIENVENIDO A BELLAARTE BOUTIQUE! 💖"
    
    # Versión HTML del correo
    html_content = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
            <div style="background-color: #ffffff; padding: 25px; text-align: center; border-bottom: 3px solid #f9f9f9;">
                <img src="cid:logo_bellaarte" alt="BellaArte Boutique" style="max-width: 250px; height: auto;">
            </div>
            <div style="padding: 40px; background-color: #ffffff;">
                <h2 style="color: #d4a373; margin-top: 0; font-size: 24px;">¡Hola {full_name}! 👋</h2>
                <p style="font-size: 16px;">✨ ¡Bienvenido al equipo de <b>BellaArte Boutique</b>! Tu cuenta de acceso al sistema ha sido creada exitosamente.</p>
                
                <div style="background-color: #fff9f3; padding: 25px; border-radius: 12px; border: 1px dashed #d4a373; margin: 30px 0;">
                    <p style="margin: 0 0 15px 0; font-size: 15px; color: #8b5e3c;"><b>Tus credenciales de acceso:</b></p>
                    <p style="margin: 8px 0; font-size: 17px;">👤 <b>Usuario:</b> <code style="background: white; padding: 4px 10px; border-radius: 5px; border: 1px solid #eee;">{username}</code></p>
                    <p style="margin: 8px 0; font-size: 17px;">🔑 <b>Contraseña:</b> <code style="background: white; padding: 4px 10px; border-radius: 5px; border: 1px solid #eee;">{initial_password}</code></p>
                </div>

                <div style="background-color: #fff4f4; padding: 15px; border-radius: 8px; border-left: 5px solid #ff4d4f; margin: 20px 0;">
                    <p style="color: #444; font-size: 14px; margin: 0;">
                        ⚠️ <b>Seguridad Obligatoria:</b> El sistema requerirá que cambies esta contraseña por una nueva y personal la primera vez que inicies sesión.
                    </p>
                </div>

                <p style="margin-top: 35px; font-size: 16px;">💼 Estamos encantados de contar contigo en el equipo de BellaArte Boutique.</p>
                
                <div style="margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px;">
                    <p style="margin: 0; color: #888;">Saludos cordiales,</p>
                    <p style="font-weight: bold; color: #d4a373; margin: 5px 0; font-size: 18px;">El equipo de BellaArte Boutique 💖</p>
                </div>
            </div>
            <div style="background-color: #fcfcfc; padding: 15px; text-align: center; font-size: 12px; color: #aaa; border-top: 1px solid #eee;">
                Este es un sistema de notificación automática. Por favor, no respondas a este correo.
            </div>
        </div>
    </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_username
    msg["To"] = recipient_email
    
    # Establecer contenido principal como HTML
    msg.set_content(f"Hola {full_name}. Bienvenido a BellaArte Boutique. Tu usuario es {username} y tu clave temporal es {initial_password}")
    msg.add_alternative(html_content, subtype="html")

    # Embeber la imagen del logo (CID)
    logo_path = Path("c:/laragon/www/bellaarte-program/frontend/public/logo_bellaarte1.png")
    if logo_path.exists():
        try:
            with open(logo_path, "rb") as f:
                img_data = f.read()
                msg.get_payload()[1].add_related(
                    img_data, 
                    maintype="image", 
                    subtype="png", 
                    cid="logo_bellaarte"
                )
        except Exception as e:
            logger.error(f"Could not attach logo to email: {e}")

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
        logger.info(f"Welcome email sent successfully to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
