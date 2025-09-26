#!/bin/bash

# Database Security Lab Deployment Script
# This script deploys the application to AWS Lambda using SAM

set -e

echo "🚀 Starting Database Security Lab deployment..."

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI is not installed. Please install it first:"
    echo "   https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Set default values
STACK_NAME=${STACK_NAME:-"database-security-lab"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
SECRET_KEY=${SECRET_KEY:-$(openssl rand -base64 32)}

echo "📋 Deployment Configuration:"
echo "   Stack Name: $STACK_NAME"
echo "   AWS Region: $AWS_REGION"
echo "   Secret Key: [HIDDEN]"
echo ""

# Build the application
echo "🔨 Building SAM application..."
sam build

# Deploy the application
echo "🚀 Deploying to AWS..."
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        SecretKey="$SECRET_KEY" \
    --confirm-changeset

# Get the outputs
echo "📊 Getting deployment outputs..."
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseSecurityLabApi`].OutputValue' \
    --output text)

CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionUrl`].OutputValue' \
    --output text)

USERS_TABLE=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`UsersTableName`].OutputValue' \
    --output text)

CONTENT_TABLE=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ContentTableName`].OutputValue' \
    --output text)

ASSETS_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AssetsBucketName`].OutputValue' \
    --output text)

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Application URLs:"
echo "   API Gateway: $API_URL"
echo "   CloudFront:  $CLOUDFRONT_URL"
echo ""
echo "📋 AWS Resources:"
echo "   Users Table:   $USERS_TABLE"
echo "   Content Table: $CONTENT_TABLE"
echo "   Assets Bucket: $ASSETS_BUCKET"
echo ""

# Create admin user
echo "👤 Creating admin user..."
read -p "Enter admin username: " ADMIN_USERNAME
read -s -p "Enter admin password: " ADMIN_PASSWORD
echo ""

# Create admin user using AWS CLI and DynamoDB
HASHED_PASSWORD=$(python3 -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('$ADMIN_PASSWORD'))
")

aws dynamodb put-item \
    --region "$AWS_REGION" \
    --table-name "$USERS_TABLE" \
    --item '{
        "username": {"S": "'$ADMIN_USERNAME'"},
        "email": {"S": "'$ADMIN_USERNAME'@admin.local"},
        "hashed_password": {"S": "'$HASHED_PASSWORD'"},
        "is_admin": {"BOOL": true},
        "is_active": {"BOOL": true},
        "created_at": {"S": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"}
    }'

echo "✅ Admin user created successfully!"
echo ""

# Migrate content
echo "📦 Migrating existing content..."
export CONTENT_TABLE="$CONTENT_TABLE"
export AWS_REGION="$AWS_REGION"

if python3 migrate_content.py; then
    echo "✅ Content migration completed!"
else
    echo "⚠️  Content migration failed. You can run it manually later:"
    echo "   export CONTENT_TABLE=$CONTENT_TABLE"
    echo "   export AWS_REGION=$AWS_REGION"
    echo "   python3 migrate_content.py"
fi

echo ""
echo "🎉 Database Security Lab is now deployed and ready to use!"
echo ""
echo "🔗 Access your application at: $CLOUDFRONT_URL"
echo "👤 Login with username: $ADMIN_USERNAME"
echo ""
echo "📚 Next steps:"
echo "   1. Visit the application URL"
echo "   2. Login with your admin credentials"
echo "   3. Go to the Admin Dashboard to manage content"
echo "   4. Create or edit exercises and steps"
echo ""