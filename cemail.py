import smtplib
from email.message import EmailMessage

def send_mail(to,subject,body):
    server = smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('chocojithin@gmail.com','jgdv zfym hwdj taxy')
    msg = EmailMessage()
    msg['From']='chocojithin@gmail.com'
    msg['To']=to
    msg['Subject']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()