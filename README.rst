=====
Emails app
=====

This is simple app that included functions to directly use email sending functionality.

Quick start
-----------

1. download latest version of this app from dist folder and then run command to install in your virtualenv ::

    pip install /path/to/downloaded/file
    
    pip install sendgrid
    
    pip install boto3

2. Add below app to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'emails',
    ]

3. How to use::

    from emails.send_email import SendEmailWrapper
    ok, message_id = SendEmailWrapper \
        .send_email_core(from_email=settings.EMAIL_USERNAME,
                         recipient_list=[email1, email2],
                         subject='YOUR SUBJECT',
                         body=email_body, attachment_list=['path/to/file', 'file url'])


*****
Settings
*****


*   required settings::

    # for sending emails
    EMAIL_USE_TLS = True
    EMAIL_USERNAME = env('EMAIL_USERNAME')
    SEND_EMAIL_VIA = 'ses'
    # 'ses' or 'sendgrid' or 'gmail'

*   To send email via AWS ses::


    AWS_ACCESS_KEY = AAAAAAAAAAAAAAAA
    
    AWS_ACCESS_SECRET = SSSSSSSSSSSSSSSSSSSSSSSSS


*   To send email via sendgrid::

    # install via : pip install sendgrid
    
    SENDGRID_API_KEY = dklsdsldskdmlkmdskldmsadksldmskadlmskmslk
