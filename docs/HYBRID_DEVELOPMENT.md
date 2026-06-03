# Hybrid Development Guide

## Development Setup: Copilot Workspace + Claude Production

This document explains how to use **GitHub Copilot Workspace** for development while keeping **Anthropic Claude** as the production execution engine.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│         GitHub Copilot Workspace (Development)          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ • Code Generation (Copilot writes code)          │   │
│  │ • Real-time Suggestions                          │   │
│  │ • Browser-based IDE                              │   │
│  │ • Git Integration                                │   │
│  │ • Testing & Debugging                            │   │
│  └──────────────────────────────────────────────────┘   │
│                        ↓ Push Code ↓                     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│       Anthropic Claude API (Production Execution)       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ • LLM for Task Planning                          │   │
│  │ • LLM for Result Aggregation                     │   │
│  │ • Advanced Reasoning & Self-Correction           │   │
│  │ • Prompt Caching (cost optimization)             │   │
│  │ • Tool Use for Structured Output                 │   │
│  └──────────────────────────────────────────────────┘   │
│                        ↓ Execute ↓                       │
└─────────────────────────────────────────────────────────┘
                           ↓
                    Your Application
                    (Slack, Snowflake, etc.)
```

---

## Step 1: Set Up Copilot Workspace

### Prerequisites
- GitHub account with Copilot subscription
- Repository pushed to GitHub
- `.github/copilot-instructions.md` file (✅ already created)

### Launch Workspace
1. Go to **https://copilot.github.com**
2. Click "New Workspace"
3. Select your GitHub repo
4. Wait for Copilot to index the codebase (~30 seconds)
5. Start coding!

### What Copilot Sees
- **Full codebase**: All files, structure, patterns
- **Documentation**: CLAUDE.md, LANGGRAPH_CONCEPTS.md
- **Instructions**: `.github/copilot-instructions.md`
- **Git history**: Previous commits and patterns
- **Tests**: Existing test patterns to follow

---

## Step 2: Local Development Environment

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_ORG/multi-step-agent.git
cd multi-step-agent
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys:
# - ANTHROPIC_API_KEY (for Claude)
# - DATABASE_URL (for Snowflake/SQLite)
```

### 4. Verify Setup
```bash
python -c "from anthropic import Anthropic; print('✅ Anthropic SDK ready')"
python main.py  # Should run successfully
```

---

## Step 3: Development Workflow

### Workflow 1: Small Feature (Tool)
```
1. Open Copilot Workspace
2. Describe feature: "Add tool for X"
3. Copilot generates code
4. Review in workspace
5. Commit in workspace (or locally)
6. Pull changes locally
7. Test: python main.py
8. Verify: pytest tests/
9. Push
```

### Workflow 2: Medium Feature (New Node)
```
1. Open Copilot Workspace
2. Ask: "Add node for X workflow"
3. Copilot generates:
   - New node function
   - Wiring in graph
   - Router logic updates
4. Review changes
5. Pull locally & test
6. Run: python main.py (with mocked data)
7. Check logs for correctness
8. Commit & push
```

### Workflow 3: Complex Feature (Slack Integration)
```
1. Open Copilot Workspace
2. Describe multi-step requirement
3. Copilot breaks into pieces:
   - slack_tool.py
   - jira_tool.py
   - New nodes for workflow
   - Update main.py
4. Review each piece
5. Pull locally
6. Test each tool individually
7. Test full workflow with mock data
8. Run against real Claude API
9. Commit & push
```

---

## Step 4: Code Review Checklist

### Before Committing (Use Copilot Chat)

Ask Copilot to review:
```
"Review [filename] for:
1. Pattern consistency (compared to existing code)
2. Error handling (all failures caught?)
3. State mutations (only changed fields returned?)
4. Tool registration (registered in main.py?)
5. Edge cases (what if X fails?)
6. Security issues (any vulnerabilities?)
"
```

### Before Testing Locally

Ask Copilot:
```
"What are the test cases I should run for this feature?"
→ It will generate pytest test cases
```

### Copilot-Generated Tests
Run them:
```bash
pytest tests/test_my_feature.py -v
```

---

## Step 5: Testing Strategy

### Unit Tests (Fast, Isolated)
```bash
# Test individual tools
pytest tests/test_tools/ -v

# Test individual nodes
pytest tests/test_orchestrator.py::test_planner_node -v

# Test executor
pytest tests/test_executor.py -v
```

### Integration Tests (Full Flow)
```bash
# Test full workflow with mocked tools
pytest tests/test_integration.py -v

# Run with real Claude API (slower, costs money)
python main.py
```

### Real Execution (Production-Like)
```bash
# Uses real Claude API + your data
python main.py

# Check logs
tail -f logs/agent.log
```

---

## Step 6: Debugging with Copilot

### Copilot Can Help With:

**"Why is this test failing?"**
```
Copilot: Will analyze error, suggest fixes
You: Verify the fix is correct
```

**"Trace through this execution flow"**
```
Copilot: Will explain what happens step-by-step
You: Verify it matches your expectation
```

**"Generate debug logging"**
```
Copilot: Will add detailed logs
You: Run and review output
```

### You Still Need To:
- Run `python main.py` with real API
- Check actual Claude responses
- Verify tool outputs are correct
- Monitor token usage / costs

---

## Step 7: Committing & Pushing

### From Copilot Workspace
```
1. Open Git panel (left sidebar)
2. Stage changes
3. Write commit message (ask Copilot to help)
4. Commit & Push
```

