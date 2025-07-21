# Quick Start Guide

## Fix UI Issues

If the UI looks broken, follow these steps:

### 1. Clean Install Dependencies

```bash
cd frontend
rm -rf node_modules bun.lockb package-lock.json
bun install
```

### 2. Start the Development Server

```bash
bun run dev
# or
npm run dev
```

The UI will be available at http://localhost:3001 (note: port 3001, not 3000)

### 3. Verify Tailwind is Working

Open http://localhost:3001 and check:
- Dark background (gray-950)
- Green accents on active menu items
- Proper spacing and layout

### 4. If Still Broken

Try using the CDN version temporarily:

1. Add to `index.html` before closing `</head>`:
```html
<script src="https://cdn.tailwindcss.com"></script>
```

2. Restart the dev server

### 5. Common Issues

- **Port conflict**: The app runs on port 3001, not 3000
- **API connection**: Ensure backend is running on port 8000
- **Missing styles**: Check browser console for CSS loading errors

### 6. Test the UI

1. Open the app
2. Paste some log content
3. Click "Analyze" or press Ctrl+Enter
4. You should see formatted analysis results

## Backend Setup

Make sure the backend is running:

```bash
# In the root directory
python main.py
```

The API should be available at http://localhost:8000