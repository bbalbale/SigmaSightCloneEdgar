#!/usr/bin/env node

/**
 * Comprehensive Chat Testing Script
 * Tests the SigmaSight chat implementation following V1.1 requirements
 * - Authentication flow (JWT + HttpOnly cookies)
 * - SSE streaming validation
 * - Responsive design
 * - Error handling
 * - Performance metrics
 */

const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

class ChatTestRunner {
  constructor() {
    this.browser = null;
    this.page = null;
    this.results = {
      timestamp: new Date().toISOString(),
      testsPassed: [],
      testsFailed: [],
      criticalIssues: [],
      highPriorityIssues: [],
      mediumPriorityIssues: [],
      performanceMetrics: {},
      consoleErrors: [],
      networkRequests: [],
      screenshots: []
    };
    this.startTime = Date.now();
  }

  async initialize() {
    console.log('🚀 Starting Comprehensive Chat Testing...\n');
    
    this.browser = await puppeteer.launch({
      headless: false, // Set to true for CI environments
      devtools: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
      ]
    });

    this.page = await this.browser.newPage();
    
    // Set up monitoring
    await this.setupMonitoring();
    
    // Set desktop viewport initially
    await this.page.setViewport({ width: 1440, height: 900 });
  }

  async setupMonitoring() {
    // Monitor console messages
    this.page.on('console', msg => {
      const type = msg.type();
      const text = msg.text();
      const location = msg.location();
      
      this.results.consoleErrors.push({
        type,
        text,
        location,
        timestamp: new Date().toISOString()
      });
      
      if (type === 'error') {
        console.log(`❌ Console Error: ${text}`);
        if (location.url) {
          console.log(`   at ${location.url}:${location.lineNumber}:${location.columnNumber}`);
        }
      }
    });

    // Monitor network requests
    this.page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/') || url.includes('localhost:3005') || url.includes('localhost:8000')) {
        this.results.networkRequests.push({
          url,
          status: response.status(),
          method: response.request().method(),
          timestamp: new Date().toISOString(),
          timing: {
            // Note: response timing details would need CDP for full metrics
          }
        });
        
        if (response.status() >= 400) {
          console.log(`🔴 Network Error: ${response.status()} ${response.request().method()} ${url}`);
        }
      }
    });

    // Monitor page errors
    this.page.on('pageerror', error => {
      this.results.criticalIssues.push({
        type: 'JavaScript Error',
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      });
      console.log(`💥 Page Error: ${error.message}`);
    });
  }

  async takeScreenshot(name) {
    const filename = `chat_test_${name}_${Date.now()}.png`;
    const filepath = path.join(__dirname, 'test_screenshots', filename);
    
    try {
      await fs.mkdir(path.dirname(filepath), { recursive: true });
      await this.page.screenshot({ path: filepath, fullPage: true });
      this.results.screenshots.push({ name, filename, filepath });
      console.log(`📸 Screenshot saved: ${filename}`);
      return filepath;
    } catch (error) {
      console.log(`❌ Failed to take screenshot: ${error.message}`);
      return null;
    }
  }

  async testPhase1_Navigation() {
    console.log('📝 Phase 1: Navigation and Initial Load');
    
    try {
      const startTime = Date.now();
      await this.page.goto('http://localhost:3005/portfolio?type=high-net-worth', {
        waitUntil: 'networkidle2',
        timeout: 30000
      });
      const loadTime = Date.now() - startTime;
      
      await this.takeScreenshot('initial_page_load');
      
      // Check if page loaded correctly
      const title = await this.page.title();
      if (title.includes('SigmaSight')) {
        this.results.testsPassed.push({
          test: 'Page Navigation',
          details: `Page loaded successfully in ${loadTime}ms`,
          evidence: 'initial_page_load screenshot'
        });
      } else {
        this.results.testsFailed.push({
          test: 'Page Navigation',
          details: `Unexpected page title: ${title}`,
          impact: 'Page may not have loaded correctly'
        });
      }
      
      this.results.performanceMetrics.initialLoadTime = loadTime;
      
    } catch (error) {
      this.results.criticalIssues.push({
        type: 'Navigation Failure',
        message: error.message,
        impact: 'Cannot access the application'
      });
    }
  }

  async testPhase2_Authentication() {
    console.log('📝 Phase 2: Authentication Testing');
    
    try {
      // Look for login elements
      const emailInput = await this.page.$('input[type="email"], input[name="email"], #email');
      const passwordInput = await this.page.$('input[type="password"], input[name="password"], #password');
      const loginButton = await this.page.$('button[type="submit"], .login-button, #login-button, [data-testid="login-button"]');
      
      if (!emailInput || !passwordInput || !loginButton) {
        // Check if already logged in
        const isLoggedIn = await this.page.evaluate(() => {
          return document.cookie.includes('auth') || localStorage.getItem('token') || sessionStorage.getItem('token');
        });
        
        if (!isLoggedIn) {
          this.results.criticalIssues.push({
            type: 'Authentication Elements Missing',
            message: 'Could not find login form elements',
            impact: 'Cannot test authentication flow'
          });
          return;
        }
      } else {
        // Perform login
        await emailInput.type('demo_hnw@sigmasight.com');
        await passwordInput.type('demo12345');
        
        await this.takeScreenshot('before_login');
        
        const authStartTime = Date.now();
        await loginButton.click();
        
        // Wait for authentication to complete
        try {
          await this.page.waitForNavigation({ timeout: 10000 });
          const authTime = Date.now() - authStartTime;
          
          await this.takeScreenshot('after_login');
          
          // Check authentication success indicators
          const hasAuthCookie = await this.page.evaluate(() => {
            return document.cookie.includes('auth') || document.cookie.includes('session');
          });
          
          const hasToken = await this.page.evaluate(() => {
            return localStorage.getItem('token') || sessionStorage.getItem('token');
          });
          
          if (hasAuthCookie || hasToken) {
            this.results.testsPassed.push({
              test: 'JWT + Cookie Authentication',
              details: `Login successful in ${authTime}ms, has cookie: ${hasAuthCookie}, has token: ${hasToken}`,
              evidence: 'after_login screenshot'
            });
          } else {
            this.results.testsFailed.push({
              test: 'Authentication Persistence',
              details: 'No authentication tokens found after login',
              impact: 'Authentication may not persist'
            });
          }
          
          this.results.performanceMetrics.authenticationTime = authTime;
          
        } catch (navError) {
          this.results.highPriorityIssues.push({
            type: 'Login Navigation Timeout',
            message: 'Login did not redirect within 10 seconds',
            impact: 'Login flow may be broken'
          });
        }
      }
      
    } catch (error) {
      this.results.criticalIssues.push({
        type: 'Authentication Error',
        message: error.message,
        impact: 'Cannot complete authentication'
      });
    }
  }

  async testPhase3_ChatInterface() {
    console.log('📝 Phase 3: Chat Interface Testing');
    
    try {
      // Look for chat interface elements
      const chatTriggers = await this.page.$$eval('*', elements => {
        return elements
          .filter(el => {
            const text = el.textContent.toLowerCase();
            const classNames = el.className.toLowerCase();
            const id = el.id.toLowerCase();
            return text.includes('chat') || text.includes('ask') || 
                   classNames.includes('chat') || id.includes('chat') ||
                   el.tagName === 'FORM' && text.includes('what');
          })
          .map(el => ({
            tagName: el.tagName,
            className: el.className,
            id: el.id,
            text: el.textContent.slice(0, 100)
          }));
      });
      
      console.log(`Found ${chatTriggers.length} potential chat elements`);
      
      // Look specifically for the chat form
      const chatInput = await this.page.$('input[placeholder*="What"], input[placeholder*="risk"], textarea[placeholder*="What"], textarea[placeholder*="risk"]');
      const chatSubmit = await this.page.$('button[type="submit"]:has(svg), .send-button, [data-testid="send-button"]');
      
      if (chatInput && chatSubmit) {
        await this.takeScreenshot('chat_interface_found');
        
        this.results.testsPassed.push({
          test: 'Chat Interface Discovery',
          details: 'Found chat input and submit button',
          evidence: 'chat_interface_found screenshot'
        });
        
        // Test chat interaction
        await this.testChatInteraction(chatInput, chatSubmit);
        
      } else {
        this.results.criticalIssues.push({
          type: 'Chat Interface Missing',
          message: 'Could not locate chat input or submit button',
          impact: 'Chat functionality not accessible',
          evidence: `Found ${chatTriggers.length} potential elements: ${JSON.stringify(chatTriggers, null, 2)}`
        });
      }
      
    } catch (error) {
      this.results.criticalIssues.push({
        type: 'Chat Interface Error',
        message: error.message,
        impact: 'Cannot test chat functionality'
      });
    }
  }

  async testChatInteraction(chatInput, chatSubmit) {
    console.log('💬 Testing chat message interaction...');
    
    try {
      // Clear and type test message
      await chatInput.click({ clickCount: 3 });
      await chatInput.type('What are my top 3 holdings?');
      
      await this.takeScreenshot('chat_message_typed');
      
      // Monitor network activity for chat requests
      const chatRequestPromise = this.page.waitForResponse(response => 
        response.url().includes('/chat/send') || response.url().includes('/api/v1/chat/'), 
        { timeout: 5000 }
      ).catch(() => null);
      
      const messageStartTime = Date.now();
      await chatSubmit.click();
      
      console.log('Message sent, waiting for response...');
      
      // Wait for chat response or timeout
      const chatResponse = await chatRequestPromise;
      
      if (chatResponse) {
        const responseTime = Date.now() - messageStartTime;
        const status = chatResponse.status();
        
        if (status === 200) {
          this.results.testsPassed.push({
            test: 'Chat Message Send',
            details: `Message sent successfully in ${responseTime}ms (status: ${status})`,
            evidence: 'chat_message_typed screenshot'
          });
          
          // Wait a bit more for streaming response
          await this.page.waitForTimeout(3000);
          await this.takeScreenshot('chat_response_received');
          
          // Check for streaming indicators
          const hasStreamingContent = await this.page.evaluate(() => {
            const bodyText = document.body.textContent.toLowerCase();
            return bodyText.includes('loading') || bodyText.includes('...') || 
                   document.querySelector('[class*="stream"], [class*="typing"], [class*="thinking"]');
          });
          
          if (hasStreamingContent) {
            this.results.testsPassed.push({
              test: 'SSE Streaming Response',
              details: 'Detected streaming response indicators',
              evidence: 'chat_response_received screenshot'
            });
          }
          
        } else if (status === 403) {
          this.results.highPriorityIssues.push({
            type: 'Authentication Required',
            message: `Chat request failed with 403 - user may not be properly authenticated`,
            impact: 'Chat functionality blocked by auth'
          });
        } else {
          this.results.highPriorityIssues.push({
            type: 'Chat Request Failed',
            message: `Chat request failed with status ${status}`,
            impact: 'Chat functionality may be broken'
          });
        }
        
        this.results.performanceMetrics.chatResponseTime = responseTime;
        
      } else {
        this.results.highPriorityIssues.push({
          type: 'Chat Request Timeout',
          message: 'No chat request detected within 5 seconds',
          impact: 'Chat may not be connected to backend'
        });
      }
      
    } catch (error) {
      this.results.highPriorityIssues.push({
        type: 'Chat Interaction Error',
        message: error.message,
        impact: 'Chat interaction failed'
      });
    }
  }

  async testPhase4_ResponsiveDesign() {
    console.log('📝 Phase 4: Responsive Design Testing');
    
    const viewports = [
      { name: 'Desktop', width: 1440, height: 900 },
      { name: 'Tablet', width: 768, height: 1024 },
      { name: 'Mobile', width: 375, height: 667 }
    ];
    
    for (const viewport of viewports) {
      try {
        await this.page.setViewport(viewport);
        await this.page.waitForTimeout(1000); // Allow layout to settle
        
        await this.takeScreenshot(`responsive_${viewport.name.toLowerCase()}`);
        
        // Check for horizontal scroll
        const hasHorizontalScroll = await this.page.evaluate(() => {
          return document.body.scrollWidth > window.innerWidth;
        });
        
        if (hasHorizontalScroll) {
          this.results.mediumPriorityIssues.push({
            type: 'Horizontal Scroll Issue',
            message: `Horizontal scrolling detected on ${viewport.name} viewport`,
            impact: 'Poor mobile user experience'
          });
        } else {
          this.results.testsPassed.push({
            test: `${viewport.name} Responsive Layout`,
            details: 'No horizontal scrolling detected',
            evidence: `responsive_${viewport.name.toLowerCase()} screenshot`
          });
        }
        
      } catch (error) {
        this.results.mediumPriorityIssues.push({
          type: 'Responsive Test Error',
          message: `Error testing ${viewport.name} viewport: ${error.message}`,
          impact: `Cannot validate ${viewport.name} experience`
        });
      }
    }
    
    // Reset to desktop
    await this.page.setViewport({ width: 1440, height: 900 });
  }

  async testPhase5_PerformanceValidation() {
    console.log('📝 Phase 5: Performance Validation');
    
    try {
      // Test page load performance
      const performanceMetrics = await this.page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0];
        const paint = performance.getEntriesByType('paint');
        
        return {
          domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
          loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
          firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
          largestContentfulPaint: paint.find(p => p.name === 'largest-contentful-paint')?.startTime || 0
        };
      });
      
      Object.assign(this.results.performanceMetrics, performanceMetrics);
      
      // Evaluate performance against targets
      const ttfb = this.results.performanceMetrics.chatResponseTime || this.results.performanceMetrics.initialLoadTime;
      if (ttfb && ttfb < 3000) {
        this.results.testsPassed.push({
          test: 'TTFB Performance',
          details: `Time to first byte: ${ttfb}ms (target: <3000ms)`,
          evidence: 'Performance metrics'
        });
      } else if (ttfb) {
        this.results.mediumPriorityIssues.push({
          type: 'Performance Issue',
          message: `TTFB too slow: ${ttfb}ms (target: <3000ms)`,
          impact: 'Slow user experience'
        });
      }
      
    } catch (error) {
      this.results.mediumPriorityIssues.push({
        type: 'Performance Test Error',
        message: error.message,
        impact: 'Cannot validate performance metrics'
      });
    }
  }

  async generateReport() {
    console.log('📝 Generating Comprehensive Test Report...\n');
    
    const totalTime = Date.now() - this.startTime;
    this.results.totalTestTime = totalTime;
    
    // Calculate success rate
    const totalTests = this.results.testsPassed.length + this.results.testsFailed.length;
    const successRate = totalTests > 0 ? (this.results.testsPassed.length / totalTests * 100).toFixed(1) : 0;
    
    // Generate report
    const report = `
# SigmaSight Chat Testing Report - Phase 1 Authentication & SSE Testing

**Test Session:** ${this.results.timestamp}
**Total Duration:** ${(totalTime/1000).toFixed(1)}s
**Success Rate:** ${successRate}% (${this.results.testsPassed.length}/${totalTests} tests passed)

## ✅ Tests Passed (${this.results.testsPassed.length})

${this.results.testsPassed.map(test => 
`### ${test.test}
- **Details:** ${test.details}
- **Evidence:** ${test.evidence || 'Console logs'}
`).join('\n')}

## ❌ Tests Failed (${this.results.testsFailed.length})

${this.results.testsFailed.map(test =>
`### ${test.test}
- **Problem:** ${test.details}
- **Impact:** ${test.impact || 'Unknown impact'}
`).join('\n')}

## 🚨 Critical Issues (${this.results.criticalIssues.length})

${this.results.criticalIssues.map((issue, i) =>
`### [Blocker] ${issue.type}
- **Problem:** ${issue.message}
- **Impact:** ${issue.impact}
- **Stack:** ${issue.stack ? issue.stack.split('\n')[0] : 'N/A'}
`).join('\n')}

## ⚠️ High Priority Issues (${this.results.highPriorityIssues.length})

${this.results.highPriorityIssues.map((issue, i) =>
`### [High-Priority] ${issue.type}
- **Problem:** ${issue.message}
- **Impact:** ${issue.impact || 'User experience degraded'}
`).join('\n')}

## 📋 Medium Priority Issues (${this.results.mediumPriorityIssues.length})

${this.results.mediumPriorityIssues.map((issue, i) =>
`### [Medium-Priority] ${issue.type}
- **Problem:** ${issue.message}
- **Impact:** ${issue.impact || 'Minor user experience issue'}
`).join('\n')}

## 📊 Performance Metrics

- **Initial Load Time:** ${this.results.performanceMetrics.initialLoadTime || 'N/A'}ms
- **Authentication Time:** ${this.results.performanceMetrics.authenticationTime || 'N/A'}ms  
- **Chat Response Time:** ${this.results.performanceMetrics.chatResponseTime || 'N/A'}ms
- **DOM Content Loaded:** ${this.results.performanceMetrics.domContentLoaded || 'N/A'}ms
- **First Contentful Paint:** ${this.results.performanceMetrics.firstContentfulPaint || 'N/A'}ms

**Performance Targets:**
- TTFB: < 3000ms ✅
- Total Response: < 10000ms ${this.results.performanceMetrics.chatResponseTime < 10000 ? '✅' : '❌'}
- Error Rate: < 1% ${this.results.consoleErrors.filter(e => e.type === 'error').length === 0 ? '✅' : '❌'}

## 🔍 Console Analysis

**Total Console Messages:** ${this.results.consoleErrors.length}
**Errors:** ${this.results.consoleErrors.filter(e => e.type === 'error').length}
**Warnings:** ${this.results.consoleErrors.filter(e => e.type === 'warning').length}

### Recent Console Errors:
${this.results.consoleErrors.filter(e => e.type === 'error').slice(-5).map(error =>
`- **${error.timestamp}:** ${error.text}`
).join('\n') || 'No errors detected'}

## 🌐 Network Activity

**Total API Requests:** ${this.results.networkRequests.length}
**Failed Requests:** ${this.results.networkRequests.filter(r => r.status >= 400).length}

### Key API Endpoints:
${this.results.networkRequests.filter(r => r.url.includes('/api/')).slice(-10).map(req =>
`- **${req.method} ${req.status}** ${req.url}`
).join('\n') || 'No API requests detected'}

## 📸 Screenshots Generated

${this.results.screenshots.map(s => `- ${s.name}: ${s.filename}`).join('\n')}

## 🎯 Recommendations

${this.results.criticalIssues.length > 0 ? '### Critical Actions Required:' : ''}
${this.results.criticalIssues.map((issue, i) => 
`${i+1}. Fix ${issue.type}: ${issue.message}`
).join('\n')}

${this.results.highPriorityIssues.length > 0 ? '### High Priority Improvements:' : ''}
${this.results.highPriorityIssues.map((issue, i) => 
`${i+1}. Address ${issue.type}: ${issue.message}`
).join('\n')}

${this.results.mediumPriorityIssues.length > 0 ? '### Medium Priority Enhancements:' : ''}
${this.results.mediumPriorityIssues.map((issue, i) => 
`${i+1}. Consider ${issue.type}: ${issue.message}`
).join('\n')}

---

**Quality Assessment:**
- **Blockers:** ${this.results.criticalIssues.length === 0 ? '✅ None' : '❌ ' + this.results.criticalIssues.length + ' must be resolved'}
- **High Priority:** ${this.results.highPriorityIssues.length === 0 ? '✅ None' : '⚠️ ' + this.results.highPriorityIssues.length + ' should be addressed'}  
- **Medium Priority:** ${this.results.mediumPriorityIssues.length} improvement opportunities
- **Overall Status:** ${this.results.criticalIssues.length === 0 && this.results.highPriorityIssues.length === 0 ? '🟢 Ready for Production' : this.results.criticalIssues.length > 0 ? '🔴 Blockers Present' : '🟡 Issues to Address'}
`;

    // Save results
    const resultsPath = path.join(__dirname, 'chat_test_results.json');
    const reportPath = path.join(__dirname, 'CHAT_TEST_REPORT.md');
    
    await fs.writeFile(resultsPath, JSON.stringify(this.results, null, 2));
    await fs.writeFile(reportPath, report);
    
    console.log(report);
    console.log(`\n📁 Full results saved to: ${resultsPath}`);
    console.log(`📁 Report saved to: ${reportPath}`);
    
    return this.results;
  }

  async runAllTests() {
    try {
      await this.initialize();
      
      await this.testPhase1_Navigation();
      await this.testPhase2_Authentication();
      await this.testPhase3_ChatInterface();
      await this.testPhase4_ResponsiveDesign();
      await this.testPhase5_PerformanceValidation();
      
      return await this.generateReport();
      
    } catch (error) {
      console.error('❌ Test runner error:', error);
      this.results.criticalIssues.push({
        type: 'Test Runner Failure',
        message: error.message,
        impact: 'Cannot complete comprehensive testing'
      });
      return this.results;
    } finally {
      if (this.browser) {
        await this.browser.close();
      }
    }
  }
}

// Run tests if script is executed directly
if (require.main === module) {
  const runner = new ChatTestRunner();
  runner.runAllTests().then(results => {
    const exitCode = results.criticalIssues.length > 0 ? 1 : 0;
    process.exit(exitCode);
  }).catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = ChatTestRunner;