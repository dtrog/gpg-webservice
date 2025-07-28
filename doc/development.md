# GPG Webservice - Development Guide

This guide provides comprehensive information for developers working on the GPG Webservice project, including setup instructions, development workflows, testing procedures, and contribution guidelines.

## Development Environment Setup

### Prerequisites

- **Docker & Docker Compose**: For containerized development and testing
- **Python 3.11+**: For local development
- **Git**: For version control
- **Optional**: VS Code with Python extension for enhanced development experience

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd gpg-webservice

# Start development environment
docker-compose up webservice

# In another terminal, run tests
docker-compose run --rm test-runner pytest tests/ -v
```

### Local Development Setup

For development without Docker:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install additional development dependencies
pip install pytest pytest-cov black flake8 mypy

# Set up pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Environment Configuration

Create a `.env` file for local development:

```bash
# Database configuration
DATABASE_URL=sqlite:///gpg_users.db

# Flask configuration
FLASK_ENV=development
FLASK_DEBUG=1

# GPG isolation (important for testing)
GPG_AGENT_INFO=""
DISPLAY=""
GPG_TTY=""
```

## Project Structure Deep Dive

```
gpg-webservice/
├── app.py                    # Flask application entry point
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container configuration
├── docker-compose.yml       # Multi-service orchestration
├── .dockerignore            # Docker build context exclusions
├── .gitignore              # Git exclusions
│
├── models/                  # Database models (SQLAlchemy)
│   ├── __init__.py         # Models package initialization
│   ├── user.py             # User account model
│   ├── pgp_key.py          # PGP key storage model
│   ├── challenge.py        # Challenge-response model
│   └── apikey.py           # (Currently unused)
│
├── services/               # Business logic layer
│   ├── __init__.py        # Services package initialization
│   ├── user_service.py    # User management operations
│   ├── auth_service.py    # Authentication utilities
│   ├── challenge_service.py # Challenge-response logic
│   └── gpg_service.py     # (Future GPG service abstraction)
│
├── routes/                 # HTTP endpoint handlers
│   ├── __init__.py        # Routes package initialization
│   ├── user_routes.py     # User registration/login endpoints
│   └── gpg_routes.py      # Cryptographic operation endpoints
│
├── utils/                  # Utility functions
│   ├── __init__.py        # Utils package initialization
│   ├── crypto_utils.py    # Cryptographic utilities
│   ├── gpg_utils.py       # GPG key generation
│   └── gpg_file_utils.py  # GPG file operations
│
├── db/                     # Database configuration
│   ├── __init__.py        # Database package initialization
│   └── database.py        # SQLAlchemy setup and session management
│
├── tests/                  # Test suite
│   ├── __init__.py        # Tests package initialization
│   ├── test_app.py        # Integration tests for HTTP endpoints
│   ├── test_models.py     # Database model tests
│   ├── test_services.py   # Business logic tests
│   ├── test_utils.py      # Utility function tests
│   └── fixtures/          # Test data and GPG keys
│       ├── __init__.py    # Test fixtures package
│       ├── alice_*.asc    # Alice's test keys
│       └── bob_*.asc      # Bob's test keys
│
└── doc/                    # Documentation
    ├── overview.md         # Technical architecture overview
    ├── api_reference.md    # Complete API documentation
    └── development.md      # This file
