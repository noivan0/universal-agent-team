#!/bin/bash

# UNIVERSAL AGENT TEAM - QUICK GITHUB PUSH SCRIPT
# This script performs the final steps to push your repository to GitHub
# Usage: ./QUICK_GITHUB_PUSH.sh YOUR_GITHUB_USERNAME

set -e

if [ -z "$1" ]; then
    echo "Usage: ./QUICK_GITHUB_PUSH.sh YOUR_GITHUB_USERNAME"
    echo ""
    echo "Example: ./QUICK_GITHUB_PUSH.sh john-doe"
    exit 1
fi

USERNAME=$1
REPO_NAME="universal-agent-team"

echo "================================================================================"
echo "  UNIVERSAL AGENT TEAM - GitHub Push Script"
echo "================================================================================"
echo ""
echo "Steps to complete:"
echo "1. Create repository on GitHub"
echo "2. Add remote origin"
echo "3. Rename branch to main (optional)"
echo "4. Push to GitHub"
echo ""
echo "================================================================================"
echo ""

# Step 1: Remind user to create repository
echo "STEP 1: Create GitHub Repository"
echo "========================================="
echo ""
echo "Go to: https://github.com/new"
echo ""
echo "Configure:"
echo "  - Repository name: $REPO_NAME"
echo "  - Description: Multi-agent AI system for automatic software project generation"
echo "  - Visibility: Public"
echo "  - Initialize: None (do not initialize)"
echo ""
echo "Click: Create repository"
echo ""
read -p "Press Enter once you've created the GitHub repository..."
echo ""

# Step 2: Add remote origin
echo "STEP 2: Adding remote origin..."
echo "========================================="
git remote add origin "https://github.com/${USERNAME}/${REPO_NAME}.git"
echo "✓ Remote origin added"
echo ""

# Step 3: Rename branch (optional)
echo "STEP 3: Rename branch to main (optional)"
echo "========================================="
read -p "Rename 'master' to 'main'? (y/n) [recommended: y]: " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git branch -M main
    echo "✓ Branch renamed to 'main'"
else
    echo "! Keeping branch as 'master'"
fi
echo ""

# Step 4: Push to GitHub
echo "STEP 4: Pushing to GitHub..."
echo "========================================="
echo "This may take a minute or two..."
echo ""

BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push -u origin "$BRANCH"

echo ""
echo "================================================================================"
echo "  PUSH COMPLETE!"
echo "================================================================================"
echo ""
echo "Repository URL:"
echo "  https://github.com/${USERNAME}/${REPO_NAME}"
echo ""
echo "Next steps:"
echo "  1. Visit your repository URL above"
echo "  2. Verify README.md renders correctly"
echo "  3. Check that 157 files are present"
echo "  4. Review commit history (should show 5 commits)"
echo ""
echo "Optional: Add topics/description on GitHub"
echo "  Settings → About → Add description and topics"
echo "  Suggested topics: ai, agents, automation, code-generation"
echo ""
echo "================================================================================"
echo ""
echo "SUCCESS! Your repository is now live on GitHub!"
echo ""
