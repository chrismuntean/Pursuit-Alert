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
### Version: `v0.1.0-beta`

### Functionality
* Use live USB camera feed or choose to upload a video for testing
* Frame skip definitions in settings
* Displays what the computer vision models are seeing in the status dropdown
* Displays resource usage bars below the status dropdown
* Analysis page shows plate number, sighting count, first seen (date), last seen (date), risk score
* Risk score is calculated based on mean, median, and mode of the total sightings for all plates
* See media logs of the vehicles by selecting a plate on the Analysis page. It will return a page with dropdowns for each date & time the plate was seen along with a cropped image of the vehicle, cropped image of the plate, and a video of the vehicle driving by highlighted in red with the label "TARGET"
* Full log clearing on Analysis page

### Technical
* [Ultralytics YOLOv9c](https://docs.ultralytics.com/models/yolov9/) for vehicle detection
* [License Plate Recognition LHQOW Dataset](https://universe.roboflow.com/objects-in-the-wild/license-plate-recognition-lhqow) for plate area detection
* [EasyOCR english_g2](https://github.com/JaidedAI/EasyOCR) for plate string detection
