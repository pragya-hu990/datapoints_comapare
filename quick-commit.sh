#!/bin/bash
# Quick commit script for Netlify files

echo "📝 Committing Netlify deployment files..."
echo ""

# Add Netlify configuration files
git add netlify.toml _redirects .netlifyignore

# Add deployment guides
git add NETLIFY_DEPLOY.md COMMIT_GUIDE.md

# Add deployment scripts
git add netlify-deploy.sh

# Commit
git commit -m "Add Netlify deployment configuration

- Added netlify.toml for deployment settings
- Added _redirects for URL routing
- Added .netlifyignore to exclude unnecessary files
- Added deployment guides and scripts"

echo ""
echo "✅ Files committed!"
echo ""
echo "To push to remote:"
echo "  git push"
