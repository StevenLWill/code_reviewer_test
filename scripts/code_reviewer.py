import os
from openai import OpenAI
import json
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key=os.getenv('OPEN_AI_KEY')

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

    print('#####################')
    print(diff)
    print('#####################')

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


if __name__ == "__main__":
    # Fetch PR diff
    diff = get_pr_diff()
        
    # Perform code review
    feedback = review_code_with_rag(diff)
        
    print("AI Review Feedback:\n", feedback)
   
