import cognitojwt
from cognitojwt.exceptions import CognitoJWTException
import boto3
from dynamodb_json import json_util
import os
from os import path
import re
if path.exists('./jwks.json'):
    os.environ['AWS_COGNITO_JWSK_PATH'] = './jwks.json'

REGION = os.environ['COGNITO_REGION']
USERPOOL_ID = os.environ['USERPOOL_ID']
APP_CLIENT_ID = os.environ['APP_CLIENT_ID']
DDB_USAGE_TABLE = os.environ['DDB_USAGE_TABLE']
DDB_GROUP_TABLE = os.environ['DDB_GROUP_TABLE']
DEFAULT_CALL_LIMIT = os.environ['DEFAULT_CALL_LIMIT']
ddb = None


def on_lambda_load():
    global ddb
    ddb = boto3.client('dynamodb')


def lambda_handler(event, context):
    id_token = event['authorizationToken']
    methodArn = event['methodArn']
    path = returnPath(methodArn)

    try:
        verified_claims: dict = cognitojwt.decode(
            id_token,
            REGION,
            USERPOOL_ID,
            app_client_id=APP_CLIENT_ID,
            testmode=True  # Disable token expiration check for testing purposes
        )

        username = verified_claims['email']
        groups = verified_claims['cognito:groups']
        response = ddb.get_item(TableName=DDB_USAGE_TABLE, Key={'PrincipalId': {'S': username}})

        if 'Item' not in response:
            ddb.put_item(
                TableName=DDB_USAGE_TABLE,
                Item={'PrincipalId': {'S': username}, 'CallLimit': {'N': DEFAULT_CALL_LIMIT}, 'Calls': {'N': '1'}}
                )
        elif int(response['Item']['CallLimit']['N']) > int(response['Item']['Calls']['N']):
            Calls = str(int(response['Item']['Calls']['N']) + 1)
            ddb.update_item(
                TableName=DDB_USAGE_TABLE,
                Key={'PrincipalId': {'S': username}},
                AttributeUpdates={'Calls': {'Value': {'N': Calls}}}
                )
        else:
            errorMsg = "Daily call limit of {} has exceeded for {}".format(response['Item']['CallLimit']['N'], username)
            return deniedResponse(username, 'Deny', methodArn, errorMsg)
        return checkRolePermissions(groups, path, ddb, DDB_GROUP_TABLE, username, methodArn)
    except CognitoJWTException as e:
        return deniedResponse('null', 'Deny', methodArn, str(e))


def allowedResponse(principalId, effect, methodArn):
    policyDocument = generatePolicyDocument(effect, methodArn)
    policy = {
        'principalId': principalId,
        'policyDocument': policyDocument
    }
    return policy


def deniedResponse(principalId, effect, methodArn, error):
    policyDocument = generatePolicyDocument(effect, methodArn)
    policy = {
        'principalId': principalId,
        'policyDocument': policyDocument,
        'context': {
            'errorMessage': error
        }
    }
    return policy


def generatePolicyDocument(effect, methodArn):
    policyDocument = {
                    'Version': "2012-10-17",
                    'Statement': [
                        {
                            'Action': 'execute-api:Invoke',
                            'Resource': [
                                methodArn
                                ],
                            'Effect': effect
                        }
                    ]
                }
    return policyDocument


def returnPath(methodArn):
    delimiters = "/GET", "/POST", "/OPTIONS", "/HEAD", "/PUT", "/DELETE", "/PATCH", "/ANY", "?"
    regexPattern = '|'.join(map(re.escape, delimiters))
    return re.split(regexPattern, methodArn)[1]


def checkRolePermissions(group, path, ddb, DDB_ROLE_TABLE, principalId, methodArn):
    group = set(group)
    groups = ddb.get_item(TableName=DDB_GROUP_TABLE, Key={'Resource': {'S': path}})['Item']['Groups']['L']
    groups = set(json_util.loads(groups))
    if group & groups:
        return allowedResponse(principalId, 'Allow', methodArn)
    else:
        error = "{} is not part of any group which is allowed to access resource: {} ".format(principalId, path)
        return deniedResponse(principalId, 'Deny', methodArn, error)


on_lambda_load()
