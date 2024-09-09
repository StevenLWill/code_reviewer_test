# Code Reviewer with OpenAI

This repository is a demo of how a code review system can be built using OpenAI's GPT models to automatically analyze code changes in a GitHub repository. The system provides feedback on code improvements, best practices, and potential issues every time a pull request is opened or updated.

## Features

- **Automated Code Reviews**: Uses OpenAI's GPT model (e.g., `gpt-3.5-turbo` or `gpt-4`) to automatically review code changes in pull requests.
- **Pull Request Integration**: Automatically triggered through GitHub Actions whenever a pull request is created or updated.
- **Detailed Feedback**: Provides insights into potential improvements, adherence to best practices, and any potential issues found in the code.

## How It Works

1. **GitHub Actions**: A GitHub Action is set up to trigger whenever a pull request is opened or synchronized.
2. **PR Diff Fetching**: The GitHub Action fetches the pull request changes (diff) using the GitHub API.
3. **OpenAI Model**: The diff is passed to an OpenAI model which analyzes the changes and generates feedback.
4. **Feedback**: The feedback is either displayed in the GitHub Actions log or as a comment on the pull request.

## Getting Started

### Prerequisites

- Python 3.x
- An OpenAI API key (you can get one by signing up at [OpenAI's website](https://platform.openai.com/))
- A GitHub repository where this demo is applied

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/stevenlwill/code_reviewer_test.git
   cd code_reviewer_test
