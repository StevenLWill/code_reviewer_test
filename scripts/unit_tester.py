import os
import openai
import re

# Set up OpenAI API key (assumed to be stored as an environment variable)
openai.api_key = os.getenv("OPEN_AI_KEY")

def get_python_files(repo_path):
    """Recursively get all Python files from the repository."""
    python_files = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py") and not root.endswith("tests"):  # Avoid scanning test folder
                python_files.append(os.path.join(root, file))
    return python_files

def read_file_content(file_path):
    """Read the content of a file."""
    with open(file_path, 'r') as f:
        return f.read()

def generate_unit_tests(file_content):
    """Generate unit test code using OpenAI's GPT model."""
    prompt = f"""
    You are a Python expert. Generate unit test cases for the following Python code:
    
    ```python
    {file_content}
    ```
    The unit tests should use the `unittest` framework and test all functions and methods.
    """
    
    response = openai.Completion.create(
        engine="text-davinci-003",  # Use a GPT-3 model
        prompt=prompt,
        max_tokens=1500,  # Limit the size of the generated response
        temperature=0.5  # Adjust the creativity
    )
    
    return response.choices[0].text

def write_unit_test_file(original_file_path, test_code, tests_folder):
    """Write the generated unit tests to a new file in the tests folder."""
    # Create a test file name based on the original file name
    original_file_name = os.path.basename(original_file_path)
    test_file_name = re.sub(r'\.py$', '_test.py', original_file_name)
    
    # Create the test file path in the tests folder
    test_file_path = os.path.join(tests_folder, test_file_name)
    
    with open(test_file_path, 'w') as f:
        f.write(test_code)

def process_repository(repo_path):
    """Scan the repo, generate unit tests, and write them to test files."""
    # Create a tests folder in the root of the repository if it doesn't exist
    tests_folder = os.path.join(repo_path, 'tests')
    os.makedirs(tests_folder, exist_ok=True)
    
    # Get all Python files in the repo (excluding the tests folder itself)
    python_files = get_python_files(repo_path)
    
    for python_file in python_files:
        print(f"Processing {python_file}...")
        file_content = read_file_content(python_file)
        
        # Skip empty files
        if not file_content.strip():
            continue
        
        # Generate unit tests using OpenAI
        test_code = generate_unit_tests(file_content)
        
        # Write the generated tests to a new file in the tests folder
        write_unit_test_file(python_file, test_code, tests_folder)

if __name__ == "__main__":
    # Automatically detect the repository path using GITHUB_WORKSPACE environment variable
    repo_path = os.getenv("GITHUB_WORKSPACE", ".")
    
    if os.path.exists(repo_path):
        process_repository(repo_path)
        print(f"Unit tests generated and stored in the 'tests' folder inside {repo_path}.")
    else:
        print("Invalid repository path.")
