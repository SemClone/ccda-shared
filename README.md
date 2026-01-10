# CCDA Shared Code

Shared utilities, models, constants, and database migrations for CCDA components.

## Overview

This repository contains common code shared between:
- `ccda-worker` - Background job processor
- `ccda-api` - REST API service

## Contents

- `constants.py` - System-wide constants and configuration
- `env.py` - Environment variable helpers
- `models.py` - Pydantic data models
- `storage.py` - DigitalOcean Spaces client
- `git_utils.py` - Git repository utilities
- `migrations/` - PostgreSQL database migrations

## Usage

This repository is included as a Git submodule in component repositories:

```bash
# In ccda-worker or ccda-api
git submodule add git@github.com:SemClone/ccda-shared.git shared
git submodule update --init --recursive
```

## Import Pattern

```python
# In Worker or API code
from shared.constants import SUPPORTED_ECOSYSTEMS
from shared.models import VulnerabilityModel
from shared.storage import SpacesClient
```

## License

Copyright (c) 2026 Oscar Valenzuela <oscar.valenzuela.b@gmail.com>  
All Rights Reserved.

This is proprietary software. Unauthorized copying or distribution is strictly prohibited.
