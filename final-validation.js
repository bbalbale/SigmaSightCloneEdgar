const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

async function captureFinalScreenshots() {
    const browser = await chromium.launch();
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const screenshotsDir = path.join(__dirname, 'screenshots');
    await fs.mkdir(screenshotsDir, { recursive: true });
    
    try {
        // Capture final localhost:3005
        console.log('Capturing FINAL localhost:3005...');
        const localPage = await context.newPage();
        await localPage.goto('http://localhost:3005', { waitUntil: 'networkidle' });
        
        // Wait for all elements to load
        await localPage.waitForTimeout(3000);
        
        // Take final viewport screenshot
        await localPage.screenshot({ 
            path: path.join(screenshotsDir, 'localhost-3005-FINAL.png') 
        });
        
        // Take final full page screenshot
        await localPage.screenshot({ 
            path: path.join(screenshotsDir, 'localhost-3005-FINAL-full.png'),
            fullPage: true 
        });
        
        console.log('FINAL validation screenshots complete!');
        console.log('Files saved in:', screenshotsDir);
        
    } finally {
        await browser.close();
    }
}

captureFinalScreenshots().catch(console.error);