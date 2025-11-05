const { chromium } = require('playwright');

async function testChatFlow() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Monitor console logs
  const logs = [];
  const errors = [];
  
  page.on('console', msg => {
    const text = msg.text();
    logs.push(`${msg.type()}: ${text}`);
    console.log(`Console ${msg.type()}: ${text}`);
  });
  
  page.on('pageerror', error => {
    errors.push(error.message);
    console.error('Page error:', error.message);
  });
  
  try {
    console.log('1. Navigate to portfolio page...');
    await page.goto('http://localhost:3005/portfolio?type=high-net-worth');
    await page.waitForLoadState('networkidle');
    
    console.log('2. Look for login form...');
    // Wait for either login form or chat trigger
    await page.waitForTimeout(2000);
    
    // Check if we need to login
    const loginForm = await page.$('#email');
    if (loginForm) {
      console.log('3. Logging in...');
      await page.fill('#email', 'demo_growth@sigmasight.com');
      await page.fill('#password', 'demo12345');
      await page.click('button[type="submit"]');
      await page.waitForTimeout(3000);
    }
    
    console.log('4. Looking for chat trigger...');
    await page.waitForTimeout(2000);
    
    // Try to find and click chat trigger
    const chatTriggers = [
      'button[aria-label="Open chat"]',
      '[data-testid="chat-trigger"]',
      '.chat-trigger',
      'button:has-text("Chat")',
      'button:has-text("Ask AI")'
    ];
    
    let chatOpened = false;
    for (const selector of chatTriggers) {
      try {
        await page.click(selector);
        console.log(`Found chat trigger: ${selector}`);
        chatOpened = true;
        break;
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!chatOpened) {
      // Try floating action button or any button in bottom right
      const floatingButtons = await page.$$('button');
      for (const button of floatingButtons) {
        const box = await button.boundingBox();
        if (box && box.x > 800 && box.y > 400) { // Bottom right area
          await button.click();
          console.log('Clicked floating button in bottom right');
          chatOpened = true;
          break;
        }
      }
    }
    
    if (!chatOpened) {
      console.log('Could not find chat trigger. Available buttons:');
      const buttons = await page.$$eval('button', btns => 
        btns.map(btn => ({
          text: btn.textContent?.trim(),
          className: btn.className,
          id: btn.id,
          ariaLabel: btn.getAttribute('aria-label')
        }))
      );
      console.log(buttons);
      throw new Error('Chat trigger not found');
    }
    
    await page.waitForTimeout(1000);
    
    console.log('5. Looking for chat input...');
    const chatInputs = [
      'input[placeholder*="chat"]',
      'input[placeholder*="message"]', 
      'textarea[placeholder*="chat"]',
      'textarea[placeholder*="message"]',
      '#chat-input',
      '[data-testid="chat-input"]'
    ];
    
    let inputFound = false;
    for (const selector of chatInputs) {
      try {
        await page.waitForSelector(selector, { timeout: 2000 });
        await page.fill(selector, 'What are my top 3 holdings?');
        console.log(`Found chat input: ${selector}`);
        inputFound = true;
        break;
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!inputFound) {
      console.log('Available inputs:');
      const inputs = await page.$$eval('input, textarea', els => 
        els.map(el => ({
          type: el.tagName,
          placeholder: el.placeholder,
          className: el.className,
          id: el.id
        }))
      );
      console.log(inputs);
      throw new Error('Chat input not found');
    }
    
    console.log('6. Sending message...');
    // Try to find send button
    const sendButtons = [
      'button[type="submit"]',
      'button:has-text("Send")',
      'button[aria-label*="send"]',
      '[data-testid="send-button"]',
      '#send-button'
    ];
    
    let sent = false;
    for (const selector of sendButtons) {
      try {
        await page.click(selector);
        console.log(`Found send button: ${selector}`);
        sent = true;
        break;
      } catch (e) {
        // Try next selector
      }
    }
    
    if (!sent) {
      // Try pressing Enter
      await page.keyboard.press('Enter');
      console.log('Pressed Enter to send');
    }
    
    console.log('7. Waiting for response...');
    await page.waitForTimeout(10000);
    
    // Take screenshot
    await page.screenshot({ path: 'chat_test_result.png', fullPage: true });
    
    console.log('8. Test completed!');
    console.log('\n=== CONSOLE LOGS ===');
    logs.forEach(log => console.log(log));
    
    if (errors.length > 0) {
      console.log('\n=== ERRORS ===');
      errors.forEach(error => console.log(error));
    }
    
    // Check for streaming messages or responses
    const messages = await page.$$eval('[data-message], .message, .chat-message', 
      msgs => msgs.map(msg => msg.textContent?.trim()).filter(Boolean)
    );
    
    console.log('\n=== CHAT MESSAGES ===');
    console.log(messages);
    
    return {
      success: true,
      logs,
      errors,
      messages,
      screenshots: ['chat_test_result.png']
    };
    
  } catch (error) {
    await page.screenshot({ path: 'chat_test_error.png', fullPage: true });
    console.error('Test failed:', error.message);
    
    return {
      success: false,
      error: error.message,
      logs,
      errors,
      screenshots: ['chat_test_error.png']
    };
  } finally {
    await browser.close();
  }
}

// Run the test
testChatFlow().then(result => {
  console.log('\n=== FINAL RESULT ===');
  console.log(JSON.stringify(result, null, 2));
}).catch(console.error);