# Lambda Authorizer

## Description: 
This package provides cloudformation and python source code for deployment of a Custom Lambda Authorizer for API Gateway. The solution assumes that Cognito is the identity provider and the user will pass the Cognito JWT into the API Authorization request. The goal of the solution is to enforce quota-limit per user identity and role base access based on group memberships. The user has to pass three checks before being authorized to call the API resource. The cloudformation stack will create the following resources:
- Lambda Authorizer function.
- Lambda Layers containing dependencies for the authorizer
- IAM Role for Lambda to read/writte from the dynamoDb tables.
- DynamoDB tables.


Lambda Authorizer will perform the following checks:

[1] - Verify the validity of the JWT

The Authorizer decodes the JWT and verifies the signature and expiration time.
The JWT is extracted from the Authorization request header. The event expected from API gateway would look like the following:
```json
{
  "type": "TOKEN",
  "authorizationToken": "JWTtoken",
  "methodArn": "arn:aws:execute-api:eu-central-1:012345678912:hvavirljld/*/GET/secrets"
}
```
To archieve the output above create a token based authorizer from API Gateway. 

[2] - Verify the user api call quota.

A dynamodb table tracks the number of calls performed from each user and the quota limit.
An example of an item would be:
```json
{
  "PrincipalId": "user1@example.com",
  "CallLimit": 50,
  "Calls": 5
}
```
Access is denied once the user reaches the quota limit. If there is no entry for the user in the table, the authorizer will create a new item and assign a default quota limit. The solution doesn't reset the call at any point in time, for example if you want to apply the quota limit on daily basis, you may implement and run a daily job which resets the calls attribute for the items in the table. For the quota count to work, you should not enable Authorization caching for the authorizer in API Gateway. The email claim serve as user identity, you can change the logic of the lambda in case you wish to use any other claim provided from cognito, like cognito:username, etc.

[3] - Verify that the user is member of any Cognito Group which is allowed to access the resource.

DynamoDb Table: DdbResourceGroupRelationship will keep the mapping between the API Gateway resources and the Cognito Groups that are allowed to access the resources. Following an example item from the table:
```json
{
  "Resource": "/examples",
  "Groups": [
    "Administrators",
    "PowerUsers",
    "Developers"
  ],
}
```
Only users that are member of any of the groups listed above should have access to the API resource 
```/examples```.





## Prerequisits:
Creation of the Cognito User Pool, API Gateway and/or frontend app is not included in this package.
- The Cognito JWT should look as follow:
```json
{
  "at_hash": "jxSwTFJMtH1cmmh_AWkGrQ",
  "sub": "0171b18b-c07c-400c-87a0-dd0157fd6337",
  "aud": "32un998vgv93lt3sd56cff7oqi",
  "cognito:groups": [
    "Administrators",
    "PowerUsers"
  ],
  "event_id": "603b4098-74b3-4eb6-9217-56e7cbfe0354",
  "token_use": "id",
  "auth_time": 1598024835,
  "iss": "https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_jFzGA5opU",
  "cognito:username": "0171b18b-c07c-400c-87a0-dd0157fd6337",
  "exp": 1598028435,
  "iat": 1598024835,
  "email": "user1@example.com"
}
```
- A token based authorizer should be create from API Gateway.
  Event example expected from API Gateway:
```json
    {
    "type": "TOKEN",
    "authorizationToken": "JWTtoken",
    "methodArn": "arn:aws:execute-api:eu-central-1:012345678912:hvavirljld/*/GET/secrets"
    }
```
- Authorization caching should be disabled.
- To return the authorizer response for access denied (403) you need to set the response template for Access Denied Gateway Response of your API to:
  - Response template media type: ```application/json```
  - Response template body: ```{"message":$context.authorizer.errorMessage}```   
- You need to provide the artefact bucket where cloudformation will store the resources code. The bucket must be located in the same region where the stack will be created.

## Deployment commands: 
All deployemnts are done using makefile, following commands are available: 
 - ```make downloadCognitoJWKS```    - downloads Cognito JWKS and packs it with the lambda authorizer code.
                                       providing the JWKS will improve latency of the Authorizer.
 - ```make build```                  - Packages the local artifacts (local paths) that your AWS
                                       CloudFormation template references.      
 - ```make apply```                  - Deploys  the specified AWS CloudFormation template by creating and 
                                       then executing a change set. 
 - ```make deploy```                 - executes make cdownloadCognitoJWKS, make build and make apply
 - ```make destroy```                - destroys cloudformation stack
 - ```make clean```                  - deletes the artifact bucket and removes Cognito JWKS



