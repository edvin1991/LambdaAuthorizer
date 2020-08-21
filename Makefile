# CloudFormation Makefile

.ONESHELL:
SHELL := /bin/bash

##Parameters
AWS_REGION			 	?= eu-central-1
COGNITO_REGION		 	?= eu-central-1
STACK_NAME 		  	 	?= LambdaAuthorizer
COGNITO_APP_CLIENT_ID 	?= client-id
COGNITO_USER_POOL_ID	?= eu-central-1_userpool
DEFAULT_CALL_LIMIT		?= 50
ARTEFACT_S3_BUCKET		?= example-bucket
##System paramteres
current_dir 	:=  $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SOURCE_TEMPLATE	:=	$(current_dir)/CloudFormationTemplate.yaml
OUTPUT_TEMPLATE	:=	$(current_dir)/outputtemplate.yaml


downloadCognitoJWKS:
	@wget https://cognito-idp.$(COGNITO_REGION).amazonaws.com/$(COGNITO_USER_POOL_ID)/.well-known/jwks.json \
	-O ./LambdaCode/jwks.json

build: 
	@aws cloudformation package --template-file $(SOURCE_TEMPLATE) \
	 --s3-bucket $(ARTEFACT_S3_BUCKET) \
	 --output-template-file $(OUTPUT_TEMPLATE)

apply: 
	@aws cloudformation deploy \
	--template-file $(OUTPUT_TEMPLATE) \
	--stack-name $(STACK_NAME) \
	--capabilities CAPABILITY_NAMED_IAM \
	--parameter-overrides CognitoAppClientId=$(COGNITO_APP_CLIENT_ID) \
	CognitoUserPoolId=$(COGNITO_USER_POOL_ID) \
	DefaultCallLimit=$(DEFAULT_CALL_LIMIT) \
	CognitoRegion=$(COGNITO_REGION) \
	--region $(AWS_REGION)

deploy: downloadCognitoJWKS build apply

destroy: 
	@aws cloudformation delete-stack \
	--stack-name $(STACK_NAME) \
	--region $(AWS_REGION)

clean:
	@aws s3 rb s3://$(ARTEFACT_S3_BUCKET) --force \
	--region $(AWS_REGION); rm ./LambdaCode/jwks.json $(OUTPUT_TEMPLATE)



	
