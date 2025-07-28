#!/usr/bin/env python3
"""
Test runner that ensures complete GPG isolation.
"""

import os
import subprocess
import sys
import tempfile

def setup_isolated_gpg_environment():
    """Setup completely isolated GPG environment for testing."""
    
    # Kill any existing GPG agents
    try:
        subprocess.run(['pkill', '-f', 'gpg-agent'], stderr=subprocess.DEVNULL)
    except:
        pass
    
    # Set environment variables to disable GPG agent completely
    test_env = os.environ.copy()
    
    # Create a temporary GPG home for this test session
    temp_gnupg = tempfile.mkdtemp(prefix='test_gpg_')
    
    test_env.update({
        'GNUPGHOME': temp_gnupg,
        'GPG_AGENT_INFO': '',
        'GPG_TTY': '',
        'DISPLAY': '',  # Disable X11 passphrase prompts
        'PINENTRY_USER_DATA': 'USE_CURSES=0',  # Disable curses prompts
    })
    
    return test_env, temp_gnupg

def run_tests_isolated():
    """Run pytest with complete GPG isolation."""
    
    test_env, temp_gnupg = setup_isolated_gpg_environment()
    
    try:
        # Run pytest with isolated environment
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_app.py', '-v', '--tb=short'
        ], env=test_env)
        
        return result.returncode
        
    finally:
        # Cleanup temporary GPG directory
        import shutil
        try:
            shutil.rmtree(temp_gnupg)
        except:
            pass

if __name__ == '__main__':
    exit_code = run_tests_isolated()
    sys.exit(exit_code)
