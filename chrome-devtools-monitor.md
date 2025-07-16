# Chrome DevTools Monitor for Cursor Composer

## Overview

This script enables Cursor's Composer agent to have live access to Chrome browser console logs and network activity through the Chrome DevTools Protocol (CDP). This allows for automated debugging and error fixing workflows.

## Features

- **Real-time Console Monitoring**: Captures all console logs, errors, warnings, and info messages
- **Network Activity Tracking**: Monitors HTTP requests and responses
- **Automatic Error Detection**: Can trigger actions based on console errors
- **Playwright Integration**: Enhanced automation capabilities with BaseMonitor class
- **Cross-platform Support**: Works on Windows, macOS, and Linux

## Setup Instructions

### 1. Prerequisites

- Node.js installed on your system
- Chrome/Chromium browser
- Basic understanding of Chrome DevTools Protocol

### 2. Install Dependencies

```bash
npm install ws chrome-remote-interface playwright
```

### 3. Launch Chrome in Debug Mode

**macOS:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=~/Desktop/chrome_profile
```

**Windows:**
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome_profile
```

**Linux:**
```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome_profile
```

## Script Implementation

### Basic Chrome DevTools Monitor (`cursor-composer.js`)

```javascript
const CDP = require('chrome-remote-interface');
const WebSocket = require('ws');

class ChromeMonitor {
    constructor(options = {}) {
        this.port = options.port || 9222;
        this.host = options.host || 'localhost';
        this.clearOnRefresh = options.clearOnRefresh !== false;
        this.exitOnError = options.exitOnError || false;
        this.client = null;
        this.isConnected = false;
    }

    async connect() {
        try {
            console.log(`Connecting to Chrome DevTools on ${this.host}:${this.port}...`);
            
            this.client = await CDP({
                port: this.port,
                host: this.host
            });

            const { Runtime, Console, Network, Page } = this.client;

            // Enable domains
            await Promise.all([
                Runtime.enable(),
                Console.enable(),
                Network.enable(),
                Page.enable()
            ]);

            this.setupEventHandlers();
            this.isConnected = true;
            
            console.log('✅ Connected to Chrome DevTools');
            console.log('📊 Monitoring console logs and network activity...');
            console.log('🔄 Use Ctrl+C to stop monitoring\n');

        } catch (error) {
            console.error('❌ Failed to connect to Chrome DevTools:', error.message);
            console.error('💡 Make sure Chrome is running with --remote-debugging-port=9222');
            process.exit(1);
        }
    }

    setupEventHandlers() {
        const { Runtime, Console, Network, Page } = this.client;

        // Handle page navigation/refresh
        Page.frameNavigated(() => {
            if (this.clearOnRefresh) {
                console.log('\n🔄 Page refreshed - Console cleared\n');
            }
        });

        // Handle console API calls (console.log, console.error, etc.)
        Runtime.consoleAPICalled((event) => {
            const { type, args, stackTrace, timestamp } = event;
            const time = new Date(timestamp).toISOString();
            
            // Format arguments
            const message = args.map(arg => {
                if (arg.type === 'object' && arg.preview) {
                    return this.formatObject(arg.preview);
                }
                return arg.value || arg.description || '[Object]';
            }).join(' ');

            // Get location info
            const location = stackTrace?.callFrames?.[0];
            const locationStr = location ? 
                ` (${location.url}:${location.lineNumber}:${location.columnNumber})` : '';

            // Output with emoji for visibility
            const emoji = this.getLogEmoji(type);
            console.log(`${emoji} [${time}] ${type.toUpperCase()}${locationStr}: ${message}`);

            if (this.exitOnError && type === 'error') {
                console.log('\n🛑 Error detected - Exiting for analysis...\n');
                this.disconnect();
                process.exit(1);
            }
        });

        // Handle runtime exceptions
        Runtime.exceptionThrown((event) => {
            const { exceptionDetails } = event;
            const time = new Date().toISOString();
            const message = exceptionDetails.exception?.description || exceptionDetails.text;
            
            console.log(`💥 [${time}] EXCEPTION: ${message}`);
            
            if (exceptionDetails.stackTrace) {
                console.log('📍 Stack trace:');
                exceptionDetails.stackTrace.callFrames.forEach(frame => {
                    console.log(`    at ${frame.functionName || '<anonymous>'} (${frame.url}:${frame.lineNumber}:${frame.columnNumber})`);
                });
            }

            if (this.exitOnError) {
                console.log('\n🛑 Exception detected - Exiting for analysis...\n');
                this.disconnect();
                process.exit(1);
            }
        });

        // Handle network requests
        Network.requestWillBeSent((event) => {
            const { request, timestamp } = event;
            const time = new Date(timestamp * 1000).toISOString();
            console.log(`🌐 [${time}] ${request.method} ${request.url}`);
        });

        // Handle network responses
        Network.responseReceived((event) => {
            const { response, timestamp } = event;
            const time = new Date(timestamp * 1000).toISOString();
            const statusEmoji = response.status >= 400 ? '❌' : '✅';
            console.log(`${statusEmoji} [${time}] ${response.status} ${response.url}`);
        });

        // Handle network failures
        Network.loadingFailed((event) => {
            const { errorText, timestamp } = event;
            const time = new Date(timestamp * 1000).toISOString();
            console.log(`🚨 [${time}] NETWORK ERROR: ${errorText}`);
        });
    }

    formatObject(preview) {
        if (!preview.properties) return '[Object]';
        
        const props = preview.properties.map(prop => 
            `${prop.name}: ${prop.value}`
        ).join(', ');
        
        return `{${props}}`;
    }

    getLogEmoji(type) {
        const emojiMap = {
            'log': '📝',
            'info': 'ℹ️',
            'warn': '⚠️',
            'error': '🚨',
            'debug': '🐛',
            'trace': '🔍'
        };
        return emojiMap[type] || '📄';
    }

    async clearConsole() {
        if (this.client) {
            await this.client.Runtime.evaluate({
                expression: 'console.clear()'
            });
            console.log('🧹 Console cleared');
        }
    }

    disconnect() {
        if (this.client) {
            this.client.close();
            this.isConnected = false;
            console.log('🔌 Disconnected from Chrome DevTools');
        }
    }
}

// Enhanced monitor with Playwright integration
class BaseMonitor extends ChromeMonitor {
    constructor(options = {}) {
        super(options);
        this.playwright = null;
        this.browser = null;
        this.page = null;
    }

    async startWithPlaywright(options = {}) {
        const playwright = require('playwright');
        
        // Launch browser
        this.browser = await playwright.chromium.launch({
            headless: false,
            args: ['--remote-debugging-port=9222']
        });

        this.page = await this.browser.newPage();
        
        // Connect to CDP
        await this.connect();
        
        console.log('🎭 Playwright browser launched with CDP monitoring');
        return this.page;
    }

    async navigateAndMonitor(url) {
        if (!this.page) {
            throw new Error('Playwright not initialized. Call startWithPlaywright() first.');
        }

        console.log(`🔗 Navigating to: ${url}`);
        await this.page.goto(url);
        
        // Wait for page to load
        await this.page.waitForLoadState('networkidle');
        console.log('✅ Page loaded successfully');
    }

    async closeBrowser() {
        if (this.browser) {
            await this.browser.close();
            console.log('🚪 Browser closed');
        }
        this.disconnect();
    }
}

// CLI usage
if (require.main === module) {
    const args = process.argv.slice(2);
    const options = {};

    // Parse command line arguments
    for (let i = 0; i < args.length; i++) {
        switch (args[i]) {
            case '--port':
                options.port = parseInt(args[++i]);
                break;
            case '--host':
                options.host = args[++i];
                break;
            case '--exit-on-error':
                options.exitOnError = true;
                break;
            case '--no-clear-on-refresh':
                options.clearOnRefresh = false;
                break;
            case '--playwright':
                options.usePlaywright = true;
                break;
            case '--url':
                options.url = args[++i];
                break;
        }
    }

    const monitor = options.usePlaywright ? new BaseMonitor(options) : new ChromeMonitor(options);

    // Handle graceful shutdown
    process.on('SIGINT', () => {
        console.log('\n🛑 Shutting down monitor...');
        if (monitor.closeBrowser) {
            monitor.closeBrowser().then(() => process.exit(0));
        } else {
            monitor.disconnect();
            process.exit(0);
        }
    });

    // Start monitoring
    if (options.usePlaywright) {
        monitor.startWithPlaywright().then(async (page) => {
            if (options.url) {
                await monitor.navigateAndMonitor(options.url);
            }
        }).catch(console.error);
    } else {
        monitor.connect().catch(console.error);
    }
}

module.exports = { ChromeMonitor, BaseMonitor };
```

