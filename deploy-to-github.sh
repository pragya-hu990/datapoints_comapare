#!/bin/bash
# Script to prepare and deploy to GitHub for Netlify

echo "🚀 Preparing GitHub Deployment for Netlify"
echo "============================================"
echo ""

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not a Git repository. Initializing..."
    git init
    git remote add origin https://github.com/pragya-hu990/datapoints_comapare.git
fi

echo "📦 Staging essential files..."
git add netlify.toml _redirects .netlifyignore
git add index.html index_comprehensive.html
git add app_comprehensive.js styles_comprehensive.css
git add comparison_all_43_apis.json
git add package.json README.md

echo ""
echo "📝 Files staged. Ready to commit."
echo ""
echo "Next steps:"
echo "1. Review changes: git status"
echo "2. Commit: git commit -m 'Add Netlify deployment configuration'"
echo "3. Push: git push origin main"
echo ""
echo "Or run automatically? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    git commit -m "Add Netlify deployment configuration and dashboard files

- Added netlify.toml for deployment settings
- Added _redirects for URL routing
- Added .netlifyignore to exclude unnecessary files
- Added all essential dashboard files"
    
    echo ""
    echo "📤 Pushing to GitHub..."
    git push origin main
    
    echo ""
    echo "✅ Pushed to GitHub!"
    echo ""
    echo "Next: Connect this repo to Netlify:"
    echo "1. Go to: https://app.netlify.com/"
    echo "2. Add new site → Import from Git → GitHub"
    echo "3. Select: pragya-hu990/datapoints_comapare"
    echo "4. Build command: (empty)"
    echo "5. Publish directory: ."
    echo "6. Deploy!"
fi