```

## Development Workflows

### Adding New Features

1. **Feature Branch Creation**
   ```bash
   git checkout -b feature/new-feature-name
   ```

2. **Development Process**
   - Write tests first (TDD approach recommended)
   - Implement the feature
   - Update documentation
   - Run full test suite

3. **Code Quality Checks**
   ```bash
   # Run linting
   flake8 --max-line-length=100 .
   
   # Type checking
   mypy --ignore-missing-imports .
   
   # Code formatting
   black --line-length=100 .
   ```

4. **Testing**
   ```bash
   # Run all tests
   docker-compose run --rm test-runner pytest tests/ -v
   
   # Run with coverage
   docker-compose run --rm test-runner pytest tests/ --cov=. --cov-report=html
   
   # Run specific test categories
   docker-compose run --rm test-runner pytest tests/test_models.py -v
   ```

### Database Migrations

For database schema changes:

1. **Modify Models**
   - Update SQLAlchemy models in `models/`
   - Add appropriate type hints and documentation

2. **Create Migration Script**
   ```python
   # Example migration script
   from db.database import db
   
   def upgrade():
       # Add new columns, tables, etc.
       db.engine.execute('ALTER TABLE users ADD COLUMN new_field VARCHAR(255)')
   
   def downgrade():
       # Rollback changes
       db.engine.execute('ALTER TABLE users DROP COLUMN new_field')
   ```

3. **Test Migration**
   ```bash
   # Test with fresh database
   docker-compose run --rm test-runner python -c "from app import init_db; init_db()"
   ```

### Adding New Endpoints

1. **Define Route Handler**
   ```python
   # In routes/gpg_routes.py or routes/user_routes.py
   @gpg_bp.route('/new-endpoint', methods=['POST'])
   @require_api_key
   def new_endpoint(user):
       """
       Brief description of endpoint functionality.
       
       Args:
           user: Authenticated user object from decorator
           
       Returns:
           JSON response with operation result
       """
       # Implementation here
       return jsonify({'result': 'success'}), 200
   ```

2. **Add Service Logic**
   ```python
   # In appropriate service class
   def new_operation(self, user_id: int, data: str) -> Tuple[bool, str]:
       """
       Perform the new operation.
       
       Args:
           user_id: ID of the user requesting the operation
           data: Input data for the operation
           
       Returns:
           Tuple of (success, message/result)
       """
       # Business logic implementation
       return True, "Operation completed successfully"
   ```

3. **Write Tests**
   ```python
   # In tests/test_app.py
   def test_new_endpoint(client):
       """Test the new endpoint functionality."""
       api_key, _ = register_user(client, 'testuser', 'password')
       
       response = client.post('/new-endpoint', 
                            json={'data': 'test'},
                            headers={'X-API-KEY': api_key})
       
       assert response.status_code == 200
       assert response.get_json()['result'] == 'success'
   ```

4. **Update Documentation**
   - Add endpoint to `doc/api_reference.md`
   - Update README.md if necessary
   - Add docstrings with proper type hints

## Testing Strategy

### Test Organization

The project uses pytest with the following test categories:

- **Integration Tests** (`test_app.py`): End-to-end HTTP endpoint testing
- **Unit Tests** (`test_models.py`, `test_services.py`, `test_utils.py`): Component-level testing
- **Fixture Tests**: GPG key and data fixture validation

### Writing Effective Tests

#### Test Structure
```python
def test_feature_name():
    """
    Test description explaining what is being tested and why.
    
    This test verifies that [specific behavior] works correctly
    when [specific conditions] are met.
    """
    # Arrange: Set up test data and conditions
    api_key, _ = register_user(client, 'testuser', 'password')
    test_data = {'key': 'value'}
    
    # Act: Perform the action being tested
    response = client.post('/endpoint', 
                          json=test_data,
                          headers={'X-API-KEY': api_key})
    
    # Assert: Verify the results
    assert response.status_code == 200
    result = response.get_json()
    assert result['expected_field'] == 'expected_value'
```

#### Test Isolation
- Each test uses fresh database state
- GPG operations use temporary directories
- No shared state between tests
- Docker provides complete environment isolation

#### Test Coverage Goals
- **Models**: 90%+ coverage for all database operations
- **Services**: 85%+ coverage for business logic
- **Routes**: 80%+ coverage for HTTP endpoints
- **Utils**: 95%+ coverage for utility functions

### Running Tests

```bash
# Full test suite
docker-compose run --rm test-runner pytest tests/ -v

# Specific test file
docker-compose run --rm test-runner pytest tests/test_models.py -v

# Specific test function
docker-compose run --rm test-runner pytest tests/test_app.py::test_register -v

# With coverage report
docker-compose run --rm test-runner pytest tests/ --cov=. --cov-report=html

# Parallel execution (faster)
docker-compose run --rm test-runner pytest tests/ -n auto

# Stop on first failure
docker-compose run --rm test-runner pytest tests/ -x
```

## Code Style and Standards

### Python Style Guide

The project follows PEP 8 with these modifications:

- **Line Length**: 100 characters (not 79)
- **String Quotes**: Prefer double quotes for consistency
- **Import Organization**: Use isort for automatic import sorting

### Type Hints

All new code should include comprehensive type hints:

```python
from typing import Optional, Tuple, List, Dict, Union

def example_function(
    user_id: int, 
    data: Optional[str] = None,
    options: Dict[str, Any] = None
) -> Tuple[bool, str]:
    """
    Example function with proper type hints.
    
    Args:
        user_id: The user's database ID
        data: Optional data string
        options: Configuration options dictionary
        
    Returns:
        Tuple of (success_flag, result_message)
    """
    if options is None:
        options = {}
    
    # Implementation here
    return True, "Success"
