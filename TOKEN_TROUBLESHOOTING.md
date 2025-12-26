# Token Troubleshooting - 403 Permission Denied

## Issue
The GitHub Personal Access Token is being rejected with:
```
remote: Permission to sekharcidambi/commodity-etf-tracker.git denied to sekharcidambi.
fatal: unable to access '...': The requested URL returned error: 403
```

## Most Likely Cause

The token was created **without the correct scopes**. When creating the token, you must check the **"repo"** scope.

## Solution: Recreate Token with Correct Scopes

### Step 1: Delete Old Token
1. Go to: https://github.com/settings/tokens
2. Find the token you just created
3. Click **Delete** to remove it

### Step 2: Create New Token with Correct Scopes

1. Go to: **https://github.com/settings/tokens**
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Fill in:
   - **Note**: `commodity-etf-tracker-push`
   - **Expiration**: 90 days (or your preference)

4. **IMPORTANT - Check these scopes:**
   - ✅ **repo** (Full control of private repositories)
     - This should automatically check all sub-items:
       - ✅ repo:status
       - ✅ repo_deployment
       - ✅ public_repo
       - ✅ repo:invite
       - ✅ security_events

5. Scroll down and click **"Generate token"**
6. **COPY THE TOKEN** (you won't see it again!)

### Step 3: Push with New Token

Once you have the new token with "repo" scope checked:

```bash
cd /home/user/commodity-etf-tracker

# Replace NEW_TOKEN with your actual token
git push https://NEW_TOKEN@github.com/sekharcidambi/commodity-etf-tracker.git \
  claude/commodity-dashboard-signals-q2G91
```

## Alternative: Check Repository Settings

If the token still doesn't work after recreating with "repo" scope:

1. **Verify repository exists**:
   - Visit: https://github.com/sekharcidambi/commodity-etf-tracker
   - Confirm you can see it

2. **Check repository ownership**:
   - Make sure it's under your personal account (sekharcidambi)
   - NOT under an organization

3. **Repository visibility**:
   - If it's a private repo, the token MUST have "repo" scope
   - If it's public, the token needs at least "public_repo" scope

## Visual Guide: Token Scopes

When creating the token, the scopes section should look like this:

```
Select scopes

☑ repo                          Full control of private repositories
  ☑ repo:status                Access commit status
  ☑ repo_deployment            Access deployment status
  ☑ public_repo                Access public repositories
  ☑ repo:invite                Access repository invitations
  ☑ security_events            Read and write security events

☐ workflow                      Update GitHub Action workflows
☐ write:packages                Upload packages to GitHub Package Registry
...
```

**The main "repo" checkbox at the top is what you need to check!**

## After Fixing

Once you create a token with the correct scopes, the push command will look like:

```bash
cd /home/user/commodity-etf-tracker
git push https://YOUR_NEW_TOKEN@github.com/sekharcidambi/commodity-etf-tracker.git \
  claude/commodity-dashboard-signals-q2G91
```

You should see:
```
Enumerating objects: 85, done.
Counting objects: 100% (85/85), done.
Delta compression using up to 8 threads
Compressing objects: 100% (75/75), done.
Writing objects: 100% (85/85), 50.23 KiB | 3.35 MiB/s, done.
Total 85 (delta 25), reused 0 (delta 0), pack-reused 0
To https://github.com/sekharcidambi/commodity-etf-tracker.git
 * [new branch]      claude/commodity-dashboard-signals-q2G91 -> claude/commodity-dashboard-signals-q2G91
Branch 'claude/commodity-dashboard-signals-q2G91' set up to track remote branch 'claude/commodity-dashboard-signals-q2G91' from 'origin'.
```

Then visit: **https://github.com/sekharcidambi/commodity-etf-tracker** to see your code!
