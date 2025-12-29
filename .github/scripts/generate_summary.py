#!/usr/bin/env python3
"""
Weekly GitHub Repository Summary Generator

This script connects to GitHub's API to gather repository activity from the last week
and generates a summary of changes, commits, pull requests, and issues.
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

import requests


class GitHubAPIClient:
    """GitHub REST API Client for repository analysis"""
    
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
        now = datetime.utcnow()
        since = (now - timedelta(days=days)).isoformat() + "Z"
        since_date = now - timedelta(days=days)
        
        repo_info = self._get_repository_info()
        commits = self._get_commits(since)
        
        # Add repo info to commits for consistency with multi-repo format
        repo_full_name = f"{self.owner}/{self.repo}"
        for commit in commits:
            commit["_repo"] = repo_full_name
            commit["_repo_info"] = {
                "name": repo_info.get("name", self.repo) if repo_info else self.repo,
                "full_name": repo_full_name,
                "description": repo_info.get("description", "") if repo_info else "",
                "html_url": repo_info.get("html_url", f"https://github.com/{repo_full_name}") if repo_info else f"https://github.com/{repo_full_name}"
            }
        
        activity = {
            "commits": commits,
            "pull_requests": self._get_pull_requests(since),
            "issues": self._get_issues(since),
            "releases": self._get_releases(since),
            "repository_info": repo_info,
            "date_range": {
                "since": since_date,
                "until": now
            }
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
        return self._get_commits_for_repo(self.owner, self.repo, since)
    
    def _get_commits_for_repo(self, owner: str, repo: str, since: str) -> List[Dict]:
        """Get commits for a specific repository since specified date"""
        params = {"since": since, "per_page": 100}
        commits = self._make_request(f"/repos/{owner}/{repo}/commits", params)
        
        if not commits:
            return []
        
        # Filter commits to ensure they're within the date range (since to now)
        # GitHub API might return commits slightly outside the range
        since_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
        now_date = datetime.utcnow().replace(tzinfo=since_date.tzinfo)
        filtered_commits = []
        
        for commit in commits:
            commit_date_str = commit.get("commit", {}).get("author", {}).get("date", "")
            if commit_date_str:
                try:
                    commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                    # Only include commits between since_date and now_date
                    if since_date <= commit_date <= now_date:
                        filtered_commits.append(commit)
                except (ValueError, AttributeError):
                    # If date parsing fails, include the commit (better safe than sorry)
                    filtered_commits.append(commit)
            else:
                # If no date, include it
                filtered_commits.append(commit)
        
        return filtered_commits
    
    def _get_pull_requests(self, since: str) -> List[Dict]:
        """Get pull requests updated since specified date"""
        return self._get_pull_requests_for_repo(self.owner, self.repo, since)
    
    def _get_pull_requests_for_repo(self, owner: str, repo: str, since: str) -> List[Dict]:
        """Get pull requests for a specific repository updated since specified date"""
        params = {"state": "all", "sort": "updated", "direction": "desc", "per_page": 100}
        prs = self._make_request(f"/repos/{owner}/{repo}/pulls", params)
        
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
        return self._get_issues_for_repo(self.owner, self.repo, since)
    
    def _get_issues_for_repo(self, owner: str, repo: str, since: str) -> List[Dict]:
        """Get issues for a specific repository updated since specified date"""
        params = {"state": "all", "sort": "updated", "direction": "desc", "since": since, "per_page": 100}
        issues = self._make_request(f"/repos/{owner}/{repo}/issues", params)
        
        # Filter out pull requests (GitHub API includes PRs in issues)
        if issues:
            issues = [issue for issue in issues if "pull_request" not in issue]
            
        return issues or []
    
    def _get_releases(self, since: str) -> List[Dict]:
        """Get releases published since specified date"""
        return self._get_releases_for_repo(self.owner, self.repo, since)
    
    def _get_releases_for_repo(self, owner: str, repo: str, since: str) -> List[Dict]:
        """Get releases for a specific repository published since specified date"""
        releases = self._make_request(f"/repos/{owner}/{repo}/releases")
        
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
    
    def _get_starred_repositories(self, days: int = 30) -> List[Dict]:
        """Get repositories starred by the user in the last N days
        
        curl -X GET "https://api.github.com/user/starred?sort=created&direction=desc&per_page=100&page=1" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3.star+json" \
  -H "User-Agent: GitHub-Weekly-Summary-Bot/1.0" | jq '.[0]'
        
        
        """
        starred_repos = []
        page = 1
        per_page = 100
        now = datetime.now(timezone.utc)
        since_date = now - timedelta(days=days)
        
        # Use special header to get starred_at field (matches working curl command)
        headers_with_star = {
            **self.headers,
            "Accept": "application/vnd.github.v3.star+json"
        }
        
        print(f"⭐ Fetching starred repositories from the past {days} days...")
        
        while True:
            params = {
                "sort": "created",
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }
            
            try:
                url = f"{self.base_url}/user/starred"
                response = requests.get(url, headers=headers_with_star, params=params)
                response.raise_for_status()
                repos = response.json()
                
                if not repos or not isinstance(repos, list):
                    break
                
                # Filter repos by starred_at date
                # Note: sort=created sorts by repo creation date, not starred date,
                # so we need to check all repos and filter by starred_at
                for item in repos:
                    starred_at_str = item.get("starred_at")
                    repo_data = item.get("repo", {})
                    
                    if starred_at_str:
                        try:
                            starred_at = datetime.fromisoformat(starred_at_str.replace("Z", "+00:00"))
                            if starred_at >= since_date:
                                # Extract only the needed fields from the repo object
                                extracted_repo = {
                                    "starred_at": starred_at_str,
                                    "name": repo_data.get("name", ""),
                                    "full_name": repo_data.get("full_name", ""),
                                    "html_url": repo_data.get("html_url", ""),
                                    "description": repo_data.get("description", ""),
                                    "owner": repo_data.get("owner", {})
                                }
                                starred_repos.append(extracted_repo)
                            # Continue checking all repos since sort is by creation date, not starred date
                        except (ValueError, AttributeError) as e:
                            # If date parsing fails, skip this repo
                            print(f"   Warning: Could not parse starred_at date: {e}")
                            continue
                    # If no starred_at field, skip this repo
                    # This shouldn't happen with the star+json header, but handle it gracefully
                
                # If we got fewer results than per_page, we're done
                if len(repos) < per_page:
                    break
                
                # Continue to next page to check all starred repos
                # We can't stop early since sorting is by creation date, not starred date
                page += 1
                
            except requests.RequestException as e:
                print(f"   Error fetching starred repositories: {e}")
                break
        
        # Sort by starred_at date (most recent first)
        starred_repos.sort(
            key=lambda x: (
                datetime.fromisoformat(x.get("starred_at", "").replace("Z", "+00:00"))
                if x.get("starred_at") else datetime.min.replace(tzinfo=timezone.utc)
            ),
            reverse=True
        )
        
        print(f"   Found {len(starred_repos)} starred repositories")
        
        return starred_repos
    
    def _get_all_repositories(self, include_private: bool = True) -> List[Dict]:
        """Get all repositories for the authenticated user"""
        repos = []
        page = 1
        per_page = 100
        
        while True:
            params = {
                "affiliation": "owner",  # Only repos owned by the user
                "sort": "updated",
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }
            
            response_data = self._make_request("/user/repos", params)
            if not response_data:
                break
                
            # Filter out archived repos and optionally private repos
            for repo in response_data:
                if not repo.get("archived", False):
                    if include_private or not repo.get("private", False):
                        repos.append(repo)
            
            # Check if we got fewer results than per_page (last page)
            if len(response_data) < per_page:
                break
                
            page += 1
        
        return repos
    
    def get_all_repositories_activity(self, days: int = 7, include_private: bool = True) -> Dict[str, Any]:
        """Get aggregated activity across all repositories for the last N days"""
        now = datetime.utcnow()
        since = (now - timedelta(days=days)).isoformat() + "Z"
        since_date = now - timedelta(days=days)
        
        print(f"📦 Fetching all repositories for {self.owner}...")
        all_repos = self._get_all_repositories(include_private=include_private)
        print(f"   Found {len(all_repos)} repositories")
        
        all_commits = []
        all_prs = []
        all_issues = []
        all_releases = []
        total_stars = 0
        total_forks = 0
        
        for idx, repo in enumerate(all_repos, 1):
            repo_name = repo.get("full_name", "unknown")
            print(f"   [{idx}/{len(all_repos)}] Checking {repo_name}...")
            
            # Get owner and repo name for this repository
            repo_owner = repo.get("owner", {}).get("login", self.owner)
            repo_name_only = repo.get("name", "unknown")
            
            # Create a temporary client for this specific repo to avoid modifying instance state
            # We'll make direct API calls with the repo info
            commits = self._get_commits_for_repo(repo_owner, repo_name_only, since)
            prs = self._get_pull_requests_for_repo(repo_owner, repo_name_only, since)
            issues = self._get_issues_for_repo(repo_owner, repo_name_only, since)
            releases = self._get_releases_for_repo(repo_owner, repo_name_only, since)
            
            # Add repo info to commits for tracking
            for commit in commits:
                commit["_repo"] = repo_name
                commit["_repo_info"] = {
                    "name": repo.get("name", repo_name_only),
                    "full_name": repo_name,
                    "description": repo.get("description", ""),
                    "html_url": repo.get("html_url", "")
                }
            for pr in prs:
                pr["_repo"] = repo_name
            for issue in issues:
                issue["_repo"] = repo_name
            for release in releases:
                release["_repo"] = repo_name
            
            all_commits.extend(commits)
            all_prs.extend(prs)
            all_issues.extend(issues)
            all_releases.extend(releases)
            
            total_stars += repo.get("stargazers_count", 0)
            total_forks += repo.get("forks_count", 0)
        
        # Sort commits by date (most recent first)
        all_commits.sort(key=lambda x: x.get("commit", {}).get("author", {}).get("date", ""), reverse=True)
        
        # Aggregate repository info
        aggregated_info = {
            "name": f"{self.owner}'s repositories",
            "description": f"Aggregated activity across {len(all_repos)} repositories",
            "stargazers_count": total_stars,
            "forks_count": total_forks,
            "total_repositories": len(all_repos)
        }
        
        return {
            "commits": all_commits,
            "pull_requests": all_prs,
            "issues": all_issues,
            "releases": all_releases,
            "repository_info": aggregated_info,
            "date_range": {
                "since": since_date,
                "until": now
            }
        }


class SummaryGenerator:
    """Generate human-readable summaries from GitHub activity data"""
    
    def __init__(self, activity_data: Dict[str, Any], date_range: Optional[Dict[str, datetime]] = None):
        self.activity = activity_data
        self.date_range = date_range or {}
        
    def generate_weekly_summary(self) -> str:
        """Generate a weekly summary matching the current README.md format"""
        summary_parts = []
        
        # Repository overview - always include this
        repo_info = self.activity.get("repository_info", {})
        if repo_info:
            summary_parts.append(self._format_repository_overview(repo_info))
        
        # Commits summary - always include this  
        commits = self.activity.get("commits", [])
        summary_parts.append(self._format_commits_summary(commits))
        
        # Starred repositories summary - always include this
        starred_repos = self.activity.get("starred_repositories", [])
        if starred_repos:
            summary_parts.append(self._format_starred_repositories_summary(starred_repos))
        
        return "## Weekly Summary\n\n" + "\n\n".join(summary_parts)
    
    def _format_repository_overview(self, repo_info: Dict) -> str:
        """Format repository overview with professional styling"""
        name = repo_info.get("name", "Unknown")
        description = repo_info.get("description")
        if description is None or description.strip() == "":
            description = "Personal repository showcasing various projects and contributions"
        stars = repo_info.get("stargazers_count", 0)
        forks = repo_info.get("forks_count", 0)
        total_repos = repo_info.get("total_repositories")
        
        overview = f"**Community:** {stars} stars • {forks} forks"
        if total_repos:
            overview += f" • {total_repos} repositories"
        
        return overview
    
    def _format_commits_summary(self, commits: List[Dict]) -> str:
        """Format commits summary with professional styling"""
        commit_count = len(commits)
        authors = set()
        repos_with_commits = set()
        
        for commit in commits:
            author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
            authors.add(author)
            repo = commit.get("_repo", "unknown")
            if repo:
                repos_with_commits.add(repo)
        
        # Create a more professional header
        contributor_text = "contributor" if len(authors) == 1 else "contributors"
        commit_text = "commit" if commit_count == 1 else "commits"
        repo_text = "repository" if len(repos_with_commits) == 1 else "repositories"
        
        summary = f"**Recent Activity:** {commit_count} {commit_text} from {len(authors)} {contributor_text}"
        if len(repos_with_commits) > 0:
            summary += f" across {len(repos_with_commits)} {repo_text}"
        
        # Add date range if available
        if self.date_range:
            since_date = self.date_range.get("since")
            until_date = self.date_range.get("until")
            if since_date and until_date:
                since_str = since_date.strftime("%B %d, %Y")
                until_str = until_date.strftime("%B %d, %Y")
                summary += f"\n**Date Range:** {since_str} to {until_str}"
        
        if commit_count > 0:
            # Blacklist repositories that should not be shown
            blacklisted_repos = {
                "bkocis/bkocis",
                "bkocis/bewerbungen"
            }
            
            # Group all commits by repository (not just recent ones)
            commits_by_repo = {}
            for commit in commits:
                repo = commit.get("_repo", "unknown")
                # Skip blacklisted repositories
                if repo in blacklisted_repos:
                    continue
                if repo not in commits_by_repo:
                    commits_by_repo[repo] = []
                commits_by_repo[repo].append(commit)
            
            summary += "\n\n**Latest Changes:**"
            
            # Format commits grouped by repository
            repo_sections = []
            for repo_full_name, repo_commits in commits_by_repo.items():
                repo_info = repo_commits[0].get("_repo_info", {})
                repo_name = repo_info.get("name", repo_full_name.split("/")[-1])
                repo_description = repo_info.get("description", "")
                repo_url = repo_info.get("html_url", "")
                
                # Get last 3 commits for this repo
                last_3_commits = repo_commits[:3]
                commit_messages = []
                for commit in last_3_commits:
                    message = commit.get("commit", {}).get("message", "").split('\n')[0]
                    # Clean up automated commit messages
                    if message.startswith("🤖"):
                        message = message.replace("🤖 ", "").strip()
                    commit_messages.append(message)
                
                # Create repo header with commits in brackets on the same line (using "-" instead of "###")
                if repo_url:
                    repo_header = f"\n- [{repo_name}]({repo_url})"
                else:
                    repo_header = f"\n- {repo_name}"

                # Add description on a separate line if it exists
                if repo_description:
                    repo_header += f"\n{repo_description}"
                
                # Add commits in brackets on the same line as repo name
                if commit_messages:
                    commits_text = ", ".join(commit_messages)
                    repo_header += f" ({commits_text})"
    
                repo_sections.append(repo_header)
            
            # Join all repo sections with double newline between repos
            summary += "\n\n".join(repo_sections)
        else:
            summary += "\n\n*No recent commits this week*"
        
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
    
    def _format_starred_repositories_summary(self, starred_repos: List[Dict]) -> str:
        """Format starred repositories summary"""
        count = len(starred_repos)
        repo_text = "repository" if count == 1 else "repositories"
        
        summary = f"**Recently Starred:** {count} {repo_text} in the past month"
        
        if starred_repos:
            for repo in starred_repos[:10]:  # Show up to 10 most recently starred
                # Get repository information from extracted data
                full_name = repo.get("full_name", "")
                description = repo.get("description", "")
                html_url = repo.get("html_url", "")
                repo_name = repo.get("name", "")
                
                # Get owner information for fallback
                owner = repo.get("owner", {})
                if isinstance(owner, dict):
                    owner_login = owner.get("login", "")
                else:
                    owner_login = ""
                
                # Fallback: construct full_name from owner and name if not present
                if not full_name:
                    if owner_login and repo_name:
                        full_name = f"{owner_login}/{repo_name}"
                    elif repo_name:
                        # If we only have name, try to get owner from other fields
                        if isinstance(owner, str):
                            full_name = f"{owner}/{repo_name}"
                
                # Fallback: construct html_url if not present
                if not html_url:
                    if full_name:
                        html_url = f"https://github.com/{full_name}"
                    elif repo_name and owner_login:
                        html_url = f"https://github.com/{owner_login}/{repo_name}"
                
                # Create the repository entry with proper markdown formatting
                if html_url and full_name:
                    repo_entry = f"\n- [{full_name}]({html_url})"
                elif html_url and repo_name and owner_login:
                    # Fallback: use owner/repo_name if full_name not available
                    full_name_fallback = f"{owner_login}/{repo_name}"
                    repo_entry = f"\n- [{full_name_fallback}]({html_url})"
                elif full_name:
                    repo_entry = f"\n- {full_name}"
                elif repo_name and owner_login:
                    repo_entry = f"\n- [{owner_login}/{repo_name}](https://github.com/{owner_login}/{repo_name})"
                elif repo_name:
                    repo_entry = f"\n- {repo_name}"
                else:
                    # Last resort: print debug info and skip
                    print(f"   Warning: Could not extract repository info from starred repo. Keys: {list(repo.keys())}")
                    continue
                
                # Add description if available
                if description:
                    repo_entry += f" - {description}"
                
                summary += repo_entry
        else:
            summary += "\n\n*No repositories starred in the past month*"
        
        return summary


def update_readme_with_summary(summary: str, readme_path: str = "README.md"):
    """Update README.md with the weekly summary while preserving existing structure"""
    try:
        # Resolve absolute path to ensure we're working with the correct file
        if not os.path.isabs(readme_path):
            # Try to find README.md relative to script location or current working directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.dirname(os.path.dirname(script_dir))
            potential_path = os.path.join(repo_root, readme_path)
            
            # Use repo root path if it exists, otherwise use current working directory
            if os.path.exists(potential_path):
                readme_path = potential_path
            else:
                # Fallback to current working directory (for when script runs from repo root)
                readme_path = os.path.abspath(readme_path)
        
        print(f"📝 Reading README from: {readme_path}")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Look for the specific pattern in the current README.md
        # Match from "## Weekly Summary" until we find "<details>" (with any number of newlines/whitespace in between)
        summary_pattern = r'(## Weekly Summary.*?)(?=\n<details>)'
        
        if re.search(summary_pattern, content, re.DOTALL):
            # Replace existing summary section while preserving the detailed project sections
            new_content = re.sub(summary_pattern, summary.rstrip() + '\n', content, flags=re.DOTALL)
            print(f"✅ Found and replaced Weekly Summary section")
        else:
            # If pattern not found, try a broader pattern that matches until end of file
            broader_pattern = r'(## Weekly Summary.*?)(?=\n<details>|\Z)'
            if re.search(broader_pattern, content, re.DOTALL):
                new_content = re.sub(broader_pattern, summary.rstrip() + '\n', content, flags=re.DOTALL)
                print(f"✅ Found Weekly Summary with broader pattern")
            else:
                # Fallback: add summary after greeting
                lines = content.split('\n')
                insert_position = 2  # After "Hi,👋!" and empty line
                lines.insert(insert_position, '\n' + summary)
                new_content = '\n'.join(lines)
                print(f"⚠️ Weekly Summary section not found, inserted after greeting")
        
        # Verify the content actually changed
        if new_content == original_content:
            print(f"⚠️ Warning: Generated summary is identical to existing content")
            print(f"   This might mean there are no new commits or changes")
        else:
            # Write the updated content
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Verify the write was successful
            with open(readme_path, 'r', encoding='utf-8') as f:
                written_content = f.read()
            
            if written_content == new_content:
                print(f"✅ README.md successfully updated at {readme_path}")
            else:
                print(f"❌ Error: File write verification failed")
                sys.exit(1)
            
    except FileNotFoundError:
        print(f"❌ README.md not found at {readme_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error updating README.md: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main function to run the weekly summary generation"""
    # Get environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    check_all_repos = os.getenv("CHECK_ALL_REPOS", "true").lower() == "true"
    
    if not github_token:
        print("❌ Missing required environment variable: GITHUB_TOKEN")
        sys.exit(1)
    
    if not repo_owner:
        print("❌ Missing required environment variable: REPO_OWNER")
        sys.exit(1)
    
    # Initialize GitHub API client (repo_name can be None if checking all repos)
    if not repo_name:
        repo_name = "placeholder"  # Will be ignored when checking all repos
    
    github_client = GitHubAPIClient(github_token, repo_owner, repo_name)
    
    # Get repository activity for the last week
    if check_all_repos:
        print(f"🔍 Generating weekly summary for all repositories owned by {repo_owner}")
        print("📊 Fetching activity from all repositories...")
        activity_data = github_client.get_all_repositories_activity(days=7, include_private=True)
    else:
        if not repo_name:
            print("❌ REPO_NAME required when CHECK_ALL_REPOS=false")
            sys.exit(1)
        print(f"🔍 Generating weekly summary for {repo_owner}/{repo_name}")
        print("📊 Fetching repository activity...")
        activity_data = github_client.get_repository_activity(days=7)

    # Get starred repositories
    print("⭐ Fetching starred repositories...")
    starred_repos = github_client._get_starred_repositories(days=30)
    activity_data["starred_repositories"] = starred_repos
    
    # Extract date range from activity data
    date_range = activity_data.pop("date_range", None)
    
    # Generate summary
    print("📝 Generating summary...")
    summary_generator = SummaryGenerator(activity_data, date_range=date_range)
    weekly_summary = summary_generator.generate_weekly_summary()
    
    # Update README
    print("📄 Updating README.md...")
    update_readme_with_summary(weekly_summary)
    
    print("🎉 Weekly summary generation completed!")


if __name__ == "__main__":
    main()
