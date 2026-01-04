#!/bin/bash
# Netlify Deployment Helper Script

echo "🚀 Netlify Deployment Helper"
echo "============================"
echo ""

# Check if netlify CLI is installed
if ! command -v netlify &> /dev/null; then
    echo "⚠️  Netlify CLI not found. Installing..."
    npm install -g netlify-cli
fi

echo "✅ Netlify CLI ready"
echo ""

# Check essential files
echo "📋 Checking files..."
missing_files=0
for file in index.html index_comprehensive.html app_comprehensive.js styles_comprehensive.css comparison_all_43_apis.json netlify.toml; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        missing_files=$((missing_files + 1))
    else
        echo "✅ $file"
    fi
done

if [ $missing_files -eq 0 ]; then
    echo ""
    echo "📤 Ready to deploy to Netlify!"
    echo ""
    echo "Choose deployment method:"
    echo "1. Deploy via Netlify CLI (run: netlify deploy --prod)"
    echo "2. Deploy via Netlify Dashboard (drag & drop or connect Git)"
    echo ""
    echo "To deploy now, run:"
    echo "  netlify login"
    echo "  netlify init"
    echo "  netlify deploy --prod"
else
    echo "❌ Please fix missing files before deploying"
    exit 1
fi

