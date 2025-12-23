# Scripts

This directory contains all executable scripts for setup, testing, and utilities.

## 📁 Files in This Directory

### `setup.sh`
**Initial project setup**
- Creates `.env` from template
- Checks Docker installation
- Starts all services
- Downloads LLM model
- Initializes database

**Usage:**
```bash
chmod +x scripts/setup.sh
scripts/setup.sh
```

### `run_tests.sh`
**Test runner**
- Runs pytest test suite
- Supports different test modes (unit, integration, fast)
- Generates coverage reports

**Usage:**
```bash
scripts/run_tests.sh              # Run all tests
scripts/run_tests.sh unit         # Unit tests only
scripts/run_tests.sh coverage     # With coverage report
```

### `test_api.sh`
**API testing script**
- Tests API endpoints
- Verifies health checks
- Runs sample analyses

**Usage:**
```bash
scripts/test_api.sh
```

### `examples/`
**Example scripts and usage demonstrations**
- Python usage examples
- Integration examples
- Sample workflows

---

## 🚀 Common Tasks

### **First Time Setup**
```bash
scripts/setup.sh
```

### **Running Tests**
```bash
scripts/run_tests.sh
```

### **Testing the API**
```bash
scripts/test_api.sh
```

### **Using Python API**
```bash
python scripts/examples/usage_example.py
```

---

## 📝 Adding New Scripts

When adding new scripts:
- ✅ Make them executable: `chmod +x scripts/your_script.sh`
- ✅ Add usage instructions in header comments
- ✅ Update this README
- ✅ Use absolute paths or run from project root

---

**All automation in one place! 🔧**
