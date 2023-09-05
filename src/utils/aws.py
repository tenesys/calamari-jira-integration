import logging
import boto3

import src.utils.settings as settings

ses = boto3.client("ses")


def send_email(subject: str, message: str, addresses: list[str]):
    from_address = settings.get("notification_from_email")
    message = {"Subject": {"Data": subject}, "Body": {"Html": {"Data": message}}}
    ses.send_email(
        Source=from_address,
        Destination={"ToAddresses": addresses},
        Message=message,
    )
    logging.info("Sending email \"%s\" to %s", subject, ", ".join(addresses))

