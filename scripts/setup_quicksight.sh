#!/bin/bash

# QuickSight Setup Automation Script
# Run this script to set up Supabase → S3 → QuickSight

set -e

echo "🚀 Starting QuickSight Setup..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "❌ psql not found. Install PostgreSQL client."
    exit 1
fi

echo "✅ Prerequisites OK"

# Step 1: Create S3 Bucket
echo ""
echo "📦 Step 1: Creating S3 bucket..."
BUCKET_NAME="personal-finance-analytics"

if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$BUCKET_NAME" --region us-east-1
    echo "✅ Bucket created: $BUCKET_NAME"
else
    echo "✅ Bucket already exists: $BUCKET_NAME"
fi

# Create folder structure
echo "Creating folder structure..."
for view in vw_transaction_analytics vw_user_financial_health vw_ml_model_performance vw_category_distribution vw_anomaly_metrics vw_budget_performance vw_goal_metrics vw_system_metrics; do
    aws s3api put-object --bucket $BUCKET_NAME --key "$view/" || true
done

# Step 2: Create Anonymized Views in Supabase
echo ""
echo "🗄️  Step 2: Creating anonymized views in Supabase..."
echo "${YELLOW}Please enter your Supabase database password:${NC}"
read -s DB_PASSWORD

PGPASSWORD=$DB_PASSWORD psql \
    -h db.dgflbnjfuycdbitoxwgs.supabase.co \
    -p 6543 \
    -U postgres.dgflbnjfuycdbitoxwgs \
    -d postgres \
    -f infrastructure/quicksight/anonymized_views.sql

if [ $? -eq 0 ]; then
    echo "✅ Views created successfully"
else
    echo "❌ Failed to create views. Check your password and connection."
    exit 1
fi

# Step 3: Create Manifest Files
echo ""
echo "📄 Step 3: Creating manifest files..."

for view in vw_transaction_analytics vw_user_financial_health vw_ml_model_performance; do
    cat > "/tmp/${view}_manifest.json" <<EOF
{
  "fileLocations": [
    {
      "URIPrefixes": [
        "s3://$BUCKET_NAME/$view/"
      ]
    }
  ],
  "globalUploadSettings": {
    "format": "CSV",
    "delimiter": ",",
    "textqualifier": "\"",
    "containsHeader": "true"
  }
}
EOF
    
    aws s3 cp "/tmp/${view}_manifest.json" "s3://$BUCKET_NAME/manifests/${view}_manifest.json"
    echo "✅ Manifest created for $view"
done

# Step 4: Update .env
echo ""
echo "⚙️  Step 4: Updating .env file..."

if ! grep -q "S3_ANALYTICS_BUCKET" .env; then
    echo "" >> .env
    echo "# S3 Analytics" >> .env
    echo "S3_ANALYTICS_BUCKET=$BUCKET_NAME" >> .env
    echo "✅ .env updated"
else
    echo "✅ .env already configured"
fi

# Step 5: Install Dependencies
echo ""
echo "📦 Step 5: Installing backend dependencies..."
cd backend
npm install @aws-sdk/client-s3 --save
cd ..
echo "✅ Dependencies installed"

# Step 6: Test Export
echo ""
echo "🧪 Step 6: Testing data export..."
echo "${YELLOW}Starting backend server...${NC}"
cd backend
npm start &
BACKEND_PID=$!
sleep 5

echo "Waiting for backend to start..."
sleep 3

echo ""
echo "${GREEN}========================================${NC}"
echo "${GREEN}✅ Setup Complete!${NC}"
echo "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Go to AWS QuickSight: https://quicksight.aws.amazon.com/"
echo "2. Grant QuickSight access to S3 bucket: $BUCKET_NAME"
echo "3. Create datasets using manifest URLs:"
echo "   s3://$BUCKET_NAME/manifests/vw_transaction_analytics_manifest.json"
echo "   s3://$BUCKET_NAME/manifests/vw_user_financial_health_manifest.json"
echo "   s3://$BUCKET_NAME/manifests/vw_ml_model_performance_manifest.json"
echo ""
echo "4. Export data by calling:"
echo "   POST http://localhost:3000/api/admin/analytics/export"
echo ""
echo "5. Build your dashboard in QuickSight!"
echo ""

kill $BACKEND_PID 2>/dev/null || true
