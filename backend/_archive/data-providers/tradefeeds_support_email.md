# Email to TradeFeeds Support

**To:** support@tradefeeds.com
**Subject:** API Access Whitelisting Request - CAPTCHA Blocking Issue

Dear TradeFeeds Support Team,

I am currently evaluating TradeFeeds as a potential market data provider for our financial analytics platform, SigmaSight. We have an active API subscription (API Key: f3c21e2f919dc81a1df3732506ad9856bd409f13) and are conducting comprehensive testing to assess the platform's capabilities for our production needs.

## Issue Encountered

When attempting to use the API endpoints, particularly the ETF holdings endpoint (`/api/v1/etfholdings`), we are receiving CAPTCHA protection errors:

```
"TradeFeeds API blocked by CAPTCHA protection. Contact TradeFeeds support to whitelist API access."
```

This is preventing us from completing our evaluation of the TradeFeeds platform.

## Our Use Case

**Company:** SigmaSight
**Purpose:** Portfolio analytics and risk management platform
**Testing Scope:** 
- Evaluating mutual fund and ETF holdings data coverage
- Testing API reliability and response times
- Assessing data quality for 170+ funds across major fund families
- Comparing TradeFeeds against other providers (FMP, Polygon) for our needs

**Planned Production Usage:**
- Fetching ETF and mutual fund holdings data
- Daily updates for client portfolios
- Approximately 500-1,000 API calls per day in production
- Caching strategies to minimize API usage

## Request

We kindly request that you:

1. **Whitelist our API key** (f3c21e2f919dc81a1df3732506ad9856bd409f13) to bypass CAPTCHA protection
2. **Whitelist our IP addresses** if needed (we can provide these separately if required)
3. **Enable full API access** for the following endpoints:
   - `/api/v1/etfholdings`
   - `/api/v1/stockprices` 
   - Any other relevant endpoints for fund/ETF data

## Technical Details

- **Environment:** Python 3.11 with aiohttp client
- **Rate Limiting:** We respect the 30 calls/minute limit
- **Error Handling:** Implemented retry logic with exponential backoff
- **Compression:** Brotli support has been added to handle compressed responses

We are eager to complete our evaluation of TradeFeeds and potentially move forward with a long-term partnership. The CAPTCHA blocking is currently the only barrier preventing us from assessing whether TradeFeeds meets our requirements.

Please let us know if you need any additional information or if there are specific steps we should follow to gain proper API access.

Thank you for your assistance.

Best regards,
[Your Name]
[Your Title]
SigmaSight
[Your Contact Information]

---

## Additional Notes for Follow-up (if needed):

If they ask for more details, you can mention:
- You're specifically interested in mutual fund holdings data (which uses 20X credits)
- You're comparing coverage across providers to make a procurement decision
- You have budget allocated for market data and are evaluating multiple providers
- Timeline: Looking to make a decision within the next 1-2 weeks