const puppeteer = require('puppeteer');

async function startMonitoringSession() {
  console.log('🚀 Starting SigmaSight Chat Monitoring Session...');
  
  const browser = await puppeteer.launch({
    headless: false,
    devtools: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  
  // Set up console monitoring
  const consoleMessages = [];
  page.on('console', async msg => {
    const timestamp = new Date().toISOString();
    const type = msg.type();
    const text = msg.text();
    const location = msg.location();
    
    const logEntry = {
      timestamp,
      type,
      text,
      location
    };
    
    consoleMessages.push(logEntry);
    
    // Real-time console output
    console.log(`[${timestamp}] [${type.toUpperCase()}] ${text}`);
    if (location.url) {
      console.log(`  → Location: ${location.url}:${location.lineNumber}`);
    }
  });

  // Set up network monitoring
  const networkRequests = [];
  page.on('request', request => {
    const timestamp = new Date().toISOString();
    const requestInfo = {
      timestamp,
      method: request.method(),
      url: request.url(),
      headers: request.headers(),
      resourceType: request.resourceType()
    };
    
    networkRequests.push(requestInfo);
    
    // Log chat-related requests
    if (request.url().includes('/api/v1/chat') || request.url().includes('/stream')) {
      console.log(`🌐 [${timestamp}] ${request.method()} ${request.url()}`);
    }
  });

  // Set up response monitoring
  page.on('response', response => {
    const timestamp = new Date().toISOString();
    const request = response.request();
    
    // Log chat-related responses
    if (request.url().includes('/api/v1/chat') || request.url().includes('/stream')) {
      console.log(`📨 [${timestamp}] ${response.status()} ${request.url()}`);
    }
  });

  // Set up error monitoring
  page.on('pageerror', error => {
    const timestamp = new Date().toISOString();
    console.error(`💥 [${timestamp}] PAGE ERROR: ${error.message}`);
    console.error(`   Stack: ${error.stack}`);
  });

  // Set up request failure monitoring
  page.on('requestfailed', request => {
    const timestamp = new Date().toISOString();
    console.error(`❌ [${timestamp}] REQUEST FAILED: ${request.method()} ${request.url()}`);
    console.error(`   Failure: ${request.failure().errorText}`);
  });

  console.log('🔗 Navigating to http://localhost:3005...');
  await page.goto('http://localhost:3005', { waitUntil: 'networkidle2' });
  
  console.log('✅ Monitoring session established!');
  console.log('📊 Monitoring:');
  console.log('  - Console logs (all levels)');
  console.log('  - Network requests (focus on /api/v1/chat)');
  console.log('  - JavaScript errors');
  console.log('  - Authentication flows');
  console.log('');
  console.log('🎯 Next steps:');
  console.log('  1. Login with: demo_hnw@sigmasight.com / demo12345');
  console.log('  2. Navigate to portfolio page');
  console.log('  3. Access chat interface');
  console.log('  4. Monitor real-time logs below');
  console.log('');
  console.log('--- LIVE MONITORING STARTED ---');

  // Keep the session alive and periodically report status
  setInterval(() => {
    console.log(`📈 Status: ${consoleMessages.length} console messages, ${networkRequests.length} network requests captured`);
  }, 30000);

  // Save monitoring data every minute
  setInterval(() => {
    const monitoringData = {
      timestamp: new Date().toISOString(),
      consoleMessages: consoleMessages.slice(-100), // Keep last 100
      networkRequests: networkRequests.slice(-50), // Keep last 50
      summary: {
        totalConsoleMessages: consoleMessages.length,
        totalNetworkRequests: networkRequests.length,
        errorCount: consoleMessages.filter(m => m.type === 'error').length,
        warningCount: consoleMessages.filter(m => m.type === 'warning').length
      }
    };
    
    require('fs').writeFileSync(
      '/Users/elliottng/CascadeProjects/SigmaSight-BE/backend/chat_monitoring_report.json',
      JSON.stringify(monitoringData, null, 2)
    );
  }, 60000);

  return { browser, page };
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Monitoring session terminated by user');
  process.exit(0);
});

if (require.main === module) {
  startMonitoringSession().catch(console.error);
}

module.exports = { startMonitoringSession };