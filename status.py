"""User Status Lambda

This function consumes API Gateway query string 
parameters and reports back IAM User metadata 
relative to the query string parameter provided.  
It is assumed the query string parameter entered 
is a valid IAM User username.

The tool receives the following arguments via an 
API Gateway event:

    * username : string

The metadata associated with the username is acquired
using the following functions:

    * handler - receives the API Gateway event from AWS invokes subsequent functions
    * status - consumes the username and returns associated IAM User metadata
"""
import boto3
import logging
import sys
from botocore.exceptions import ClientError


def handler(event: dict, context: dict) -> dict:
    """AWS Lambda function handler - consumes api 
    gateway event and responds to query string
    parameter

    Parameters
    ----------
    event: dict
        aws api gateway event
    context: dict
        aws lambda function environment context

    Returns
    -------
    status: dict
        returns metadata relative to queried iam username
    """
    logger = get_logger()
    method = event['httpMethod']
    if method == 'GET':
        logger.info("HTTP GET Request Event: {}".format(event['queryStringParameters']))
        logger.debug(event)
        user = event['queryStringParameters']
        return status(user['username'])
    else:
        #non GET method error
        logger.info("Unsupported HTTP method.")
        logger.debug(event)
        return {
            "statusCode":405,
            "headers" : {},
            "body": "This method is unsupported"
        }#"error"


def status(username: str) -> dict:
    """Consumes a username and returns the following 
    metadata associated with the IAM user account as a 
    dictionary:

        * Username : str
        * Creation date : datetime
        * User id : str
        * User ARN : str
        * Password last used : datetime

    Parameters
    ----------
    username: str
        the username to query for metadata

    Returns
    -------
    user_metadata: dict
        a dictionary with user metadata related to 
        the username parameter
    """
    logger = get_logger()
    if len(username) == 0:
        body = {
            'Error': 'Required username parameter missing'
        }
        user_metadata = {
            'isBase64Encoded': False,
            'statusCode': 400,
            'headers': {'Content-Type': 'text/html'},
            'body': "{}".format(body)
        }
        logger.warn("Username parameter missing")
        logger.debug(username)
        return user_metadata

    client = get_client()
    # Remove quotes from username before invoking the status method
    username = username.replace('"', '')

    try:
        response = client.get_user(
            UserName=username
        )

        username = response['User']['UserName']
        creation_date = response['User']['CreateDate']
        # Fixes datetime.datetime object formatting to make it readable by humans
        creation = creation_date.strftime("%Y-%m-%d %H:%M")
        user_id = response['User']['UserId']
        user_arn = response['User']['Arn']
        pass_date = response['User']['PasswordLastUsed']
        # Fixes datetime.datetime object formatting to make it readable by humans
        pass_last_used = pass_date.strftime("%Y-%m-%d %H:%M")

        body = {
            "Username": username,
            "CreationDate": creation,
            "UserId": user_id,
            "UserARN": user_arn,
            "PasswordLastUsed": pass_last_used
        }

        user_metadata = {
            'isBase64Encoded': False,
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': "{}".format(body)
        }
        logger.info("IAM user account for user {} found with last login on {}".format(username, pass_last_used))
        logger.debug(user_metadata)
        return user_metadata
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':

            body = {
                'Error': e.response['Error']['Message']
            }

            user_metadata = {
                'isBase64Encoded': False,
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': "{}".format(body)
            }
            logger.error("Requested user does not exist")
            logger.debug(user_metadata)
            return user_metadata

        else:

            body = {
                'Error': e.response
            }

            user_metadata = {
                'isBase64Encoded': False,
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': "{}".format(body)
            }
            logger.error("Error: {}".format(e.response))
            logger.debug(user_metadata)
            return user_metadata


def get_client() -> boto3.client:
    """returns a boto3 iam client object

    Returns
    -------
    iam_client: boto3.client
    """
    iam_client = boto3.client('iam')
    return iam_client

def get_logger() -> logging.Logger:
    """Creates a logger with stdout stream handler

    Returns
    -------
    logger
        a python3 logging logger object with a stdout stream handler 
        set to INFO log level

    """
    logger = logging.getLogger("status")
    for h in logger.handlers:
        logger.removeHandler(h)
    h = logging.StreamHandler(sys.stdout)
    FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
    h.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    return logger