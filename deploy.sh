#!/bin/bash
# Quick deployment script for Vercel

echo "🚀 Vercel Deployment Helper"
echo "============================"
echo ""

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "⚠️  Vercel CLI not found. Installing..."
    npm install -g vercel
fi

echo "✅ Vercel CLI ready"
echo ""

# Check essential files
echo "📋 Checking files..."
missing_files=0
for file in index.html index_comprehensive.html app_comprehensive.js styles_comprehensive.css comparison_all_43_apis.json vercel.json; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -eq 0 ]; then
    echo "✅ All essential files present"
    echo ""
    echo "📤 Deploying to Vercel..."
    echo ""
    vercel --prod
else
    echo "❌ Please fix missing files before deploying"
    exit 1
fi

