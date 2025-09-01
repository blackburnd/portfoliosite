# OAuth Deployment Credentials
# Copy this file to 'deploy-credentials.sh' and fill in your actual values
# Run: source deploy-credentials.sh && ./deploy.sh

export SECRET_KEY='your-actual-secret-key-here'
export GOOGLE_CLIENT_ID='your-actual-client-id.apps.googleusercontent.com'
export GOOGLE_CLIENT_SECRET='your-actual-client-secret'
export ADMIN_PASSWORD='your-actual-admin-password'

echo "✅ Deployment credentials loaded!"
echo "Now run: ./deploy.sh"
