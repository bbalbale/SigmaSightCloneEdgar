const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

async function captureScreenshots() {
    const browser = await chromium.launch();
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    // Create screenshots directory
    const screenshotsDir = path.join(__dirname, 'screenshots');
    await fs.mkdir(screenshotsDir, { recursive: true });
    
    try {
        // Capture localhost:3005
        console.log('Capturing localhost:3005...');
        const localPage = await context.newPage();
        await localPage.goto('http://localhost:3005', { waitUntil: 'networkidle' });
        
        // Wait a bit for all animations and loading to complete
        await localPage.waitForTimeout(3000);
        
        // Take full page screenshot of localhost
        await localPage.screenshot({ 
            path: path.join(screenshotsDir, 'localhost-3005-full.png'),
            fullPage: true 
        });
        
        // Take viewport screenshot of localhost
        await localPage.screenshot({ 
            path: path.join(screenshotsDir, 'localhost-3005-viewport.png') 
        });
        
        // Capture reference site www.sigmasight.io
        console.log('Capturing www.sigmasight.io...');
        const refPage = await context.newPage();
        await refPage.goto('https://www.sigmasight.io', { waitUntil: 'networkidle' });
        
        // Wait a bit for all animations and loading to complete
        await refPage.waitForTimeout(3000);
        
        // Take full page screenshot of reference
        await refPage.screenshot({ 
            path: path.join(screenshotsDir, 'reference-sigmasight-full.png'),
            fullPage: true 
        });
        
        // Take viewport screenshot of reference
        await refPage.screenshot({ 
            path: path.join(screenshotsDir, 'reference-sigmasight-viewport.png') 
        });
        
        // Capture specific sections for detailed comparison
        console.log('Capturing specific sections...');
        
        // Header section
        try {
            const localHeaderBox = await localPage.locator('header, nav, .header, .navbar').first().boundingBox();
            const refHeaderBox = await refPage.locator('header, nav, .header, .navbar').first().boundingBox();
            
            if (localHeaderBox) {
                await localPage.screenshot({
                    path: path.join(screenshotsDir, 'localhost-header.png'),
                    clip: localHeaderBox
                });
            }
            
            if (refHeaderBox) {
                await refPage.screenshot({
                    path: path.join(screenshotsDir, 'reference-header.png'),
                    clip: refHeaderBox
                });
            }
        } catch (e) {
            console.log('Could not capture header sections:', e.message);
        }
        
        // Main content section
        try {
            const localMainBox = await localPage.locator('main, .main, .content, .hero').first().boundingBox();
            const refMainBox = await refPage.locator('main, .main, .content, .hero').first().boundingBox();
            
            if (localMainBox) {
                await localPage.screenshot({
                    path: path.join(screenshotsDir, 'localhost-main.png'),
                    clip: localMainBox
                });
            }
            
            if (refMainBox) {
                await refPage.screenshot({
                    path: path.join(screenshotsDir, 'reference-main.png'),
                    clip: refMainBox
                });
            }
        } catch (e) {
            console.log('Could not capture main sections:', e.message);
        }
        
        // Chat bar / input section
        try {
            const localChatElements = await localPage.locator('input[type="text"], textarea, .chat, .input-bar, .search-bar').all();
            const refChatElements = await refPage.locator('input[type="text"], textarea, .chat, .input-bar, .search-bar').all();
            
            for (let i = 0; i < localChatElements.length; i++) {
                const box = await localChatElements[i].boundingBox();
                if (box) {
                    await localPage.screenshot({
                        path: path.join(screenshotsDir, `localhost-input-${i}.png`),
                        clip: box
                    });
                }
            }
            
            for (let i = 0; i < refChatElements.length; i++) {
                const box = await refChatElements[i].boundingBox();
                if (box) {
                    await refPage.screenshot({
                        path: path.join(screenshotsDir, `reference-input-${i}.png`),
                        clip: box
                    });
                }
            }
        } catch (e) {
            console.log('Could not capture input elements:', e.message);
        }
        
        // Get computed styles for font comparison
        console.log('Analyzing font styles...');
        
        const localFontData = await localPage.evaluate(() => {
            const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, div, input, button');
            const fontData = [];
            
            elements.forEach((el, index) => {
                if (index < 50) { // Limit to first 50 elements
                    const styles = window.getComputedStyle(el);
                    if (el.textContent && el.textContent.trim()) {
                        fontData.push({
                            tag: el.tagName,
                            text: el.textContent.trim().substring(0, 100),
                            fontSize: styles.fontSize,
                            fontFamily: styles.fontFamily,
                            fontWeight: styles.fontWeight,
                            lineHeight: styles.lineHeight,
                            color: styles.color
                        });
                    }
                }
            });
            
            return fontData;
        });
        
        const refFontData = await refPage.evaluate(() => {
            const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, div, input, button');
            const fontData = [];
            
            elements.forEach((el, index) => {
                if (index < 50) { // Limit to first 50 elements
                    const styles = window.getComputedStyle(el);
                    if (el.textContent && el.textContent.trim()) {
                        fontData.push({
                            tag: el.tagName,
                            text: el.textContent.trim().substring(0, 100),
                            fontSize: styles.fontSize,
                            fontFamily: styles.fontFamily,
                            fontWeight: styles.fontWeight,
                            lineHeight: styles.lineHeight,
                            color: styles.color
                        });
                    }
                }
            });
            
            return fontData;
        });
        
        // Save font comparison data
        await fs.writeFile(
            path.join(screenshotsDir, 'font-comparison.json'),
            JSON.stringify({ 
                localhost: localFontData, 
                reference: refFontData 
            }, null, 2)
        );
        
        console.log('Screenshots and analysis complete!');
        console.log('Files saved in:', screenshotsDir);
        
    } finally {
        await browser.close();
    }
}

captureScreenshots().catch(console.error);