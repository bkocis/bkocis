#!/usr/bin/env python3
"""
Weekly GitHub Repository Summary Generator

This script connects to GitHub's API to gather repository activity from the last week
and generates a summary of changes, commits, pull requests, and issues.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re


class GitHubMCPClient:
    """GitHub MCP (Model Context Protocol) Client for repository analysis"""
    
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Weekly-Summary-Bot/1.0"
        }
        
    def get_repository_activity(self, days: int = 7) -> Dict[str, Any]:
        """Get repository activity for the last N days"""
        since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        
        activity = {
            "commits": self._get_commits(since),
            "pull_requests": self._get_pull_requests(since),
            "issues": self._get_issues(since),
            "releases": self._get_releases(since),
            "repository_info": self._get_repository_info()
        }
        
        return activity
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to GitHub API"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, params=params or {})
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
            return None
    
    def _get_commits(self, since: str) -> List[Dict]:
        """Get commits since specified date"""
        params = {"since": since, "per_page": 100}
        commits = self._make_request(f"/repos/{self.owner}/{self.repo}/commits", params)
        return commits or []
    
    def _get_pull_requests(self, since: str) -> List[Dict]:
        """Get pull requests updated since specified date"""
        params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 100}
        prs = self._make_request(f"/repos/{self.owner}/{self.repo}/pulls", params)
        
        if not prs:
            return []
            
        # Filter PRs updated since the specified date
        since_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
        filtered_prs = []
        
        for pr in prs:
            updated_at = datetime.fromisoformat(pr["updated_at"].replace("Z", "+00:00"))
            if updated_at >= since_date:
                filtered_prs.append(pr)
                
        return filtered_prs
    
    def _get_issues(self, since: str) -> List[Dict]:
        """Get issues updated since specified date"""
        params = {"state": "all", "sort": "updated", "direction": "desc", "since": since, "per_page": 100}
        issues = self._make_request(f"/repos/{self.owner}/{self.repo}/issues", params)
        
        # Filter out pull requests (GitHub API includes PRs in issues)
        if issues:
            issues = [issue for issue in issues if "pull_request" not in issue]
            
        return issues or []
    
    def _get_releases(self, since: str) -> List[Dict]:
        """Get releases published since specified date"""
        releases = self._make_request(f"/repos/{self.owner}/{self.repo}/releases")
        
        if not releases:
            return []
            
        since_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
        filtered_releases = []
        
        for release in releases:
            published_at = release.get("published_at")
            if published_at:
                published_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if published_date >= since_date:
                    filtered_releases.append(release)
                    
        return filtered_releases
    
    def _get_repository_info(self) -> Optional[Dict]:
        """Get basic repository information"""
        return self._make_request(f"/repos/{self.owner}/{self.repo}")


class SummaryGenerator:
    """Generate human-readable summaries from GitHub activity data"""
    
    def __init__(self, activity_data: Dict[str, Any]):
        self.activity = activity_data
        
    def generate_weekly_summary(self) -> str:
        """Generate a comprehensive weekly summary"""
        summary_parts = []
        
        # Repository overview
        repo_info = self.activity.get("repository_info", {})
        if repo_info:
            summary_parts.append(self._format_repository_overview(repo_info))
        
        # Commits summary
        commits = self.activity.get("commits", [])
        if commits:
            summary_parts.append(self._format_commits_summary(commits))
        
        # Pull requests summary
        prs = self.activity.get("pull_requests", [])
        if prs:
            summary_parts.append(self._format_pull_requests_summary(prs))
        
        # Issues summary
        issues = self.activity.get("issues", [])
        if issues:
            summary_parts.append(self._format_issues_summary(issues))
        
        # Releases summary
        releases = self.activity.get("releases", [])
        if releases:
            summary_parts.append(self._format_releases_summary(releases))
        
        if not summary_parts:
            return "## Weekly Summary\n\nNo significant activity in the past week.\n"
        
        return "## Weekly Summary\n\n" + "\n\n".join(summary_parts) + "\n"
    
    def _format_repository_overview(self, repo_info: Dict) -> str:
        """Format repository overview"""
        name = repo_info.get("name", "Unknown")
        description = repo_info.get("description", "No description available")
        stars = repo_info.get("stargazers_count", 0)
        forks = repo_info.get("forks_count", 0)
        
        return f"**Repository:** {name} | Stars: {stars} | Forks: {forks}  \n*Description:* {description}"
    
    def _format_commits_summary(self, commits: List[Dict]) -> str:
        """Format commits summary"""
        commit_count = len(commits)
        authors = set()
        
        for commit in commits:
            author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
            authors.add(author)
        
        summary = f"**Commits:** {commit_count} commits by {len(authors)} contributor(s)"
        
        if commit_count > 0:
            recent_commits = commits[:3]  # Show last 3 commits
            summary += "  \nRecent commits:"
            
            for commit in recent_commits:
                message = commit.get("commit", {}).get("message", "").split('\n')[0]
                author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
                sha = commit.get("sha", "")[:7]
                summary += f"\n- `{sha}` {message} - {author}"
        
        return summary
    
    def _format_pull_requests_summary(self, prs: List[Dict]) -> str:
        """Format pull requests summary"""
        open_prs = [pr for pr in prs if pr.get("state") == "open"]
        closed_prs = [pr for pr in prs if pr.get("state") == "closed"]
        merged_prs = [pr for pr in prs if pr.get("merged_at")]
        
        summary = f"**Pull Requests:** {len(open_prs)} open | {len(merged_prs)} merged | {len(closed_prs)} closed"
        
        if merged_prs:
            summary += "  \nRecently merged:"
            for pr in merged_prs[:3]:
                title = pr.get("title", "Untitled")
                number = pr.get("number", "")
                summary += f"\n- #{number}: {title}"
        
        return summary
    
    def _format_issues_summary(self, issues: List[Dict]) -> str:
        """Format issues summary"""
        open_issues = [issue for issue in issues if issue.get("state") == "open"]
        closed_issues = [issue for issue in issues if issue.get("state") == "closed"]
        
        summary = f"**Issues:** {len(open_issues)} open | {len(closed_issues)} recently closed"
        
        if issues:
            summary += "  \nRecent activity:"
            for issue in issues[:3]:
                title = issue.get("title", "Untitled")
                number = issue.get("number", "")
                state = issue.get("state", "unknown")
                state_indicator = "[OPEN]" if state == "open" else "[CLOSED]"
                summary += f"\n- {state_indicator} #{number}: {title}"
        
        return summary
    
    def _format_releases_summary(self, releases: List[Dict]) -> str:
        """Format releases summary"""
        summary = f"**Releases:** {len(releases)} new release(s)"
        
        if releases:
            summary += "  \nLatest releases:"
            for release in releases:
                name = release.get("name") or release.get("tag_name", "Unnamed")
                tag = release.get("tag_name", "")
                summary += f"\n- {name} ({tag})"
        
        return summary


def update_readme_with_summary(summary: str, readme_path: str = "README.md"):
    """Update README.md with the weekly summary"""
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for existing summary section and replace it
        summary_pattern = r'## (📊 )?Weekly Summary.*?(?=\n##|\Z)'
        
        if re.search(summary_pattern, content, re.DOTALL):
            # Replace existing summary
            new_content = re.sub(summary_pattern, summary.rstrip(), content, flags=re.DOTALL)
        else:
            # Add summary after the first paragraph/section
            lines = content.split('\n')
            insert_position = 5  # After the header and emoji line
            
            lines.insert(insert_position, '\n' + summary)
            new_content = '\n'.join(lines)
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"✅ README.md updated with weekly summary")
        
    except FileNotFoundError:
        print(f"❌ README.md not found at {readme_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error updating README.md: {e}")
        sys.exit(1)


def main():
    """Main function to run the weekly summary generation"""
    # Get environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    if not all([github_token, repo_owner, repo_name]):
        print("❌ Missing required environment variables: GITHUB_TOKEN, REPO_OWNER, REPO_NAME")
        sys.exit(1)
    
    print(f"🔍 Generating weekly summary for {repo_owner}/{repo_name}")
    
    # Initialize GitHub MCP client
    github_client = GitHubMCPClient(github_token, repo_owner, repo_name)
    
    # Get repository activity for the last week
    print("📊 Fetching repository activity...")
    activity_data = github_client.get_repository_activity(days=7)
    
    # Generate summary
    print("📝 Generating summary...")
    summary_generator = SummaryGenerator(activity_data)
    weekly_summary = summary_generator.generate_weekly_summary()
    
    # Update README
    print("📄 Updating README.md...")
    update_readme_with_summary(weekly_summary)
    
    print("🎉 Weekly summary generation completed!")


if __name__ == "__main__":
    main()
