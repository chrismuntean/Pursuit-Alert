# Pursuit Alert
### Counter surveillance system that detects vehicles that may be following you using ALPR. Designed simply with open source projects.

## Installation
First grab my repo
`git clone https://github.com/chrismuntean/Pursuit-Alert.git`

### Python virtual environment installation
1. `chmod +x venv-run.sh`
2. `./venv-run.sh`

**IMPORTANT**: Please ensure that all requirements are fully installed before interrupting the installation process. If the installation does not complete successfully, you may need to remove the `pursuit-alert-venv` directory and execute `./venv-run.sh` again to reinstall the requirements.

### Docker installation
1. `docker pull chrismuntean/pursuit-alert`
2. `docker compose up`

## Features
### Current version: `v0.1.0-beta`

### Functionality Overview
- **Video Input Options**: Utilize a live USB camera feed or upload a pre-recorded video for analysis.
- **Frame Skipping**: Define frame skip settings to optimize processing.
- **Visual Feedback**: 
  - The status dropdown displays outputs from the computer vision models.
  - Resource usage is shown through bars located below the status dropdown.
- **Analysis Tools**:
  - Displays vehicle details such as plate number, sighting count, first and last sighting dates, and a calculated risk score.
  - Risk score calculation is based on the mean, median, and mode of total sightings across all observed plates.
  - Media logs for each vehicle can be accessed by selecting a plate on the Analysis page, featuring dropdowns for each sighting date and time, along with a cropped image of the vehicle and plate, and a video highlighting the vehicle in red labeled as "TARGET".
- **Data Management**: Offers an option to clear all logs on the Analysis page for privacy and system performance.

### Technical Specifications
- **Vehicle Detection**: Utilizes [Ultralytics YOLOv9c](https://docs.ultralytics.com/models/yolov9/), a state-of-the-art model for accurate vehicle detection.
- **Plate Area Detection**: Employs the [License Plate Recognition LHQOW Dataset](https://universe.roboflow.com/objects-in-the-wild/license-plate-recognition-lhqow) to locate license plates within the video frames.
- **Plate Recognition**: Implements [EasyOCR english_g2](https://github.com/JaidedAI/EasyOCR) for extracting alphanumeric characters from license plates, enabling detailed plate string detection.