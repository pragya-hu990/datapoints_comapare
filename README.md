# ReBIT vs FinFactor - Data Points Comparison Dashboard

A comprehensive comparison dashboard for ReBIT XSD schemas and Finn Factor API responses.

## 🚀 Quick Start

This is a static site that can be deployed to Vercel.

### Local Development

Simply open `index_comprehensive.html` in a browser or use a local server:

```bash
python3 -m http.server 8000
```

Then visit: `http://localhost:8000/index_comprehensive.html`

### Vercel Deployment

1. Connect your repository to Vercel
2. Vercel will automatically detect and deploy
3. All static files (HTML, CSS, JS, JSON) will be served

## 📁 File Structure

- `index.html` - Main entry point (redirects to comprehensive dashboard)
- `index_comprehensive.html` - Main dashboard
- `app_comprehensive.js` - Dashboard application logic
- `styles_comprehensive.css` - Dashboard styles
- `comparison_all_43_apis.json` - Comparison data (all nested fields included)
- `vercel.json` - Vercel configuration

## ✅ Verified Data

- All 43 APIs parsed
- All nested fields extracted (dataResourceType, lastFetchDate, currentValue, etc.)
- ReBIT: 935 fields
- Finn Factor: 605 fields
- Common: 15 fields

