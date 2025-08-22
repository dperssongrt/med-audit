import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
# get todays date in format MM_DD_YYYY
from datetime import date


def send_results():
    # Get todays date
    today = date.today()
    today = today.strftime("%m_%d_%Y")


    # Email setup
    msg = MIMEMultipart()
    msg['Subject'] = f'MED Audit for {today}'
    msg['From'] = 'tel_eng_reports@granitevoip.com'
    msg['To'] = 'fpike@granitenet.com'
    cc_recipients = ['dpersson@granitenet.com', 'kegrabhorn@granitenet.com', 'pgreen@granitenet.com', 'smcelroy@granitenet.com' ]
    msg['CC'] = ', '.join(cc_recipients)
    msg.attach(MIMEText('Please see attached Audit for My Eye Dr', 'plain'))


    # Attach CSV file
    filename = f'MED_Audit_{today}.csv'
    with open('results.csv', 'rb') as file:
        part = MIMEApplication(file.read(), Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)

    # Send email via SMTP server
    smtp_server = '172.85.228.6'

    server = smtplib.SMTP(smtp_server, 25)

    all_recipients = [msg['To']] + cc_recipients
    server.send_message(msg, from_addr=msg['From'], to_addrs=all_recipients)
    server.quit()
