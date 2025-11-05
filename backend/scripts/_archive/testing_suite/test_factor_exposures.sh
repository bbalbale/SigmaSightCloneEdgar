#!/usr/bin/env bash
set -euo pipefail

# Simple read-only validation for Factor Exposures endpoints
# - Logs in with demo creds
# - Fetches portfolio_id
# - Validates portfolio factor exposures (expects 7-factor complete set)
# - Validates first 2 positions have 7 factors each

BASE_URL=${BASE_URL:-"http://localhost:8000/api/v1"}
EMAIL=${EMAIL:-"demo_hnw@sigmasight.com"}
PASSWORD=${PASSWORD:-"demo12345"}

echo "Using BASE_URL=$BASE_URL"

echo "Logging in as $EMAIL ..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"'"$EMAIL"'","password":"'"$PASSWORD"'"}' | jq -r .access_token)

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "ERROR: Failed to obtain JWT token. Check credentials and server."
  exit 1
fi

PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/auth/me" | jq -r .portfolio_id)
if [[ -z "$PORTFOLIO_ID" || "$PORTFOLIO_ID" == "null" ]]; then
  echo "ERROR: Failed to resolve portfolio_id from /auth/me"
  exit 1
fi
echo "portfolio_id=$PORTFOLIO_ID"

echo "\n1) Portfolio Factor Exposures"
PF_JSON=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/analytics/portfolio/$PORTFOLIO_ID/factor-exposures")
echo "$PF_JSON" | jq . >/dev/null || { echo "ERROR: Non-JSON response"; exit 1; }

AVAILABLE=$(echo "$PF_JSON" | jq -r .available)
if [[ "$AVAILABLE" != "true" ]]; then
  REASON=$(echo "$PF_JSON" | jq -r .metadata.reason)
  echo "WARN: available=false (reason=$REASON). Exiting with non-zero to surface in CI."
  exit 2
fi

COUNT=$(echo "$PF_JSON" | jq '.factors | length')
echo "Factor count: $COUNT"
if [[ "$COUNT" -ne 7 ]]; then
  echo "ERROR: Expected 7 factors, got $COUNT"
  echo "$PF_JSON" | jq '.factors | map(.name)'
  exit 3
fi

NAMES_OK=$(echo "$PF_JSON" | jq '[.factors[].name] | sort == ["Growth","Low Volatility","Market Beta","Momentum","Quality","Size","Value"]')
if [[ "$NAMES_OK" != "true" ]]; then
  echo "ERROR: Factor names do not match expected 7-factor set"
  echo "$PF_JSON" | jq '[.factors[].name] | sort'
  exit 4
fi
echo "✅ Portfolio exposures: 7-factor complete set verified"

echo "\n2) Position Factor Exposures (first 2 positions)"
POS_JSON=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/analytics/portfolio/$PORTFOLIO_ID/positions/factor-exposures?limit=2&offset=0")
echo "$POS_JSON" | jq . >/dev/null || { echo "ERROR: Non-JSON response"; exit 1; }

P_AVAILABLE=$(echo "$POS_JSON" | jq -r .available)
if [[ "$P_AVAILABLE" != "true" ]]; then
  REASON=$(echo "$POS_JSON" | jq -r .metadata.reason)
  echo "WARN: available=false (reason=$REASON). Exiting with non-zero to surface in CI."
  exit 5
fi

LEN1=$(echo "$POS_JSON" | jq '.positions[0].exposures | length')
LEN2=$(echo "$POS_JSON" | jq '.positions[1].exposures | length')
echo "Exposures lengths: $LEN1, $LEN2"
if [[ "$LEN1" -ne 7 || "$LEN2" -ne 7 ]]; then
  echo "ERROR: Expected 7 factors for each of first two positions"
  echo "$POS_JSON" | jq '.positions[0,1]'
  exit 6
fi

echo "✅ Position exposures: first two positions have 7 factors each"
echo "\nAll checks passed."