```

### Documentation Standards

#### Docstring Format
```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief one-line description of function purpose.
    
    More detailed description of what the function does, how it works,
    and any important considerations or side effects.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Description of return value and its format
        
    Raises:
        SpecificException: Description of when this exception is raised
        AnotherException: Description of when this other exception is raised
        
    Example:
        >>> result = function_name("example", 42)
        >>> print(result)
        "Expected output"
    """
```

#### Class Documentation
```python
class ExampleClass:
    """
    Brief description of class purpose and functionality.
    
    Detailed description of what this class does, how it fits into
    the overall system, and any important usage considerations.
    
    Attributes:
        attribute1 (type): Description of first attribute
        attribute2 (type): Description of second attribute
        
    Example:
        >>> instance = ExampleClass("param")
        >>> result = instance.method()
        >>> print(result)
        "Expected output"
    """
```

## Debugging and Troubleshooting

### Common Development Issues

#### GPG Agent Problems
If you encounter GPG agent prompts during development:

```bash
# Kill existing GPG agents
pkill -f gpg-agent

# Set isolation environment variables
export GPG_AGENT_INFO=""
export DISPLAY=""
export GPG_TTY=""

# Use Docker for complete isolation
docker-compose run --rm test-runner pytest tests/test_app.py::test_sign -v
```

#### Database Issues
For database-related problems:

```bash
# Reset database
rm -f gpg_users.db
python -c "from app import init_db; init_db()"

# Check database schema
sqlite3 gpg_users.db ".schema"

# Inspect database contents
sqlite3 gpg_users.db "SELECT * FROM users;"
```

#### Docker Issues
For container-related problems:

```bash
# Rebuild containers
docker-compose build --no-cache

# Clean up containers and volumes
docker-compose down -v
docker system prune -f

# Check container logs
docker-compose logs webservice
docker-compose logs test-runner
```

### Debugging Techniques

#### Using Python Debugger
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use the newer breakpoint() function (Python 3.7+)
breakpoint()
```

#### Logging Setup
```python
import logging

# Configure logging for development
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use in code
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error message")
```

#### Testing Individual Components
```python
# Test GPG operations directly
from utils.gpg_utils import generate_gpg_keypair
from utils.crypto_utils import generate_api_key
import hashlib

api_key = generate_api_key()
passphrase = hashlib.sha256(api_key.encode()).hexdigest()
pub_key, priv_key = generate_gpg_keypair("test", "test@example.com", passphrase)

print(f"API Key: {api_key}")
print(f"Passphrase: {passphrase}")
print(f"Public Key Length: {len(pub_key)}")
print(f"Private Key Length: {len(priv_key)}")
```

## Performance Optimization

### Profiling

Use Python profiling tools to identify performance bottlenecks:

```python
import cProfile
import pstats

# Profile a specific function
def profile_function():
    # Your function code here
    pass

# Run profiler
cProfile.run('profile_function()', 'profile_stats')

# Analyze results
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(10)
```

### Database Optimization

- Use appropriate indexes for frequently queried columns
- Consider connection pooling for high-load scenarios
- Monitor query performance with SQLAlchemy logging

### GPG Operation Optimization

- Reuse temporary directories when safe
- Cache public keys for repeated operations
- Consider async processing for large files

## Security Considerations for Development

### Secure Development Practices

1. **Never Commit Secrets**
   - Use environment variables for sensitive data
   - Add secrets to `.gitignore`
   - Use `.env.example` for configuration templates

2. **Input Validation**
   - Validate all user inputs
   - Sanitize file uploads
   - Use parameterized queries for database operations

3. **Error Handling**
   - Don't expose sensitive information in error messages
   - Log security events appropriately
   - Use generic error messages for client responses

### Security Testing

```python
# Example security test
def test_api_key_required():
    """Test that endpoints require valid API key."""
    response = client.post('/sign', data={'file': ('test.txt', b'content')})
    assert response.status_code == 401
    assert response.get_json()['error'] == 'API key required'

def test_invalid_api_key():
    """Test that invalid API keys are rejected."""
    response = client.post('/sign', 
                          data={'file': ('test.txt', b'content')},
                          headers={'X-API-KEY': 'invalid_key'})
    assert response.status_code == 403
    assert response.get_json()['error'] == 'Invalid or inactive API key'
```

## Deployment Preparation

### Production Checklist

- [ ] Update security configurations (stronger password hashing)
- [ ] Configure production database (PostgreSQL recommended)
- [ ] Set up proper logging and monitoring
- [ ] Implement rate limiting
- [ ] Configure SSL/TLS termination
- [ ] Set up backup procedures for user keys
- [ ] Review and harden Docker configuration
- [ ] Implement proper secret management

### Environment-Specific Configurations

Create separate configuration files for different environments:

```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'development-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///gpg_users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # Production-specific settings
```

## Contributing Guidelines

### Pull Request Process

1. **Fork and Branch**
   ```bash
   git fork <repository-url>
   git checkout -b feature/your-feature-name
   ```

2. **Development**
   - Follow code style guidelines
   - Write comprehensive tests
   - Update documentation
   - Ensure all tests pass

3. **Commit Messages**
   ```
   feat: Add new GPG key rotation endpoint
   
   - Implement key rotation service logic
   - Add endpoint for key rotation requests
   - Include comprehensive tests for rotation flow
   - Update API documentation
   
   Closes #123
   ```

4. **Pull Request**
   - Provide clear description of changes
   - Reference related issues
   - Include testing instructions
   - Ensure CI passes

### Code Review Guidelines

#### For Reviewers
- Check code style and documentation
- Verify test coverage
- Test functionality manually
- Review security implications
- Ensure backward compatibility

#### For Authors
- Respond to feedback promptly
- Make requested changes
- Keep pull requests focused and small
- Provide context for design decisions

This development guide provides the foundation for effective contribution to the GPG Webservice project. For additional questions or clarifications, please refer to the existing codebase or reach out to the development team.
