import openai
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import requests
import os
import json

# Setup OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Function to retrieve the PR diff
def get_pr_diff():
    # GitHub provides the event file containing the PR data
    event_path = os.getenv('GITHUB_EVENT_PATH')
    
    with open(event_path, 'r') as f:
        event_data = json.load(f)
    
    # Extract PR number from event data
    pr_number = event_data['pull_request']['number']
    repo = os.getenv('GITHUB_REPOSITORY')  # e.g., user/repo
    
    # Use the GitHub API to fetch the PR diff
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {
        'Authorization': f"Bearer {os.getenv('GITHUB_TOKEN')}",  # Ensure Bearer is used with the token
        'Accept': 'application/vnd.github.v3+json',
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        files = response.json()
        return '\n'.join([f['patch'] for f in files])  # The 'patch' contains the diff
    else:
        raise Exception(f"Failed to fetch PR diff: {response.status_code}, {response.text}")

# Retrieval-Augmented Generation (RAG) logic
def review_code_with_rag(diff):
    # Define prompt template
    prompt_template = PromptTemplate(
        input_variables=["diff"],
        template="""
        You are a code review AI that helps developers identify potential issues, best practices, 
        and improvements. Given the following code diff:
        {diff}
        Analyze it and provide detailed feedback, including suggestions for improvements and 
        adherence to best practices.
        """
    )
    
    # Using the ChatCompletion API instead of the deprecated Completion API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # You can also use "gpt-4" if you have access
        messages=[
            {"role": "system", "content": "You are a code review assistant."},
            {"role": "user", "content": prompt_template.format(diff=diff)},
        ]
    )
    
    # Extract and return the feedback from the response
    feedback = response['choices'][0]['message']['content']
    return feedback

# Main logic
if __name__ == "__main__":
    try:
        diff = get_pr_diff()
        feedback = review_code_with_rag(diff)
        print("AI Review Feedback:\n", feedback)
    except Exception as e:
        print(f"Error: {e}")
