import os
import subprocess
import pytest
import time

def test_repo_to_text():
    # Remove any existing snapshot files to avoid conflicts
    for file in os.listdir('.'):
        if file.startswith('repo-to-text_') and file.endswith('.txt'):
            os.remove(file)
    
    # Run the repo-to-text command
    result = subprocess.run(['repo-to-text'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Assert that the command ran without errors
    assert result.returncode == 0, f"Command failed with error: {result.stderr.decode('utf-8')}"
    
    # Check for the existence of the new snapshot file
    snapshot_files = [f for f in os.listdir('.') if f.startswith('repo-to-text_') and f.endswith('.txt')]
    assert len(snapshot_files) == 1, "No snapshot file created or multiple files created"
    
    # Verify that the snapshot file is not empty
    with open(snapshot_files[0], 'r') as f:
        content = f.read()
    assert len(content) > 0, "Snapshot file is empty"
    
    # Clean up the generated snapshot file
    os.remove(snapshot_files[0])

if __name__ == "__main__":
    pytest.main()
