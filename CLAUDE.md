# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a remote control system for GTNH-AE2 (GregTech: New Horizons - Applied Energistics 2) based on OpenComputers. The system consists of three main components:

- **Server**: Python FastAPI backend that handles communication with OC clients
- **Client**: Lua-based OpenComputers client that runs in-game
- **Website**: Vue.js frontend for web interface

## Common Commands

### Server Development
```bash
cd server
pip install -r requirements.txt
python run.py --port 8080
```

### Frontend Development
```bash
cd website
npm install
npm run dev          # Development server on port 80
npm run build        # Production build
```

### Docker Deployment
```bash
docker-compose up -d    # Start all services
docker-compose logs -f   # View logs
docker-compose down     # Stop services
```

## Architecture

### Server (`server/`)
- **FastAPI backend** with task management, automation, and trigger systems
- **Configuration**: Main settings in `config.py` including task definitions, triggers, and automation workflows
- **Core modules**:
  - `app/task.py` - Task execution and management
  - `app/automate.py` - Automation workflows
  - `app/info.py` - System information endpoints
  - `utils/task.py` - Task manager with caching and chunked uploads
  - `utils/trigger.py` - Trigger system for conditional actions
  - `utils/scheduler.py` - Scheduled task execution

### Client (`client/`)
- **Lua-based OpenComputers client** that connects to in-game AE2 systems
- **Core files**:
  - `run.lua` - Main client entry point with polling loop
  - `env.lua` - Configuration (server URL, tokens, AE2 address)
  - `src/executor.lua` - Command execution and result processing
  - `plugins/ae.lua` - AE2 integration plugin
- **Optional plugins** in `optional_plugins/monitor/` for extended functionality

### Website (`website/`)
- **Vue.js 3** frontend with Element Plus UI components
- **Key features**:
  - Real-time AE2 network monitoring
  - Item/fluid management and crafting
  - CPU status monitoring
  - Task automation interface
  - Mobile-responsive design with dark mode
- **Build configuration**: Vite with compression and chunk splitting

## Key Configuration Files

### Server Configuration
- `server/config.py` - Main configuration with task definitions, triggers, and automation
- `server/.env` - Environment variables (SERVER_TOKEN, etc.)
- `server/requirements.txt` - Python dependencies

### Client Configuration
- `client/env.lua` - Client settings (server URL, AE2 address, polling interval)
- Requires OpenComputers with T3 CPU, internet card, and ME interface/controller

### Frontend Configuration
- `website/vite.config.js` - Build configuration with compression and chunking
- `website/package.json` - Dependencies and build scripts

## Development Notes

### Task System
- Tasks are defined in `server/config.py` with caching and chunked upload support
- Large datasets (like item lists) use chunked uploads to avoid memory issues
- Task results can be cached to reduce OC client load

### Trigger System
- Conditional triggers can execute actions based on CPU status or other conditions
- Supports notification actions (HTTP requests) and crafting operations
- Template system for common trigger patterns

### AE2 Integration
- Client connects to ME interface/controller via adapter block
- Supports monitoring of items, fluids, CPUs, and storage components
- Optional monitor plugin for capacitor and storage element monitoring

### Multi-client Support
- System supports multiple OC clients with unique client IDs
- Tasks can be assigned to specific clients or broadcast to all
- Configuration allows for distributed AE2 network monitoring

## Security
- Server token authentication prevents unauthorized access
- Client-server communication uses token-based authentication
- Environment variables store sensitive configuration

## Deployment
- Docker Compose setup for easy deployment
- Frontend can be deployed as static files (Nginx/Apache)
- Backend runs as FastAPI application with Uvicorn
- Supports both development and production configurations