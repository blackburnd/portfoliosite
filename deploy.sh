#!/bin/bash

# Secure deployment script for OAuth-enabled portfolio site
# This script deploys with real credentials via Cloud Build substitutions

echo "🚀 Deploying OAuth-enabled portfolio site..."

# Check if environment variables are set
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ] || [ -z "$SECRET_KEY" ]; then
    echo "❌ Error: Required environment variables not set!"
    echo "Please set the following environment variables before running this script:"
    echo "  export GOOGLE_CLIENT_ID='your-actual-client-id'"
    echo "  export GOOGLE_CLIENT_SECRET='your-actual-client-secret'"
    echo "  export SECRET_KEY='your-actual-secret-key'"
    echo "  export ADMIN_PASSWORD='your-actual-admin-password'"
    exit 1
fi

# Deploy with Cloud Build using secure substitution variables
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="\
_SECRET_KEY=$SECRET_KEY,\
_GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID,\
_GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET,\
_AUTHORIZED_EMAILS=blackburnd@gmail.com,\
_ADMIN_PASSWORD=${ADMIN_PASSWORD:-your-admin-password}"

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🔐 OAuth authentication is now enabled at https://blackburnsystems.com"
    echo "📝 Authorized users: blackburnd@gmail.com"
else
    echo "❌ Deployment failed!"
    exit 1
fi
