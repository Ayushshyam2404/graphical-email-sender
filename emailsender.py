# Simple Graphical Email Sender — Streamlit app (no CSV required)
# Filename: graphical_email_sender_simple.py
#
# Purpose:
# - Send emails that contain a graphic (banner/image) only — no data CSV required.
# - Recipients can be pasted into a textbox (one-per-line or comma-separated) or uploaded as a simple .txt file.
# - You can upload your own image (png/jpg) or generate a simple banner image inside the app.
# - Compose subject + HTML body. The image is embedded inline so it displays inside the email body.
# - Send immediately or schedule for a specific date/time (APScheduler). The app must be running for scheduled jobs.
#
# Requirements:
# pip install streamlit pillow apscheduler
#
# Run:
# streamlit run graphical_email_sender_simple.py

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time

st.set_page_config(page_title="Simple Graphical Email Sender", layout="wide")

scheduler = BackgroundScheduler()
scheduler.start()

# --- Helper functions ---

def parse_recipients(text):
    # Accepts comma-separated or newline-separated emails
    if not text:
        return []
    # replace commas with newlines, split on newline
    parts = text.replace(',', '\n').split('\n')
    emails = [p.strip() for p in parts if p.strip()]
    return emails


def generate_banner(text, width=800, height=200, bgcolor=(30,144,255), text_color=(255,255,255)):
    # Create a simple banner with centered text using PIL
    img = Image.new('RGB', (width, height), color=bgcolor)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", size=40)
    except Exception:
        # fallback to default PIL font if arial not available
        font = ImageFont.load_default()
    text_w, text_h = draw.textsize(text, font=font)
    x = (width - text_w) / 2
    y = (height - text_h) / 2
    draw.text((x, y), text, font=font, fill=text_color)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def send_email_with_image(smtp_server, smtp_port, username, password, recipients, subject, html_body, image_buffer, image_cid='banner'):
    if not recipients:
        raise ValueError("No recipients provided")
    msg = MIMEMultipart('related')
    msg['From'] = username
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject

    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)

    if '<img' not in html_body:
        html_body += f"<br><img src=\"cid:{image_cid}\" alt=\"banner\" style=\"max-width:100%;height:auto;\"/>"

    msg_alternative.attach(MIMEText(html_body, 'html'))

    img = MIMEImage(image_buffer.read())
    img.add_header('Content-ID', f"<{image_cid}>")
    img.add_header('Content-Disposition', 'inline', filename='banner.png')
    msg.attach(img)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(username, recipients, msg.as_string())

# --- Streamlit UI ---
st.title("📨 Simple Graphical Email Sender")

with st.sidebar:
    st.markdown("### SMTP settings")
    smtp_server = st.text_input("SMTP server", value="smtp.gmail.com")
    smtp_port = st.number_input("SMTP port", value=587)
    username = st.text_input("Sender email (username)")
    password = st.text_input("Email password or app password", type="password")
    st.markdown("**Tip:** Use app-specific passwords for Gmail/Outlook if you have 2FA enabled.")

st.header("1) Recipients — no CSV needed")
recipients_text = st.text_area("Paste emails (one per line or comma-separated)", height=120, placeholder="alice@example.combob@example.com")
recipients_file = st.file_uploader("Or upload a simple .txt file with one email per line (optional)", type=['txt'])

if recipients_file and not recipients_text:
    try:
        data = recipients_file.read().decode('utf-8')
        recipients_text = data
    except Exception:
        st.error("Could not read uploaded file. Please paste emails or upload a UTF-8 text file.")

recipients = parse_recipients(recipients_text)
if recipients:
    st.success(f"Loaded {len(recipients)} recipients")
    if len(recipients) <= 20:
        st.write(recipients)
    else:
        st.write(f"Showing 20 of {len(recipients)} recipients")
        st.write(recipients[:20])
else:
    st.info("No recipients yet — paste emails above or upload a .txt file.")

st.header("2) Graphic (upload or generate)")
col1, col2 = st.columns(2)
with col1:
    uploaded_image = st.file_uploader("Upload an image to include in the email (png/jpg)", type=['png','jpg','jpeg'])
    if uploaded_image:
        img_buf = BytesIO(uploaded_image.read())
        st.image(img_buf)
        img_buf.seek(0)
    else:
        img_buf = None

with col2:
    st.markdown("**Or generate a simple banner**")
    banner_text = st.text_input("Banner text", value="Your Business Name — Latest News")
    bg_hex = st.text_input("Background color (hex)", value="#1E90FF")
    generate_button = st.button("Generate banner")
    if generate_button:
        # convert hex to RGB
        try:
            bg_hex_clean = bg_hex.lstrip('#')
            bgcolor = tuple(int(bg_hex_clean[i:i+2], 16) for i in (0, 2, 4))
        except Exception:
            bgcolor = (30,144,255)
        img_buf = generate_banner(banner_text, bgcolor=bgcolor)
        st.image(img_buf)
        img_buf.seek(0)

st.header("3) Compose email")
subject = st.text_input("Subject", value="Hello from Our Business")
html_body = st.text_area("HTML body (will append image if you don't include <img src='cid:banner'/>)", value="<p>Hi there,</p><p>See our latest update below.</p>")

st.header("4) Send or Schedule")
col3, col4 = st.columns(2)
with col3:
    send_now = st.button("Send Now")
with col4:
    schedule_dt = st.date_input("Schedule date")
    schedule_time = st.time_input("Schedule time")
    schedule_button = st.button("Schedule Send")

# --- Actions ---
if send_now:
    if not (username and password):
        st.error("Provide SMTP settings before sending.")
    elif not recipients:
        st.error("Add recipients before sending.")
    elif not img_buf:
        st.error("Provide or generate a graphic before sending.")
    else:
        try:
            img_buf.seek(0)
            send_email_with_image(smtp_server, smtp_port, username, password, recipients, subject, html_body, img_buf)
            st.success(f"Emails sent to {len(recipients)} recipients")
        except Exception as e:
            st.error(f"Failed to send: {e}")

if schedule_button:
    if not (username and password):
        st.error("Provide SMTP settings before scheduling.")
    elif not recipients:
        st.error("Add recipients before scheduling.")
    elif not img_buf:
        st.error("Provide or generate a graphic before scheduling.")
    else:
        run_dt = datetime.combine(schedule_dt, schedule_time)
        run_dt = run_dt.replace(second=0, microsecond=0)
        if run_dt <= datetime.now():
            st.error("Scheduled time must be in the future")
        else:
            job_id = f"send_job_{int(time.time())}"

            def job_func(smtp_server=smtp_server, smtp_port=smtp_port, username=username, password=password, recipients=recipients, subject=subject, html_body=html_body, img_buf=img_buf):
                try:
                    img_buf.seek(0)
                    send_email_with_image(smtp_server, smtp_port, username, password, recipients, subject, html_body, img_buf)
                except Exception as e:
                    print(f"Scheduled job failed: {e}")

            scheduler.add_job(job_func, 'date', run_date=run_dt, id=job_id)
            st.success(f"Scheduled email job for {run_dt}")

st.markdown("---")
st.markdown("**Notes:** The app must remain running for scheduled sends. Use app passwords for providers with 2FA and respect anti-spam rules.")

# keep the scheduler alive while Streamlit runs (no-op loop to satisfy some environments)
try:
    while False:
        time.sleep(1)
except KeyboardInterrupt:
    pass
