#!/bin/bash

# QuickSight Data Export to S3
# Exports anonymized views from Supabase to S3 for QuickSight

PGHOST="db.dgflbnjfuycdbitoxwgs.supabase.co"
PGPORT="6543"
PGUSER="postgres.dgflbnjfuycdbitoxwgs"
PGDATABASE="postgres"
S3_BUCKET="s3://personal-finance-analytics"
DATE=$(date +%Y-%m-%d)

echo "Starting QuickSight data export..."

# Views to export
VIEWS=(
  "vw_transaction_analytics"
  "vw_user_financial_health"
  "vw_ml_model_performance"
  "vw_category_distribution"
  "vw_anomaly_metrics"
  "vw_budget_performance"
  "vw_goal_metrics"
  "vw_system_metrics"
  "vw_user_feedback_analysis"
  "vw_investment_readiness"
)

# Export each view
for view in "${VIEWS[@]}"
do
  echo "Exporting $view..."
  PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE \
    -c "\COPY (SELECT * FROM $view) TO STDOUT CSV HEADER" \
    | aws s3 cp - $S3_BUCKET/$view/$DATE.csv
  
  if [ $? -eq 0 ]; then
    echo "✓ $view exported successfully"
  else
    echo "✗ Failed to export $view"
  fi
done

echo "Export complete! Files available at: $S3_BUCKET"
