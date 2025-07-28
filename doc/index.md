# GPG Webservice Documentation Index

Welcome to the GPG Webservice documentation! This index provides quick access to all project documentation organized by audience and use case.

## 📚 Documentation Overview

| Document | Audience | Purpose |
|----------|----------|---------|
| [README.md](../README.md) | All Users | Quick start guide and project overview |
| [API Reference](api_reference.md) | API Users | Complete endpoint documentation with examples |
| [Technical Overview](overview.md) | Developers | Architecture and implementation details |
| [Development Guide](development.md) | Contributors | Development setup and contribution guidelines |

## 🚀 Quick Start Paths

### For End Users
1. **Start Here**: [README.md](../README.md) - Get the service running quickly
2. **API Usage**: [API Reference](api_reference.md) - Learn how to use all endpoints
3. **Examples**: [API Reference - Usage Examples](api_reference.md#usage-examples) - Copy-paste code examples

### For Developers
1. **Architecture**: [Technical Overview](overview.md) - Understand the system design
2. **Setup**: [Development Guide](development.md) - Set up your development environment
3. **Contributing**: [Development Guide - Contributing](development.md#contributing-guidelines) - Submit your improvements

### For Security Reviewers
1. **Security Architecture**: [Technical Overview - Security](overview.md#security-architecture) - Review security design
2. **Threat Model**: [Technical Overview - Security Considerations](overview.md#security-considerations) - Understand security boundaries
3. **Production**: [Development Guide - Deployment](development.md#deployment-preparation) - Production security checklist

## 🔍 Documentation by Topic

### Authentication & Security
- [User Registration Process](api_reference.md#register-user) - How users sign up and get API keys
- [API Key Authentication](api_reference.md#authentication) - How authentication works
- [Security Architecture](overview.md#security-architecture) - Overall security design
- [GPG Key Protection](overview.md#key-protection-strategy) - How keys are secured

### Cryptographic Operations
- [File Signing](api_reference.md#sign-file) - How to sign files
- [Signature Verification](api_reference.md#verify-signature) - How to verify signatures
- [File Encryption](api_reference.md#encrypt-file) - How to encrypt files
- [File Decryption](api_reference.md#decrypt-file) - How to decrypt files
- [GPG Implementation](overview.md#utility-layer-utils) - Low-level GPG operations

### System Architecture
- [Database Design](overview.md#database-layer-models) - Data models and relationships
- [Service Layer](overview.md#service-layer-services) - Business logic organization
- [Docker Architecture](overview.md#docker-configuration) - Containerization strategy
- [Testing Strategy](overview.md#testing-strategy) - How testing is organized

### Development Workflows
- [Environment Setup](development.md#development-environment-setup) - Get started developing
- [Adding Features](development.md#adding-new-features) - How to add new functionality
- [Testing Guide](development.md#testing-strategy) - How to write and run tests
- [Code Standards](development.md#code-style-and-standards) - Style and quality guidelines

## 📖 Quick Reference

### Most Common Tasks

#### Getting Started
```bash
# Start the service
docker-compose up webservice

# Run tests
docker-compose run --rm test-runner pytest tests/ -v
```

#### Using the API
```bash
# Register a user
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret","email":"alice@example.com"}'

# Sign a file
curl -X POST http://localhost:5000/sign \
  -H "X-API-KEY: your_api_key" \
  -F "file=@document.txt" \
  -o document.txt.sig
```

#### Development
```bash
# Add and test a new feature
git checkout -b feature/my-feature
# ... make changes ...
docker-compose run --rm test-runner pytest tests/ -v
git commit -m "feat: Add new feature"
```

### Key Concepts

- **API Key Authentication**: All cryptographic operations use API keys, no passwords needed
- **GPG Passphrase Derivation**: Private keys use `SHA256(API_key)` as passphrase for consistency
- **Docker Isolation**: Complete GPG environment isolation prevents host system interference
- **Temporary Keyrings**: Each operation uses isolated temporary GPG directories
- **Automatic Key Generation**: RSA 3072-bit keys generated automatically during registration

### Architecture Highlights

- **Flask Application**: HTTP API with Blueprint-based route organization
- **SQLAlchemy Models**: User accounts, PGP keys, and challenge data
- **Service Layer**: Business logic separation from HTTP handling
- **Utility Functions**: Reusable cryptographic and GPG operations
- **Comprehensive Testing**: Integration and unit tests with Docker isolation

## 🛠️ Troubleshooting

### Common Issues

| Problem | Solution | Documentation |
|---------|----------|---------------|
| GPG prompts during testing | Use Docker environment | [Development Guide - Debugging](development.md#gpg-agent-problems) |
| Tests failing | Check Docker setup | [Development Guide - Testing](development.md#running-tests) |
| API authentication errors | Verify API key format | [API Reference - Authentication](api_reference.md#authentication) |
| Database issues | Reset and reinitialize | [Development Guide - Database Issues](development.md#database-issues) |

### Getting Help

1. **Check Documentation**: Search this documentation for your specific issue
2. **Review Examples**: Look at the code examples in the API reference
3. **Run Tests**: Use the test suite to verify your environment
4. **Check Logs**: Use `docker-compose logs` to see detailed error messages

## 📋 Documentation Status

### Completed Documentation
- ✅ Comprehensive README with quick start guide
- ✅ Complete API reference with examples and client code
- ✅ Technical architecture overview with security analysis
- ✅ Development guide with setup and contribution instructions
- ✅ Full code documentation with type hints and docstrings

### Documentation Standards
- All classes and functions have comprehensive docstrings
- Type hints used throughout the codebase
- Examples provided for all API endpoints
- Security considerations documented
- Development workflows clearly explained

### Maintenance
This documentation is maintained alongside the codebase. When making changes:

1. Update relevant documentation sections
2. Add examples for new features
3. Update API reference for endpoint changes
4. Review security implications
5. Test all documentation examples

---

**Last Updated**: {{ current_date }}  
**Documentation Version**: 1.0  
**Project Version**: Latest

For questions about this documentation or suggestions for improvements, please check the [Development Guide contribution section](development.md#contributing-guidelines).
