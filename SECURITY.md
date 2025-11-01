# Security Guidelines

## ⚠️ IMPORTANT: API Keys & Secrets

### Never Commit Secrets!

**DO NOT** commit any of the following to git:
- ✗ API keys (OpenAI, Anthropic, etc.)
- ✗ Database passwords
- ✗ Private keys
- ✗ Access tokens
- ✗ `.env` files

### Proper Secret Management

#### For Local Development

1. **Create `.env` file locally** (already in `.gitignore`)
   ```bash
   cd speech-to-text  # or graph-generation
   cp .env.example .env
   ```

2. **Add your secrets to `.env`**
   ```env
   OPENAI_API_KEY=your-actual-key-here
   ANTHROPIC_API_KEY=your-actual-key-here
   ```

3. **Never commit `.env`** - It's protected by `.gitignore` ✅

#### For Production/Deployment

Use environment variables provided by your hosting service:

**Vercel:**
- Settings → Environment Variables
- Add secrets there, not in code

**Railway/Render:**
- Environment Variables section
- Set secrets in the dashboard

**Docker:**
- Use `--env-file` or `-e` flags
- Never bake secrets into images

### Sharing Secrets with Team

**Secure Methods:**
- ✅ In-person (verbal)
- ✅ Encrypted messaging (Signal, etc.)
- ✅ Password manager with sharing (1Password, Bitwarden)
- ✅ Secret management service (Doppler, Vault)

**Insecure Methods:**
- ✗ Slack/Discord/Email (plain text)
- ✗ Git commits
- ✗ Screenshots posted online
- ✗ Shared documents

### What To Do If You Exposed a Secret

1. **Immediately rotate/regenerate** the secret
2. **Delete** the exposed key from the service
3. **Create a new key**
4. **Update your local `.env`** with the new key
5. **Share new key securely** with team

For OpenAI:
- Go to: https://platform.openai.com/api-keys
- Delete the compromised key
- Create a new one

For Anthropic:
- Go to: https://console.anthropic.com/settings/keys
- Delete the compromised key
- Create a new one

### Checking Your Repo

Before pushing to git:

```bash
# Check what you're about to commit
git status
git diff

# Make sure .env is NOT listed!
# If it is, add it to .gitignore immediately
```

### .gitignore is Your Friend

This repo has `.gitignore` files that protect:
- `.env` and `.env.local`
- `venv/` and `node_modules/`
- IDE settings
- Temporary files

**Never remove these entries!**

### API Key Best Practices

1. **Use separate keys** for dev/staging/production
2. **Set usage limits** on API keys if available
3. **Monitor usage** regularly
4. **Rotate keys** periodically
5. **Revoke unused keys** immediately

### For This Project

Each component needs its own `.env`:

```
brainstorm-graph/
├── speech-to-text/.env          # OPENAI_API_KEY
├── graph-generation/.env        # ANTHROPIC_API_KEY or OPENAI_API_KEY
└── frontend/.env.local          # Public API URLs only
```

All `.env` files are **protected by .gitignore** ✅

## Questions?

If you're unsure whether something is safe to commit, ask the team first!

**When in doubt, don't commit it.**
