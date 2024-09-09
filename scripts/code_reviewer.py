import os
import requests
import logging
import json
from base64 import b64decode
from openai import OpenAI
import time
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key = os.getenv('OPEN_AI_KEY')

# Setup OpenAI client
openai_client = OpenAI(api_key=api_key)

def get_pr_details():
    event_path = os.getenv('GITHUB_EVENT_PATH')
    
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
        
        repo = os.getenv('GITHUB_REPOSITORY')
        pr_number = event_data['pull_request']['number']
        sha = event_data['pull_request']['head']['sha']
        
        logger.info(f"Repository: {repo}")
        logger.info(f"Pull Request Number: {pr_number}")
        logger.info(f"SHA: {sha}")
        
        return repo, pr_number, sha
    except Exception as e:
        logger.error(f"Error fetching PR details: {str(e)}")
        raise

def get_pr_diff():
    repo, pr_number, _ = get_pr_details()
    
    try:
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

    Provide a detailed analysis. When evaluating the code, consider the following criteria for approval:
    - Does the code follow best practices?
    - Are there any obvious bugs or errors?
    - Is the code well-organized and readable?
    - Are there any security concerns?

    If you believe the code meets these criteria and is ready for approval, state so clearly. Otherwise, suggest areas for improvement.

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
            "title": "AI Code Review Results",
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

def determine_approval(repo: str, pr_number: int, diff: str):
    prompt_template = f"""
    You are an AI code reviewer. Your task is to review the following code diff and determine if it is ready for approval:

    {diff}

    Based on your analysis, please respond with one of the following:
    - Approve: The changes are good to go and ready for merging.
    - Request Changes: There are issues that need to be addressed before approval.
    - Neutral: More information is needed to make a final decision.

    Provide a brief explanation for your recommendation.
    """

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a code review assistant."},
                {"role": "user", "content": prompt_template},
            ]
        )

        result = completion.choices[0].message.content.strip().lower()
        if "approve" in result:
            return True, "Approve"
        elif "request changes" in result:
            return False, "Request Changes"
        else:
            return None, "Neutral"

    except Exception as e:
        logger.error(f"Error during OpenAI API call: {str(e)}")
        raise

def approve_pull_request(repo: str, pr_number: int):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"
    headers = {
        'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",
        'Accept': 'application/vnd.github.v3+json',
    }
    payload = {}
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

def request_changes(repo: str, pr_number: int, message: str):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/requests"
    headers = {
        'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",
        'Accept': 'application/vnd.github.antiope-preview+json',
    }
    payload = {
        "title": "Request Changes",
        "body": message
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

if __name__ == "__main__":
    try:
        repo, pr_number, sha = get_pr_details()
        
        # Fetch PR diff
        diff = get_pr_diff()
        
        # Perform code review
        feedback = review_code_with_rag(diff)
        
        # Create initial check run
        check_id = create_check_run(repo, sha)

        # Update check run with results
        output = {
            "title": "AI Code Review Results",
            "summary": "Detailed analysis below.",
            "text": feedback
        }
        update_check_run(repo, check_id, "success", output)

        print(f"Using token: {os.getenv('PERSONAL_GITHUB_TOKEN')}[:10] + '...'")

        # Determine approval
        approval_result, reason = determine_approval(repo, pr_number, diff)
        if approval_result is True:
            approve_pull_request(repo, pr_number)
            print(f"Pull request approved. Reason: {reason}")
        elif approval_result is False:
            change_message = input(f"Based on the AI's recommendation, would you like to request changes? Enter a message: ")
            request_changes(repo, pr_number, change_message)
            print(f"Changes requested. Reason: {reason}")
        else:
            print(f"A neutral recommendation was made. Reason: {reason}")

        logger.info("GitHub Actions completed successfully.")
    except Exception as e:
        logger.error(f"Error during GitHub Actions: {str(e)}")
        raise
