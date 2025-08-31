const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function analyzePricingSection() {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  // Set viewport to ensure consistent screenshots
  await page.setViewportSize({ width: 1400, height: 900 });
  
  try {
    console.log('Navigating to http://localhost:3005...');
    await page.goto('http://localhost:3005', { waitUntil: 'networkidle' });
    
    // Wait for page to fully load
    await page.waitForTimeout(2000);
    
    // Create screenshots directory
    const screenshotsDir = path.join(__dirname, 'pricing-review-screenshots');
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir);
    }
    
    // Take full page screenshot first
    console.log('Taking full page screenshot...');
    await page.screenshot({ 
      path: path.join(screenshotsDir, 'full-page.png'),
      fullPage: true
    });
    
    // Look for pricing section - try multiple selectors
    let pricingSection = null;
    const possibleSelectors = [
      'text="Choose Your Experience Level"',
      '[data-testid*="pricing"]',
      '.pricing-section',
      'section:has-text("Choose Your Experience Level")',
      'div:has-text("Choose Your Experience Level")'
    ];
    
    for (const selector of possibleSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.count() > 0) {
          pricingSection = element;
          console.log(`Found pricing section with selector: ${selector}`);
          break;
        }
      } catch (e) {
        // Continue to next selector
      }
    }
    
    if (pricingSection) {
      // Take screenshot of pricing section
      console.log('Taking pricing section screenshot...');
      await pricingSection.screenshot({ 
        path: path.join(screenshotsDir, 'pricing-section.png')
      });
    } else {
      console.log('Could not find pricing section with specific selector, taking viewport screenshot...');
      await page.screenshot({ 
        path: path.join(screenshotsDir, 'viewport-screenshot.png')
      });
    }
    
    // Look for individual pricing cards
    const cardSelectors = [
      'text="Basic"',
      'text="Standard"', 
      'text="Professional"'
    ];
    
    const cardNames = ['Basic', 'Standard', 'Professional'];
    
    for (let i = 0; i < cardSelectors.length; i++) {
      try {
        console.log(`Looking for ${cardNames[i]} card...`);
        
        // Try to find the card by text and then get its parent container
        const cardText = page.locator(cardSelectors[i]).first();
        
        if (await cardText.count() > 0) {
          // Try different parent selectors to get the full card
          const parentSelectors = [
            '..',  // Direct parent
            '../..',  // Grandparent
            '../../..',  // Great-grandparent
            '../../../..'  // Great-great-grandparent
          ];
          
          let cardContainer = null;
          for (const parentSel of parentSelectors) {
            try {
              const parent = cardText.locator(parentSel);
              const boundingBox = await parent.boundingBox();
              if (boundingBox && boundingBox.height > 200 && boundingBox.width > 200) {
                cardContainer = parent;
                break;
              }
            } catch (e) {
              // Continue
            }
          }
          
          if (cardContainer) {
            console.log(`Taking screenshot of ${cardNames[i]} card...`);
            await cardContainer.screenshot({ 
              path: path.join(screenshotsDir, `${cardNames[i].toLowerCase()}-card.png`)
            });
          } else {
            console.log(`Could not find suitable container for ${cardNames[i]} card`);
          }
        }
      } catch (e) {
        console.log(`Error capturing ${cardNames[i]} card:`, e.message);
      }
    }
    
    // Take additional screenshots scrolled to different positions
    console.log('Taking additional positioned screenshots...');
    
    // Scroll to find pricing section
    await page.evaluate(() => {
      const element = document.querySelector('*');
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
      );
      
      let node;
      while (node = walker.nextNode()) {
        if (node.textContent.includes('Choose Your Experience Level')) {
          node.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
          break;
        }
      }
    });
    
    await page.waitForTimeout(1000);
    
    await page.screenshot({ 
      path: path.join(screenshotsDir, 'pricing-centered.png')
    });
    
    // Get page content for analysis
    console.log('Extracting page content for analysis...');
    const pageContent = await page.content();
    fs.writeFileSync(path.join(screenshotsDir, 'page-content.html'), pageContent);
    
    // Try to extract pricing card information
    const pricingInfo = await page.evaluate(() => {
      const results = [];
      const possibleCardContainers = document.querySelectorAll('div, section, article');
      
      for (const container of possibleCardContainers) {
        const text = container.textContent || '';
        if (text.includes('Basic') || text.includes('Standard') || text.includes('Professional')) {
          if (text.includes('month') || text.includes('$') || text.includes('Free')) {
            const rect = container.getBoundingClientRect();
            results.push({
              text: text.substring(0, 500), // First 500 chars
              rect: {
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height
              },
              tagName: container.tagName,
              className: container.className
            });
          }
        }
      }
      return results;
    });
    
    fs.writeFileSync(
      path.join(screenshotsDir, 'pricing-analysis.json'), 
      JSON.stringify(pricingInfo, null, 2)
    );
    
    console.log('Analysis complete! Screenshots saved to:', screenshotsDir);
    console.log('Found', pricingInfo.length, 'potential pricing containers');
    
  } catch (error) {
    console.error('Error during analysis:', error);
  } finally {
    await browser.close();
  }
}

analyzePricingSection().catch(console.error);