import base64
import os
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import requests
import sendgrid

from django.conf import settings
from botocore.exceptions import ClientError
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import URLValidator
from sendgrid.helpers.mail import Email, Content, Mail, Attachment


# ------------------------------------------------------------------------------


class SendEmailWrapper:
    """
        Core class for sending email.
    """

    @staticmethod
    def send_email_core(from_email, recipient_list, subject, body, attachment_list={}, configuration_set_name=''):

        if not (len(recipient_list) > 0):
            return True, None

        if settings.SEND_EMAIL_VIA == 'ses':
            # send mail using smtp
            ok, message_id = send_email_ses(from_email, recipient_list, subject, body, attachment_list,
                                            configuration_set_name)

        elif settings.SEND_EMAIL_VIA == 'sendgrid':
            # send mail using smtp
            ok, message_id = send_email_sg(from_email, recipient_list, subject, body, attachment_list)

        elif settings.SEND_EMAIL_VIA == 'gmail':
            # send mail using smtp
            ok, message_id = send_email_smtp(from_email, recipient_list, subject, body, attachment_list)
        else:
            return False

        # if ok:
        #     logger.info("SEND EMAIL CORE: Successful", extra={'extra': {'recipient_list': recipient_list,
        #                                                                 'subject': subject}})

        return ok, message_id


def cleanup_temp_files(file_paths):
    """
    Method to remove files from given file_paths
    :param file_paths: Array containing local file paths
    """
    for path in file_paths:
        try:
            os.remove(path)
        except OSError:
            pass


# Function to send email using smtp
# below settings / env variables should be set to send email using gmail account
# EMAIL_HOSTNAME=http://localhost:3000
# EMAIL_USERNAME=email@gmail.com
# EMAIL_PASSWORD=password_here
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST_USER=email@gmail.com
def send_email_smtp(from_email, recipient_list, subject, body, attachment_list={}):
    # Initialize file paths array
    file_paths = []
    # Forming email message
    msg = EmailMultiAlternatives(subject, body, from_email, recipient_list)

    # Attaching email type as text/html
    msg.attach_alternative(body, "text/html")

    # Adding attachment if specified
    if len(attachment_list) > 0:
        for attachment_name in attachment_list:
            attachment_url = attachment_list[attachment_name]
            # Download the url as a temporary file
            file_value = requests.get(attachment_url)
            file_name = attachment_name + '_T_I_M_E_' + str(time.time())
            temp_url = '/tmp/' + file_name
            # write the file to a temporary path
            with open(temp_url, 'wb') as f:
                f.write(file_value.content)
            file_paths.append(temp_url)

            # Attach file to the email
            part = MIMEApplication(open(temp_url, 'rb').read())
            part.add_header('Content-Disposition', 'attachment', filename=attachment_name)
            msg.attach(part)

    # Sending mail
    msg.send()
    # Call file cleanup function
    cleanup_temp_files(file_paths)
    return True, None


def send_email_ses(from_email, recipient_list, subject, body, attachment_list={}, configuration_set_name=''):
    # Initialize file paths array
    file_paths = []
    # Initiating multipart message
    msg = MIMEMultipart()
    # Adding email subject
    msg['Subject'] = subject
    # Adding from email
    msg['From'] = from_email
    # Specify email recipients
    msg['To'] = ', '.join(recipient_list)
    # Attaching email body
    msg.attach(MIMEText(body, 'html'))

    # Attach email attachments
    if len(attachment_list) > 0:
        # Loop through all attachments
        for attachment_name in attachment_list:
            # Validate if attachment is a valid URL
            validator = URLValidator()
            attachment_url = attachment_list[attachment_name]
            try:
                validator(attachment_url)
            except ValidationError:
                # logger.error("SEND EMAIL CORE: Not a valid attachment url",
                #              extra={'extra': {'attachment_name': attachment_name,
                #                               'attachment_url': attachment_url
                #                               }})
                return False

            # Download the url as a temporary file
            file_value = requests.get(attachment_url)
            file_name = attachment_name + '_T_I_M_E_' + str(time.time())
            temp_url = '/tmp/' + file_name
            # write the file to a temporary path
            with open(temp_url, 'wb') as f:
                f.write(file_value.content)
            file_paths.append(temp_url)

            # Attach file to the email
            part = MIMEApplication(open(temp_url, 'rb').read())
            part.add_header('Content-Disposition', 'attachment', filename=attachment_name)
            msg.attach(part)

    message_id = None
    # Send AWS SES raw email
    try:
        ses = boto3.client(
            'ses',
            region_name='us-west-2',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_ACCESS_SECRET
        )

        response = ses.send_raw_email(RawMessage={'Data': msg.as_string()},
                                      Source=msg['From'],
                                      Destinations=recipient_list,
                                      ConfigurationSetName=configuration_set_name)
        message_id = response['MessageId']
    except ClientError as e:
        # logger.error('Sending email via aws ses failed', extra={
        #     'extra': {
        #         'recipient_list': recipient_list,
        #         'error': e.__dict__,
        #         'subject': subject
        #     }
        # })
        return False, None

    # Call file cleanup function
    cleanup_temp_files(file_paths)
    return True, message_id


def send_email_sg(from_email, recipient_list, subject, body, attachment_list={}):
    from_email = Email(from_email)
    to_email = Email((', '.join(recipient_list)))
    content = Content("text/html", body)

    file_paths = []

    sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)
    mail = Mail(from_email, subject, to_email, content)

    # Adding attachment if specified
    if len(attachment_list) > 0:
        for attachment_name in attachment_list:
            attachment_url = attachment_list[attachment_name]
            # Download the url as a temporary file
            file_value = requests.get(attachment_url)
            file_name = attachment_name + '_T_I_M_E_' + str(time.time())
            temp_url = '/tmp/' + file_name
            # write the file to a temporary path
            with open(temp_url, 'wb') as f:
                f.write(file_value.content)
            file_paths.append(temp_url)

            attachment = Attachment()
            # temp_file = open(temp_url, 'rb').read()
            with open(temp_url, 'rb') as f:
                data = f.read()
                attachment.content = base64.b64encode(data).decode()
            attachment.disposition = "attachment"
            attachment.filename = attachment_name
            mail.add_attachment(attachment)

    response = sg.client.mail.send.post(request_body=mail.get())

    # Call file cleanup function
    cleanup_temp_files(file_paths)

    if response.status_code == 202:
        message_id = response.headers['X-Message-Id']
        return True, message_id
    else:
        # logger.error('Sending email via sendgrid failed', extra={
        #     'extra': {
        #         'recipient_list': recipient_list,
        #         'status_code': response.status_code,
        #         'subject': subject
        #     }
        # })
        return False, None