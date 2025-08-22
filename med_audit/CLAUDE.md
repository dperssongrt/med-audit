# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a containerized Python application for auditing "My Eye Dr" telephone systems. It performs automated web scraping to check call forwarding configurations for telephone numbers, running weekly as a scheduled job. The application uses Selenium WebDriver to interact with the CommPortal web interface, retrieving passwords via SOAP calls to a MetaView server.

## Architecture

### Core Components

- **main.py**: Entry point and main audit logic. Contains `MyEyeDrAudit` class that inherits from `SeleniumInterfaceBase`
- **SeleniumInterface.py**: Base class providing Firefox WebDriver configuration and lifecycle management
- **soap.py**: SOAP client for retrieving EAS (Enhanced Authentication Service) credentials from MetaView server
- **sendresults.py**: Email functionality to send audit results as CSV attachments

### Data Flow

1. Load telephone numbers from `tns.txt`
2. For each TN: Query EAS for password → Login to CommPortal → Check forwarding status → Record results
3. Write results to `results.csv` 
4. Email results to stakeholders

### Key Technical Details

- **Browser**: Firefox in headless mode with specific performance optimizations
- **Call Handlers**: Supports both BCM (business) and ICM profiles with different UI element IDs
- **Authentication**: Uses EAS passwords retrieved via SOAP for CommPortal login
- **Environment Detection**: Chooses appropriate geckodriver binary based on `TED_ENV` variable

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r app/requirements.txt

# Run audit locally (requires environment variables)
cd app && python main.py
```

### Docker Operations
```bash
# Build container
docker build -t med_audit .

# Tag for artifact registry
docker tag med_audit us-east4-docker.pkg.dev/rugged-night-193017/scheduled-jobs/med_audit:latest

# Push to registry
docker push us-east4-docker.pkg.dev/rugged-night-193017/scheduled-jobs/med_audit:latest
```

## Required Environment Variables

The application requires these environment variables for SOAP authentication:
- `MVS_SOAP_HOST`: MetaView SOAP server hostname
- `MVS_SOAP_URL`: MetaView SOAP endpoint URL  
- `MVS_SOAP_USERNAME`: SOAP authentication username
- `MVS_SOAP_PASSWORD`: SOAP authentication password
- `TED_ENV`: Environment identifier (affects geckodriver selection)

## File Structure Notes

- **geckodriver variants**: Three binaries for different platforms (Linux, Mac M1, standard Mac)
- **tns.txt**: Input file containing telephone numbers to audit (one per line)
- **results.csv**: Output file with TN and status columns
- **test.json**: Test data file (purpose unclear from structure)

## Email Configuration

Results are automatically emailed to `fpike@granitenet.com` with CC to the engineering team. Email uses internal SMTP server at `172.85.228.6:25` with no authentication required.