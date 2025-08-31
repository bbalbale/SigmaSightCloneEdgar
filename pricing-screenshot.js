const { chromium } = require('playwright');

async function takePricingSectionScreenshot() {
  const browser = await chromium.launch({ 
    headless: true
  });
  
  const context = await browser.newContext({
    viewport: { width: 1200, height: 800 }
  });
  
  const page = await context.newPage();
  
  try {
    console.log('Navigating to http://localhost:3005...');
    await page.goto('http://localhost:3005');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Find the pricing section
    console.log('Looking for pricing section...');
    const pricingSection = await page.locator('section:has(h2:has-text("Choose Your Experience Level"))');
    
    if (await pricingSection.count() > 0) {
      console.log('Found pricing section, taking screenshot...');
      await pricingSection.screenshot({ 
        path: 'pricing-section-current.png'
      });
      console.log('✅ Pricing section screenshot saved as pricing-section-current.png');
    } else {
      // Fallback: scroll to find the section and take a broader screenshot
      console.log('Pricing section not immediately visible, scrolling...');
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight * 0.7));
      await page.waitForTimeout(500);
      
      await page.screenshot({ 
        path: 'pricing-section-current.png',
        clip: { x: 0, y: 100, width: 1200, height: 700 }
      });
      console.log('✅ Fallback pricing area screenshot saved');
    }
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
}

takePricingSectionScreenshot();