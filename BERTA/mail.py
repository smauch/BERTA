import smtplib, ssl
import codecs
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser

def mail(attachment):
    config = configparser.ConfigParser()
    config.read('config.ini')

    sender_email = config['Mail']['SenderEmail']
    receiver_email = config['Mail']['ReceiverEmail']
    password = config['Mail']['Password']
    host = config['Mail']['Host']
    port = int(config['Mail']['Port'])

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "KIT Sitzplatzreservierung"

    f=codecs.open(attachment, 'r')
    html = f.read()

    content = MIMEText(html, "html")
    message.attach(content)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )