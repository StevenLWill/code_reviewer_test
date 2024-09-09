import os
from openai import OpenAI
import json
import requests
import logging
from base64 import b64decode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key = os.getenv('OPEN_AI_KEY')

# Setup OpenAI client
openai_client = OpenAI(
    api_key=api_key
)

def get_pr_diff():
    event_path = os.getenv('GITHUB_EVENT_PATH')
    
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
        
        pr_number = event_data['pull_request']['number']
        repo = os.getenv('GITHUB_REPOSITORY')
        
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        headers = {
            'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",
            'Accept': 'application/vnd.github.v3+json',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        files = response.json()
        return '\n'.join([f['patch'] for f in files])
    except Exception as e:
        logger.error(f"Error fetching PR diff: {str(e)}")
        raise

def review_code_with_rag(diff):
    prompt_template = f"""
    You are an AI code reviewer. Your task is to review the following code diff and provide feedback on potential improvements, best practices, and any issues you find:

    {diff}

    Provide a detailed analysis.
    """
    
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a code review assistant."},
                {"role": "user", "content": prompt_template},
            ]
        )
        
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")
        raise

def create_check_run(repo, sha, status='in_progress'):
    url = f"https://api.github.com/repos/{repo}/check-runs"
    headers = {
        'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.antiope-preview+json'
    }
    payload = {
        "name": "AI Code Review",
        "head_sha": sha,
        "status": status,
        "started_at": "2023-09-09T00:00:00Z",
        "output": {
            "title": "AI Code Review",
            "summary": "",
            "text": ""
        },
        "conclusion": "neutral"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()['id']

def update_check_run(repo, check_id, conclusion, output):
    url = f"https://api.github.com/repos/{repo}/check-runs/{check_id}"
    headers = {
        'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.antiope-preview+json'
    }
    payload = {
        "status": "completed",
        "conclusion": conclusion,
        "output": output
    }
    response = requests.patch(url, headers=headers, json=payload)
    response.raise_for_status()

def post_comment(repo, issue_number, body):
    url = f"https://api.github.com/repos/{repo}/issues/comments"
    headers = {
        'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
    }
    payload = {
        "body": body,
        "issue_number": issue_number
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

if __name__ == "__main__":
    try:
        # Fetch PR details
        event_path = os.getenv('GITHUB_EVENT_PATH')
        with open(event_path, 'r') as f:
            event_data = json.load(f)
        
        pr_number = event_data['pull_request']['number']
        repo = os.getenv('GITHUB_REPOSITORY')
        sha = event_data['pull_request']['head']['sha']

        # Create initial check run
        check_id = create_check_run(repo, sha)

        # Fetch PR diff
        diff = get_pr_diff()
        
        # Perform code review
        feedback = review_code_with_rag(diff)
        
        # Update check run with results
        output = {
            "title": "AI Code Review Results",
            "summary": "Detailed analysis below.",
            "text": feedback
        }
        update_check_run(repo, check_id, "success", output)

        # Post comment on PR
        post_comment(repo, pr_number, "AI Code Review completed. Please review the check run results.")

        logger.info("AI Code Review completed successfully.")
    except Exception as e:
        logger.error(f"Error during AI Code Review: {str(e)}")
        raise
