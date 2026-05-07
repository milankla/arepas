# Contributing to Arepas

We welcome contributions to the Arepas project! This document provides guidelines for contributing to the codebase.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/arepas.git
   cd arepas
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🏗️ Development Setup

### Running Tests
```bash
# API demonstration
python scripts/demo_enhanced_api.py

# Main pipeline
python -m src.fine_tune
```

### Code Quality
- Follow PEP 8 style guidelines
- Use type hints throughout the codebase
- Write descriptive docstrings for all functions and classes
- Maintain the existing logging patterns

## 📋 Contribution Guidelines

### 🐛 Bug Reports
When reporting bugs, please include:
- Python version and operating system
- Complete error messages and stack traces
- Steps to reproduce the issue
- Sample data (if applicable and safe to share)

### ✨ Feature Requests
For new features:
- Describe the use case and motivation
- Provide detailed specifications
- Consider backward compatibility
- Discuss performance implications

### 🔧 Code Contributions

#### Pull Request Process
1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** following our coding standards
3. **Test thoroughly** using existing test scripts
4. **Update documentation** if needed
5. **Commit with clear messages**:
   ```bash
   git commit -m "feat: add new image processing feature"
   ```
6. **Push to your fork** and create a pull request

#### Commit Message Format
Use conventional commits format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `refactor:` for code refactoring
- `perf:` for performance improvements
- `test:` for test additions/changes

### 🏛️ Architecture Guidelines

The project follows enterprise-grade patterns:

#### Core Principles
- **Factory Pattern**: Use factories for object creation
- **Dependency Injection**: Inject dependencies rather than hard-coding
- **Type Safety**: Use type hints and validation
- **Error Handling**: Comprehensive error handling and logging
- **Performance**: Consider performance implications of changes

#### Module Structure
```
src/loader/          # Enterprise data loading system
├── config.py        # Configuration management
├── csv_parser.py    # CSV parsing with validation
├── data_loader.py   # Core loading interface
├── factory.py       # Factory patterns
├── image_index.py   # High-performance indexing
├── neighborhood_loader.py  # Multi-neighborhood support
├── results.py       # Structured result objects
└── validation.py    # Input validation
```

### 📊 Performance Considerations

When making changes:
- **Profile** memory usage for large datasets
- **Document** any performance trade-offs

### 🔍 Code Review Criteria

Pull requests will be reviewed for:
- **Functionality**: Does it work as intended?
- **Performance**: No significant performance regression
- **Code Quality**: Follows established patterns and standards
- **Documentation**: Adequate documentation and comments
- **Testing**: Adequate test coverage
- **Backward Compatibility**: Doesn't break existing functionality

## 📚 Documentation

### Code Documentation
- Use clear, descriptive variable and function names
- Write comprehensive docstrings with examples
- Document complex algorithms and business logic
- Keep README.md and docs/PROJECT_STRUCTURE.md updated

### Architecture Documentation
When adding new components:
- Update `docs/PROJECT_STRUCTURE.md` with architectural details
- Document design decisions and trade-offs
- Provide usage examples
- Update performance metrics if applicable

## 🤝 Community Guidelines

- Be respectful and constructive in discussions
- Help newcomers get started
- Share knowledge and best practices
- Report issues promptly and clearly

## 📞 Getting Help

- Create an issue for bugs or feature requests
- Use clear, descriptive titles
- Provide all relevant context and details
- Be patient and responsive to questions

## 🏆 Recognition

Contributors will be recognized in:
- README.md acknowledgments section
- Release notes for significant contributions
- Project documentation credits

Thank you for contributing to Arepas! 🎉
