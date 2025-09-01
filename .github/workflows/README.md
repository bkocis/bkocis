# GitHub Actions Workflows

## Weekly Summary Workflow

### Overview
The `weekly-summary.yml` workflow automatically generates and updates a weekly summary of repository activity. It runs every Sunday at 6:00 AM UTC and analyzes the past week's:

- 🔨 Commits and contributors
- 🔀 Pull requests (opened, merged, closed)
- 🐛 Issues activity
- 🚀 New releases
- 📊 Repository statistics

### Schedule
- **Automatic**: Every Sunday at 6:00 AM UTC
- **Manual**: Can be triggered manually via GitHub Actions UI

### Configuration

#### Customizing the Schedule
To change when the workflow runs, modify the cron expression in `weekly-summary.yml`:

```yaml
schedule:
  # Current: Every Sunday at 6:00 AM UTC
  - cron: '0 6 * * 0'
  
  # Examples:
  # Every day at midnight: '0 0 * * *'
  # Every Monday at 9 AM: '0 9 * * 1'
  # Twice a week (Mon & Thu at 10 AM): '0 10 * * 1,4'
```

#### Customizing the Summary Period
To analyze a different time period (default is 7 days), modify the `days` parameter in `generate_summary.py`:

```python
# Current: Last 7 days
activity_data = github_client.get_repository_activity(days=7)

# Examples:
# Last 14 days: days=14
# Last 30 days: days=30
```

### How It Works

1. **Checkout**: Downloads the repository code
2. **Setup**: Installs Python and required dependencies
3. **Analysis**: Uses GitHub API to fetch repository activity
4. **Summary**: Generates a markdown summary of changes
5. **Update**: Updates the README.md with the new summary
6. **Commit**: Automatically commits and pushes changes

### Permissions Required

The workflow needs these permissions (already configured):
- `contents: write` - To update README.md
- `pull-requests: write` - For future PR creation features

### Generated Summary Format

The workflow adds a "📊 Weekly Summary" section to your README.md with:

```markdown
## 📊 Weekly Summary

**Repository:** repository-name ⭐ 123 🍴 45
📝 Repository description

**🔨 Commits:** 15 commits by 3 contributor(s)

Recent commits:
• `abc1234` Fixed bug in authentication - John Doe
• `def5678` Added new feature - Jane Smith
• `ghi9012` Updated documentation - Bob Wilson

**🔀 Pull Requests:** 2 open, 3 merged, 1 closed

Recently merged:
• #42: Implement user dashboard
• #41: Fix mobile responsiveness
• #40: Add unit tests for API endpoints
```

### Troubleshooting

#### Workflow Not Running
- Check if the repository has GitHub Actions enabled
- Verify the workflow file is in `.github/workflows/`
- Check the Actions tab for error messages

#### Permission Errors
- Ensure the `GITHUB_TOKEN` has sufficient permissions
- Check repository settings → Actions → General → Workflow permissions

#### Script Errors
- Check the Actions logs for detailed error messages
- Verify the Python script has correct GitHub API endpoints
- Ensure all required environment variables are set

### Customization Ideas

1. **Add Slack/Discord notifications** when summary is updated
2. **Create a pull request** instead of direct commits
3. **Include code quality metrics** from other tools
4. **Generate charts and graphs** of activity trends
5. **Send email summaries** to team members
6. **Integrate with project management tools** (Jira, Notion, etc.)

### Dependencies

The workflow uses these Python packages:
- `requests` - For GitHub API calls
- `python-dateutil` - For date parsing and manipulation

No additional GitHub secrets or tokens are required beyond the default `GITHUB_TOKEN`.
