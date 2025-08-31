const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

async function captureValidationScreenshots() {
    const browser = await chromium.launch();
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    // Create screenshots directory
    const screenshotsDir = path.join(__dirname, 'screenshots');
    await fs.mkdir(screenshotsDir, { recursive: true });
    
    try {
        // Capture updated localhost:3005
        console.log('Capturing updated localhost:3005...');
        const localPage = await context.newPage();
        await localPage.goto('http://localhost:3005', { waitUntil: 'networkidle' });
        
        // Wait a bit for all animations and loading to complete
        await localPage.waitForTimeout(3000);
        
        // Take full page screenshot of updated localhost
        await localPage.screenshot({ 
            path: path.join(screenshotsDir, 'localhost-3005-updated-full.png'),
            fullPage: true 
        });
        
        // Take viewport screenshot of updated localhost
        await localPage.screenshot({ 
            path: path.join(screenshotsDir, 'localhost-3005-updated-viewport.png') 
        });
        
        // Capture hero section specifically
        try {
            const heroSection = await localPage.locator('section').first();
            const heroBox = await heroSection.boundingBox();
            if (heroBox) {
                await localPage.screenshot({
                    path: path.join(screenshotsDir, 'localhost-updated-hero.png'),
                    clip: heroBox
                });
            }
        } catch (e) {
            console.log('Could not capture hero section:', e.message);
        }
        
        // Capture input field specifically
        try {
            const inputElement = await localPage.locator('input[type="text"]');
            const inputBox = await inputElement.boundingBox();
            if (inputBox) {
                await localPage.screenshot({
                    path: path.join(screenshotsDir, 'localhost-updated-input.png'),
                    clip: inputBox
                });
            }
        } catch (e) {
            console.log('Could not capture input field:', e.message);
        }
        
        // Capture Quick Actions section
        try {
            const quickActionsSection = await localPage.locator('section').nth(1);
            const quickActionsBox = await quickActionsSection.boundingBox();
            if (quickActionsBox) {
                await localPage.screenshot({
                    path: path.join(screenshotsDir, 'localhost-updated-quickactions.png'),
                    clip: quickActionsBox
                });
            }
        } catch (e) {
            console.log('Could not capture Quick Actions section:', e.message);
        }
        
        // Get updated font data for comparison
        console.log('Analyzing updated font styles...');
        
        const updatedFontData = await localPage.evaluate(() => {
            const elements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, span, div, input, button');
            const fontData = [];
            
            elements.forEach((el, index) => {
                if (index < 20) { // Limit to first 20 elements for key comparisons
                    const styles = window.getComputedStyle(el);
                    if (el.textContent && el.textContent.trim()) {
                        fontData.push({
                            tag: el.tagName,
                            text: el.textContent.trim().substring(0, 50),
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
        
        // Save updated font comparison data
        await fs.writeFile(
            path.join(screenshotsDir, 'font-comparison-updated.json'),
            JSON.stringify({ 
                localhost_updated: updatedFontData 
            }, null, 2)
        );
        
        console.log('Updated screenshots and analysis complete!');
        console.log('Files saved in:', screenshotsDir);
        
    } finally {
        await browser.close();
    }
}

captureValidationScreenshots().catch(console.error);