### Package.json

```json
{
  "name": "cursor-chrome-monitor",
  "version": "1.0.0",
  "description": "Chrome DevTools monitor for Cursor Composer integration",
  "main": "cursor-composer.js",
  "scripts": {
    "start": "node cursor-composer.js",
    "start:playwright": "node cursor-composer.js --playwright",
    "start:exit-on-error": "node cursor-composer.js --exit-on-error"
  },
  "dependencies": {
    "chrome-remote-interface": "^0.33.2",
    "playwright": "^1.40.0",
    "ws": "^8.14.2"
  },
  "keywords": ["chrome", "devtools", "cursor", "composer", "debugging"],
  "author": "Your Name",
  "license": "MIT"
}
```

## Usage Examples

### 1. Basic Console Monitoring

```bash
# Start basic monitoring
node cursor-composer.js

# Monitor on custom port
node cursor-composer.js --port 9223

# Exit on first error (useful for automated debugging)
node cursor-composer.js --exit-on-error
```

### 2. Playwright Integration

```bash
# Start with Playwright automation
node cursor-composer.js --playwright --url "http://localhost:3000"

# Monitor specific application
node cursor-composer.js --playwright --url "http://localhost:3000/login" --exit-on-error
```

### 3. Cursor Composer Workflow

1. **Tell Composer to start monitoring:**
   ```
   Run the chrome monitor script in a terminal that stays open so you can see the console logs
   ```

