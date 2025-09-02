const { chromium } = require('playwright');

(async () => {
  console.log('Starting browser test...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    // Step 1: Navigate to login page
    console.log('1. Navigating to login page...');
    await page.goto('http://localhost:3005/login');
    await page.screenshot({ path: 'test-1-login.png' });
    
    // Step 2: Fill in credentials
    console.log('2. Filling in credentials...');
    await page.fill('input[type="email"]', 'demo_hnw@sigmasight.com');
    await page.fill('input[type="password"]', 'demo12345');
    
    // Step 3: Submit login
    console.log('3. Submitting login...');
    await page.click('button[type="submit"]');
    
    // Step 4: Wait for redirect
    console.log('4. Waiting for redirect to portfolio...');
    await page.waitForURL('**/portfolio**', { timeout: 10000 });
    await page.waitForTimeout(2000); // Let page load
    await page.screenshot({ path: 'test-2-portfolio.png' });
    
    // Step 5: Find chat input
    console.log('5. Looking for chat input...');
    const chatInput = await page.locator('input[placeholder*="Ask a question"]').first();
    if (await chatInput.isVisible()) {
      console.log('   ✓ Found chat input');
      await chatInput.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: 'test-3-chat-open.png' });
      
      // Step 6: Type message in sheet
      console.log('6. Typing message in chat sheet...');
      const sheetInput = await page.locator('input[placeholder*="Type your message"]').first();
      if (await sheetInput.isVisible()) {
        await sheetInput.fill('What is my largest position?');
        console.log('   ✓ Message typed');
        
        // Step 7: Send message
        console.log('7. Sending message...');
        const sendButton = await page.locator('button:has-text("Send")').first();
        await sendButton.click();
        console.log('   ✓ Message sent');
        
        // Step 8: Wait for response
        console.log('8. Waiting for response (5 seconds)...');
        await page.waitForTimeout(5000);
        await page.screenshot({ path: 'test-4-response.png' });
        
        // Check for messages
        const messages = await page.locator('.text-sm.whitespace-pre-wrap').count();
        console.log(`   ✓ Found ${messages} messages in chat`);
        
        // Check for errors
        const errors = await page.locator('text=/error|failed/i').count();
        if (errors > 0) {
          console.log(`   ⚠️ Found ${errors} error message(s)`);
        }
      } else {
        console.log('   ⚠️ Chat sheet input not found');
      }
    } else {
      console.log('   ⚠️ Chat input not found on page');
    }
    
    // Final screenshot
    await page.screenshot({ path: 'test-5-final.png', fullPage: true });
    console.log('✓ Test completed! Check test-*.png files for results');
    
  } catch (error) {
    console.error('Error during test:', error);
    await page.screenshot({ path: 'test-error.png' });
  } finally {
    await browser.close();
  }
})();