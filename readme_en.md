# HonyGo System - Experimental Automation Tool

## Note

Unverified and unimplemented features in this project:
- OCR pool optimization and performance optimization (planned)
- Verification of simulation tasks under different DPI scaling scenarios
- Sorting issues with multiple simulated clicks
- Image similarity threshold verification and performance optimization (planned)
- Click animation optimization (planned)

## Project Overview

HonyGo System is an experimental automation tool developed with Python and PySide6, integrating OCR text recognition capabilities with intelligent region selection and automated operations. This system is designed specifically for personal learning and experimental purposes, providing a comprehensive platform for automation technology exploration.

## Core Features

- **Intelligent Region Selection**: Advanced screen region selection with OCR recognition
- **OCR Instance Pool**: Dynamic management of multiple OCR instances for improved processing efficiency
- **Automated Operations**: Intelligent mouse clicking based on OCR results
- **Real-time Monitoring**: System performance and OCR service status monitoring
- **Unified Logging**: Comprehensive logging with categorized storage
- **Offline Operation**: Complete offline functionality with local model support
- **Performance Optimization**: Advanced caching and resource management

## Technical Architecture

- **Frontend Interface**: PySide6 (Qt6 Python bindings)
- **OCR Engine**: EasyOCR with local model support
- **Image Processing**: OpenCV, Pillow
- **System Interaction**: PyAutoGUI, Pynput
- **Backend Services**: Flask (OCR pool service)
- **Performance Monitoring**: Real-time metrics and dashboard

## Project Structure

```
HonyGo/
├── src/
│   ├── config/                        # Configuration files
│   ├── core/                          # Core functionality modules
│   │   ├── ocr/                       # OCR-related modules
│   │   └── services/                  # Service modules
│   ├── ui/                            # User interface modules
│   └── data/
│       └── logs/                      # Log files
├── docs/                              # Project documentation
├── tests/                             # Test scripts
├── requirements.txt                   # Python dependencies
├── start_honygo.py                    # Project startup script
└── README.md                          # Project documentation
```

## Installation and Setup

### System Requirements

- Python 3.8 or higher
- Windows 10/11 (primary support)
- At least 4GB RAM (8GB recommended for OCR pool)
- 2GB available disk space for models

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Application

```bash
python start_honygo.py
```

### 3. OCR Pool Service

The OCR pool service starts automatically with the main application, listening on port 8900.

## User Guide

### Basic Operations

1. **Start Application**: Run the main program to open the control interface
2. **Region Selection**: Use the region selector to define screen monitoring areas
3. **OCR Recognition**: Perform text recognition on selected regions
4. **Automated Operations**: Configure and execute automated mouse operations

### OCR Pool Management

- **Instance Monitoring**: View active OCR instances and their status
- **Performance Metrics**: Monitor processing speed and resource usage
- **Dynamic Scaling**: Automatic scaling based on workload
- **Health Checks**: Regular service health monitoring

## Development and Testing

### Running Tests

```bash
# Basic functionality tests
cd tests
python test_basic.py

# OCR functionality tests
python test_ocr_basic.py
```

### Logging System

All logs are stored in categorized directories under `data/logs/`:

- `Application/` - Main application logs
- `OCR/` - OCR service and processing logs
- `System/` - System monitoring and performance logs
- `Error/` - Error and exception logs
- `Tests/` - Test execution logs
- `Performance/` - Performance metrics and monitoring
- `General/` - General system information

## Troubleshooting

### Common Issues

1. **OCR Service Connection Timeout**
   - Check if port 8900 is available
   - Verify OCR service is running
   - Review OCR service logs

2. **Model Loading Errors**
   - Ensure models exist in specified directory
   - Check model file integrity

3. **UI Response Issues**
   - Check system resource usage
   - Review application logs
   - Restart application if necessary

### Log Analysis

```bash
# View application logs
tail -f data/logs/Application/app_*.log

# View OCR service logs
tail -f data/logs/OCR/OCR_Pool_*.log

# View error logs
tail -f data/logs/Error/error_*.log
```

## Contributing

This is an experimental learning project. Contributions, suggestions, and feedback are welcome:

1. **Bug Reports**: Use detailed descriptions and include relevant logs
2. **Feature Requests**: Describe use cases and expected behavior
3. **Code Contributions**: Follow existing code standards and include tests
4. **Documentation**: Help improve documentation and examples

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author Information

@author: Mr.Rey Copyright © 2025

## Open Source Framework Acknowledgments

This project is built upon the following excellent open source frameworks and libraries. We express our sincere gratitude to all contributors:

### Core Frameworks
- **PySide6** (LGPL-3.0) - Qt6 Python bindings for modern GUI interfaces
- **EasyOCR** (Apache-2.0) - Powerful OCR text recognition engine
- **OpenCV** (Apache-2.0) - Computer vision and image processing library
- **PyTorch** (BSD-3-Clause) - Deep learning framework supporting OCR models
- **TensorFlow** (Apache-2.0) - Machine learning platform

### Image Processing
- **Pillow** (HPND) - Python image processing library
- **NumPy** (BSD-3-Clause) - Scientific computing foundation library

### System Interaction
- **PyAutoGUI** (BSD-3-Clause) - Automated GUI operations
- **psutil** (BSD-3-Clause) - System and process monitoring
- **pywin32** (PSF-2.0) - Windows API access
- **keyboard** (MIT) - Keyboard event handling
- **watchdog** (Apache-2.0) - File system monitoring

### Network and API
- **Flask** (BSD-3-Clause) - Lightweight web framework
- **Flask-CORS** (MIT) - Cross-origin resource sharing support
- **requests** (Apache-2.0) - HTTP library
- **urllib3** (MIT) - HTTP client

### System Monitoring
- **pynvml** (BSD-3-Clause) - NVIDIA GPU monitoring
- **GPUtil** (MIT) - GPU usage monitoring

### Utility Libraries
- **schedule** (MIT) - Task scheduling
- **jsonschema** (MIT) - JSON data validation
- **importlib-metadata** (Apache-2.0) - Package metadata access

### Development Tools
- **pytest** (MIT) - Testing framework
- **pytest-qt** (MIT) - Qt application testing support
- **PyYAML** (MIT) - YAML configuration file processing
- **torchvision** (BSD-3-Clause) - Computer vision tools
- **nvidia-ml-py** (BSD-3-Clause) - NVIDIA management library Python bindings

### License Compatibility Analysis

This project uses the MIT license and maintains good compatibility with all used open source frameworks:

- **Fully Compatible**: MIT, BSD-3-Clause, BSD-2-Clause, Apache-2.0, HPND, PSF-2.0 licenses
- **Compatible with Considerations**: LGPL-3.0 (PySide6) - Used as a dynamic link library, does not affect this project's MIT licensing

All dependency library licenses allow use in MIT projects, ensuring the project's open source compliance.

## Acknowledgments

Our sincere gratitude goes to all pioneers who have blazed trails in the technology field. As a beginner, it is by standing on your shoulders and drawing nourishment from the experiences and explorations of predecessors that I have been able to break through limitations in thinking and implement ideas into various functional modules in HonyGo System for learning and practice, giving the joy of technological exploration a vessel.

Special thanks to every user of HonyGo System. As an experimental system limited to personal learning purposes, its core value comes from your experiences and feedback.

Thanks to all contributors of the above open source projects. Without your selfless dedication, there would be no birth of HonyGo System.

Mr. Rey  
By HonyGo System Team (including AI Assistant)

---