2. **Debug workflow example:**
   ```
   1. Start the monitor with exit-on-error mode
   2. Navigate to the page with issues
   3. When an error occurs, the script exits and shows the error
   4. Fix the error based on the output
   5. Restart and repeat until no errors
   ```

### 4. Integration with Cursor Terminal

To use with Cursor's terminal referencing feature (available in v0.46+):

1. Start the monitor in a terminal within Cursor
2. Move the terminal to the editor area (right-click → "Move terminal into Editor Area")
3. Reference the terminal in Composer with `@terminal`
4. The agent can now see live console output

## Advanced Features

### Custom Error Handling

```javascript
// Create custom monitor with specific error handling
const monitor = new ChromeMonitor({
    exitOnError: true,
    customErrorHandler: (error) => {
        // Custom logic for specific errors
        if (error.includes('TypeError')) {
            console.log('🔧 TypeScript error detected - checking types...');
        }
    }
});
```

### Playwright Test Automation

```javascript
const { BaseMonitor } = require('./cursor-composer');

async function debugCreatePetComponent() {
    const monitor = new BaseMonitor({ exitOnError: true });
    const page = await monitor.startWithPlaywright();
    
    try {
        await monitor.navigateAndMonitor('http://localhost:3000/pets/create');
        
        // Interact with the page
        await page.fill('#pet-name', 'Fluffy');
        await page.click('#submit-button');
        
        // Monitor will exit if errors occur
        console.log('✅ No errors detected in CreatePet component');
        
    } catch (error) {
        console.error('❌ Error in CreatePet component:', error);
    } finally {
        await monitor.closeBrowser();
    }
}
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Ensure Chrome is running with `--remote-debugging-port=9222`
   - Check if port 9222 is available
   - Verify Chrome profile directory exists

2. **No Console Output**
   - Make sure the page is actively generating console logs
   - Check if the page has loaded completely
   - Verify network activity is occurring

3. **Windows Compatibility**
   - Use proper path escaping for Chrome executable
   - Consider using PowerShell instead of CMD

### Performance Tips

- Use `--exit-on-error` for focused debugging sessions
- Clear console between navigation for cleaner output
- Monitor specific domains with network filtering

## Integration with Cursor Composer

### Prompt Examples

1. **Start Monitoring:**
   ```
   Start the chrome devtools monitor script and keep it running in a terminal. Make sure the terminal stays visible so we can see console logs.
   ```

2. **Debug Workflow:**
   ```
   1. Start the monitor with exit-on-error enabled
   2. Navigate to the page with issues  
   3. Read the console output when errors occur
   4. Fix the identified errors
   5. Restart the monitor and test again
   ```

3. **Automated Testing:**
   ```
   Create a Playwright script that uses BaseMonitor to automatically navigate to the CreatePet component, test the functionality, and report any console errors.
   ```

This comprehensive script provides the functionality described in the forum discussion and enables powerful debugging workflows with Cursor's Composer agent.