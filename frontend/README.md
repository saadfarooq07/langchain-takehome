# Log Analyzer UI (Allogator)

A modern, dark-themed UI for the Log Analyzer Agent with enhanced analysis capabilities.

## Features

- 🎨 **Modern Dark Theme**: Sleek interface with green accents
- 📊 **Enhanced Analysis**: Structured output with executive summaries
- 📁 **File Upload**: Support for log file uploads
- 📜 **History Tracking**: View past analyses with severity indicators
- 🔧 **Diagnostic Commands**: Ready-to-run troubleshooting commands
- ⚡ **Real-time Analysis**: Instant feedback with formatted results

## Quick Start

### Prerequisites
- Node.js 18+ or Bun
- Backend API running at http://localhost:8000

### Installation

```bash
# Install dependencies
npm install
# or
bun install

# Start the development server
npm start
# or
bun start
```

The UI will be available at http://localhost:3000

## Usage

1. **Analyze Logs**:
   - Paste logs directly into the text area
   - Or upload a log file using the "Upload File" button
   - Press Ctrl+Enter or click "Analyze" to start

2. **View Results**:
   - Executive summary with health assessment
   - Categorized issues with severity levels
   - Actionable recommendations
   - Diagnostic commands to run

3. **History**:
   - View all past analyses
   - Filter by severity
   - Click "View" to see full details

4. **Settings**:
   - Configure analysis depth
   - Enable/disable enhanced analysis
   - Adjust API settings

## Architecture

The UI is built with:
- React 18 with TypeScript
- Tailwind CSS for styling
- Axios for API communication
- No authentication required (simplified for ease of use)

## API Integration

The UI communicates with the backend API at `/api/v2/analyze` endpoint.

Request format:
```json
{
  "log_content": "your logs here",
  "application_name": "user-app",
  "enable_enhanced_analysis": true
}
```

## Customization

### Colors
Edit the Tailwind classes in `AllogatorUI.tsx`:
- Primary: `green-400`, `green-600`
- Background: `gray-950`, `gray-900`
- Text: `gray-200`, `gray-300`

### Analysis Depth
Configure in Settings or modify the API request in the `analyzeLog` function.

## Development

```bash
# Run type checking
npm run typecheck

# Format code
npm run format

# Lint
npm run lint
```

## Production Build

```bash
npm run build
# or
bun run build
```

The build output will be in the `dist` directory.