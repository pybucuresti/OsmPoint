from email.mime.text import MIMEText
import smtplib
import flask


def send_mail(msg_to, msg_subject, msg_body):
    assert isinstance(msg_to, (list, tuple))
    app = flask.current_app
    msg_from = app.config['MAIL_FROM']
    msg = MIMEText(msg_body, 'text', 'utf-8')
    msg['Subject'] = msg_subject
    msg['From'] = msg_from
    msg['To'] = ', '.join(msg_to)

    conn = smtplib.SMTP(app.config['MAIL_SERVER'])
    conn.sendmail(msg_from, msg_to, msg.as_string())
    conn.quit()
