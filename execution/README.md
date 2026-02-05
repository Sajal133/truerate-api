# Execution Scripts (Layer 3)

This directory contains **deterministic Python scripts** that perform the actual work.

## Purpose
Execution scripts handle the **doing** - API calls, data processing, file operations, database interactions. They should be:

- **Reliable**: Consistent, deterministic behavior
- **Testable**: Can be tested independently
- **Fast**: Optimized for performance
- **Well-commented**: Clear documentation

## Guidelines

### Script Structure
Each script should:
1. Use environment variables from `.env`
2. Accept clear input parameters
3. Return predictable outputs
4. Handle errors gracefully
5. Log meaningful information

### Example Script Template

```python
#!/usr/bin/env python3
"""
Script Name: example_script.py
Purpose: Brief description of what this does
Inputs: List inputs
Outputs: List outputs
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main execution function"""
    try:
        # Your logic here
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Best Practices

1. **Use meaningful names**: `scrape_single_site.py` not `script1.py`
2. **Add docstrings**: Explain purpose, inputs, outputs
3. **Handle errors**: Try/except with meaningful messages
4. **Use logging**: Print progress and status
5. **Keep it focused**: One script = one responsibility
6. **Test thoroughly**: Verify before committing

## Dependencies

Install required packages:
```bash
pip install -r requirements.txt
```

## Testing

Test scripts individually before integrating:
```bash
python execution/script_name.py --test
```