### From Local Terminal
```bash
# Review what you're committing
git status
git diff

# Stage files
git add src/tools/my_tool.py

# Ask Copilot for message
echo "Copilot, write a commit message for adding Slack tool"

# Commit
git commit -m "Add Slack tool for reading data requests"

# Push
git push origin feature/slack-integration
```

---

## Step 8: Create Pull Request

### Option A: From GitHub Web
1. Go to your repo on GitHub.com
2. Click "New Pull Request"
3. Select your branch
4. Add description (ask Copilot to write it)
5. Create PR

### Option B: From Terminal
```bash
gh pr create \
  --title "Add Slack integration" \
  --body "Enables reading data requests from Slack #data-requests channel"
```

---

## Example: Real Development Session

### Session Goal: Add Slack Tool

### Step 1: Open Copilot Workspace
```
URL: https://copilot.github.com
Select: multi-step-agent repo
Wait: Indexing complete
```

### Step 2: Ask Copilot
```
"I want to add Slack integration to read messages from 
#data-requests channel. Create:

1. src/tools/slack_tool.py with:
   - listen_to_channel(channel_id) → returns message + jira_link
   - send_message(channel_id, message) → sends response

2. Update main.py to register the tools:
   - executor.register_tool("slack_listen", SlackTool.listen_to_channel)
   - executor.register_tool("slack_send", SlackTool.send_message)

3. Add SLACK_BOT_TOKEN to .env example

Follow the pattern in src/tools/sql_tool.py"
```

### Step 3: Copilot Generates
- Creates `src/tools/slack_tool.py`
- Updates `main.py` with registrations
- Updates `.env.example`

### Step 4: Review (Still in Workspace)
```
"Review slack_tool.py for:
1. Error handling
2. Return value structure
3. Any missing edge cases"

Copilot explains & suggests improvements
```

### Step 5: Commit in Workspace
```
Copilot: "Write a commit message for this"
Result: "Add Slack tool for reading data requests"
Action: Commit & Push
```

### Step 6: Pull Locally
```bash
git pull origin main
```

### Step 7: Test Locally
```bash
# Create test file
pytest tests/test_slack_tool.py -v

# Run full agent (uses real Claude API)
python main.py
```

### Step 8: Create PR
```bash
gh pr create --title "Add Slack integration" \
             --body "Enables reading data requests from #data-requests channel"
```

---

## Dos & Don'ts

### ✅ DO

- Use Copilot for code generation (saves time)
- Test generated code locally (safety)
- Ask Copilot for reviews (catches issues)
- Use real Claude API for execution (production-grade)
- Keep audit trails in logs (debugging)
- Ask Copilot to write tests (coverage)

### ❌ DON'T

- Accept code without reviewing (bugs)
- Commit without testing (breaks main)
- Ignore Copilot's warnings (learn from them)
- Modify core patterns (breaks architecture)
- Skip the approval gate (data safety)
- Push to main directly (use PRs)

---

## Cost Optimization

### Copilot Workspace (Development)
- Free with Copilot subscription
- No API calls = No cost
- Generate as much code as you want

### Claude API (Production)
- Costs money per token
- Use **prompt caching** (enabled in code)
- Saves 90% on repeated system prompts
- Estimate: ~$0.81 per 1M tokens

### Cost-Saving Tips
```
1. Test with python main.py (real Claude API)
2. Watch token usage in logs
3. Use caching for repeated patterns
4. Batch similar requests
5. Monitor costs: openai.com/account/usage (for reference)
```

---

## Troubleshooting

### Copilot Workspace Issues

**"Copilot isn't suggesting code"**
- Try: Reload the page
- Try: Open copilot-instructions.md (reads it)
- Try: Describe your request more specifically

**"Generated code doesn't match patterns"**
- Ask: "Follow the pattern in sql_tool.py"
- Reference: Existing files explicitly
- Review: Code before committing

### Local Testing Issues

**"python main.py fails"**
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Check dependencies
pip list | grep anthropic

# Check environment
python -c "import os; print(os.getenv('ANTHROPIC_API_KEY'))"
```

**"Tests fail"**
```bash
# Run with verbose output
pytest -vvv tests/test_my_feature.py

# Ask Copilot to debug
"Why does this test fail: [error message]"
```

---

## Quick Reference

| Need | Where | How |
|------|-------|-----|
| Generate code | Copilot Workspace | Describe feature |
| Write tests | Copilot Chat | "Write tests for X" |
| Review code | Copilot Chat | "Review this code" |
| Debug issue | Copilot Chat | "Why does this fail?" |
| Test locally | Terminal | `python main.py` |
| Test isolated | Terminal | `pytest tests/` |
| Commit | Git | `git commit -m "..."` |
| Push | Terminal | `git push origin branch` |
| Create PR | GitHub | `gh pr create` |

---

## Summary

**This hybrid approach gives you:**

✅ **Fast Development** - Copilot generates 80% of code  
✅ **Code Quality** - Copilot reviews for patterns & issues  
✅ **Production Reliability** - Claude API handles execution  
✅ **Cost Effective** - No API calls during development  
✅ **Maintainable** - Consistent patterns, good documentation  
✅ **Auditable** - Complete execution logs  
✅ **Scalable** - Easy to add features via Copilot  

**Ready to start developing?**

1. Go to https://copilot.github.com
2. Open your repo
3. Describe what you want to build
4. Copilot generates code
5. Review, test, commit!
