import os
import cv2
import time
from PIL import Image
import numpy as np
from ultralytics import YOLO
import easyocr
from collections import Counter
import json

# delete the log folder if it exists and create a new one (or if it doesn't exist)
if os.path.exists("logs"):
    os.system("rm -rf logs")
    os.makedirs("logs")
else:
    os.makedirs("logs")

# delete the frames folder if it exists and create a new one (or if it doesn't exist)
if os.path.exists("frames"):
    os.system("rm -rf frames")
    os.makedirs("frames")
else:
    os.makedirs("frames")

# iniitialize models
car_detector = YOLO('models/yolov8n.pt') # object detection
plate_detector = YOLO('models/license_plate.pt') # object detection
character_detector = easyocr.Reader(['en']) # optical character recognition

# temporal redundancy voting function
def temporal_redundancy_voting(plates):
    
    # Extracting plate strings
    plate_strings = [plate['plate'] for plate in plates]

    # Determine the maximum length of the plates
    max_length = max(len(plate) for plate in plate_strings)

    # Initialize a list to hold the voted characters for each position
    voted_characters = []

    # Iterate through each position
    for i in range(max_length):
        char_counter = Counter()

        # Count characters at the current position for each plate and count blanks
        num_blanks = 0
        for plate in plate_strings:
            if i < len(plate):
                char_counter[plate[i]] += 1
            else:
                num_blanks += 1

        # If blanks are the majority, stop adding more characters
        if num_blanks > len(plate_strings) / 2:
            break

        # Find the most common character for this position
        most_common_char, _ = char_counter.most_common(1)[0]
        voted_characters.append(most_common_char)

    # Join the characters to form the final voted plate
    voted_plate = ''.join(voted_characters)
    return voted_plate

# perm log function
def create_perm_log(car_id, vid, fps):
    
    # Load plate strings and vehicle tracking data from JSON files if they exist
    with open(f"logs/tmp/Vehicle_{car_id}/plates.json", "r") as file:
        plate_strings = json.load(file)
    
    if os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/vehicle_track.json"):
        with open(f"logs/tmp/Vehicle_{car_id}/vehicle_track.json", "r") as file:
            vehicle_data = json.load(file)
            vehicle_data_found = True
    else:
        vehicle_data_found = False
    
    if os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/plate_track.json"):
        with open(f"logs/tmp/Vehicle_{car_id}/plate_track.json", "r") as file:
            plate_track_data = json.load(file)
            plate_data_found = True
    else:
        plate_data_found = False
        
    # Apply the temporal redundancy voting algorithm
    voted_plate = temporal_redundancy_voting(plate_strings['plates'])

    # Create permanent log directory
    perm_path = f"logs/perm/{voted_plate}"
    if not os.path.exists(perm_path):
        os.makedirs(perm_path)

    # Determine the correct directory name with counter
    count = 1
    while os.path.exists(f"{perm_path}/seen_{count}"):
        count += 1
    seen_path = f"{perm_path}/seen_{count}"
    os.makedirs(seen_path)

    # Get frame size for the video
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Create video writer object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(f"{seen_path}/video.mp4", fourcc, fps, (width, height))

    # Restructure vehicle and plate tracking data
    if (vehicle_data_found):
        vehicle_frames_dict = {int(d['frame']): d for d in vehicle_data['frames']}

    if (plate_data_found):
        plate_frames_dict = {int(d['frame']): d for d in plate_track_data['frames']}

    # Process each frame and save one cropped image
    frame_dir = f"logs/tmp/Vehicle_{car_id}/frames"
    frame_numbers = sorted([int(frame.split('.')[0]) for frame in os.listdir(frame_dir) if frame.endswith('.jpg')])
    cropped_vehicle_saved = False
    cropped_plate_saved = False

    for frame_num in frame_numbers:
        img_path = f"{frame_dir}/{frame_num}.jpg"
        if os.path.exists(img_path):
            img = cv2.imread(img_path)

            # Retrieve vehicle frame data and draw bounding box
            if (vehicle_data_found):
                vehicle_frame_data = vehicle_frames_dict.get(frame_num)
                if vehicle_frame_data:
                    vx1, vy1, vx2, vy2 = map(int, [vehicle_frame_data['x1'], vehicle_frame_data['y1'], vehicle_frame_data['x2'], vehicle_frame_data['y2']])
                    cv2.rectangle(img, (vx1, vy1), (vx2, vy2), (0, 0, 255), 2)
                    cv2.putText(img, "Target Vehicle", (vx1, vy1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)

                    # Crop and save one image of the vehicle and plate
                    if not cropped_vehicle_saved:
                        cropped_vehicle = img[vy1:vy2, vx1:vx2]
                        cv2.imwrite(f"{seen_path}/cropped_vehicle.jpg", cropped_vehicle)
                        cropped_vehicle_saved = True

            # Retrieve plate frame data, adjust to vehicle coordinates, and draw cornered bounding box
            if (plate_data_found):
                plate_frame_data = plate_frames_dict.get(frame_num)
                if plate_frame_data and vehicle_frame_data:
                    px1, py1, px2, py2 = map(int, [plate_frame_data['x1'], plate_frame_data['y1'], plate_frame_data['x2'], plate_frame_data['y2']])

                    # Adjust plate coordinates to vehicle coordinates
                    px1 += vx1
                    py1 += vy1
                    px2 += vx1
                    py2 += vy1

                    # Draw cornered bounding box for the plate
                    # Top left corner
                    cv2.line(img, (px1, py1), (px1, py1 + 20), (255, 255, 255), 4)
                    cv2.line(img, (px1, py1), (px1 + 20, py1), (255, 255, 255), 4)
                    # Top right corner
                    cv2.line(img, (px2, py1), (px2, py1 + 20), (255, 255, 255), 4)
                    cv2.line(img, (px2, py1), (px2 - 20, py1), (255, 255, 255), 4)
                    # Bottom left corner
                    cv2.line(img, (px1, py2), (px1, py2 - 20), (255, 255, 255), 4)
                    cv2.line(img, (px1, py2), (px1 + 20, py2), (255, 255, 255), 4)
                    # Bottom right corner
                    cv2.line(img, (px2, py2), (px2, py2 - 20), (255, 255, 255), 4)
                    cv2.line(img, (px2, py2), (px2 - 20, py2), (255, 255, 255), 4)

                    # Add the voted plate string to the plate area label
                    cv2.putText(img, voted_plate, (px1, py1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)

                    # Crop and save one image of the plate
                    if not cropped_plate_saved:
                        cropped_plate = img[py1:py2, px1:px2]
                        cv2.imwrite(f"{seen_path}/cropped_plate.jpg", cropped_plate)
                        cropped_plate_saved = True

            # Write the frame to the video
            out.write(img)

    out.release()

    # delete the tmp folder for the vehicle 
    os.system("rm -rf logs/tmp/Vehicle_" + str(car_id))

############################
### DO NOT EDIT ABOVE THIS LINE ###
#### CONFIGURATION  VARIABLES ####

# get the video file path
vid_path = 'test_files/test_vids/test_vid_7_(4k).mov'
# vid_path = 0 # for webcam

frame_skip = 10 # maxes out at the fps of original video/ camera stream
# frame_skip = 0 # no frame skipping

#### CONFIGURATION  VARIABLES ####
### DO NOT EDIT BELOW THIS LINE ###
############################

# create a video capture object
vid = cv2.VideoCapture(vid_path)

############################

# calculate the coresponding re-write fps based on the frame_skip and the original video fps
orig_fps = vid.get(cv2.CAP_PROP_FPS)
if frame_skip == 0:
    write_fps = orig_fps
else:
    write_fps = orig_fps / frame_skip

print("Original FPS: " + str(orig_fps))
print("Frame Skip: " + str(frame_skip))
print("Write FPS: " + str(write_fps))

############################

# get the frame size
frame_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define the codec and create VideoWriter object to save the video to /logs/output.mp4
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('logs/output.mp4', fourcc, write_fps, (frame_width, frame_height))

# create a empty list to hold the target vehicles that have plate detections
target_vehicles = []

############################
###### MAIN ALPR LOOP ######
############################
# create a loop to go through every frame
while True:

    # read every video at the set frame rate
    vid.set(cv2.CAP_PROP_POS_FRAMES, vid.get(cv2.CAP_PROP_POS_FRAMES) + frame_skip)

    # get the frame
    ret, frame = vid.read()
    
    # if the frame is empty (the video is over), break the loop
    if not ret:
        break

    # print the target vehicles
    print("\nTarget Vehicle IDs: " + str(target_vehicles))

    ############################

    # detect the car in the frame
    car_results = car_detector.track(frame, classes=2, persist=True)

    # create a list with all of the car ids
    all_car_ids = [int(car[4]) for car in car_results[0].boxes.data]

    # check if the target list has any cars that are not in the frame
    # if there are, remove them from the target list and execute the create_perm_log() function for that vehicle
    for car_id in target_vehicles:
        if car_id not in all_car_ids:
            target_vehicles.remove(car_id)
            create_perm_log(car_id, vid, write_fps)

    # if there are cars detected, get the bounding box coordinates of each car detected by looping through each array
    for index, car in enumerate(car_results[0].boxes.data):

        # get the car if it exists
        if car_results[0][index].boxes.id is None:
            car_id = 0
        else:
            car_id = int(car_results[0][index].boxes.id)

        # get the coordinates of the bounding box
        x1, y1, x2, y2 = int(car[0]), int(car[1]), int(car[2]), int(car[3])

        # crop the image to the bounding box using cv2
        car_crop = frame[y1:y2, x1:x2]

        # save the cropped image as current_vehicle.jpg
        cv2.imwrite("frames/current_vehicle.jpg", car_crop)

        ############################

        # if the car id is in the target list create directorys under it's tmp folder called "vehicle_track" and "frames"
        # under the vehicle's tmp folder log the coordinates of the car in a json file called "vehicle_track.json" and write the frame number and coordinates to it
        # also create a directory called "frames" and save the original frame as "<frame #>.jpg"
        if car_id in target_vehicles:

            ### save original frame ###
            if not os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/frames"):
                os.makedirs("logs/tmp/Vehicle_" + str(car_id) + "/frames")

            if not os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/frames/" + str(int(vid.get(cv2.CAP_PROP_POS_FRAMES))) + ".jpg"):
                cv2.imwrite("logs/tmp/Vehicle_" + str(car_id) + "/frames/" + str(int(vid.get(cv2.CAP_PROP_POS_FRAMES))) + ".jpg", frame)
            ###

            ### write vehicle track data ###
            # if the json file does not exist, create it and add the frame number and coordinates
            if not os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/vehicle_track.json"):
                f = open("logs/tmp/Vehicle_" + str(car_id) + "/vehicle_track.json", "w")
                f.write("{\n\t\"frames\": [\n\t\t{\n\t\t\t\"frame\": \"" + str(int(vid.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]\n}")
                f.close()
            # if the json file does exist, append the frame number and coordinates
            else:
                f = open("logs/tmp/Vehicle_" + str(car_id) + "/vehicle_track.json", "r")
                data = f.read()
                f.close()
                data = data.replace("]", ",\n\t\t{\n\t\t\t\"frame\": \"" + str(int(vid.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]")
                f = open("logs/tmp/Vehicle_" + str(car_id) + "/vehicle_track.json", "w")
                f.write(data)
                f.close()
            ###

        ############################

        # draw the bounding box of the car on the original frame using the color blue
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 4)

        # put the car id on the original frame using the color blue
        cv2.putText(frame, "Vehicle " + str(car_id), (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 2)

        ############################

        # run the cropped image through the license plate detector
        plate_results = plate_detector(car_crop, classes=0) # allow multiple plate detections per frame

        # if there are license plates detected, get the bounding box coordinates of each license plate detected by looping through each array
        for plate in plate_results[0].boxes.data:
    
            # get the coordinates of the bounding box
            x1, y1, x2, y2 = int(plate[0]), int(plate[1]), int(plate[2]), int(plate[3])
    
            # crop the image to the bounding box using cv2
            plate_crop = car_crop[y1:y2, x1:x2]

            # convert the cropped image to grayscale
            plate_crop = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)

            # save the cropped image as current_plate.jpg
            cv2.imwrite("frames/current_plate.jpg", plate_crop)

            ############################

            # if the car id is in the target list create a json file under the vehicle's tmp folder called "plate_track.json" and write the frame number and coordinates to it
            if car_id in target_vehicles:
                # if the json file does not exist, create it and add the frame number and coordinates
                if not os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/plate_track.json"):
                    f = open("logs/tmp/Vehicle_" + str(car_id) + "/plate_track.json", "w")
                    f.write("{\n\t\"frames\": [\n\t\t{\n\t\t\t\"frame\": \"" + str(int(vid.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]\n}")
                    f.close()
                    # if the json file does exist, append the frame number and coordinates
                else:
                    f = open("logs/tmp/Vehicle_" + str(car_id) + "/plate_track.json", "r")
                    data = f.read()
                    f.close()
                    data = data.replace("]", ",\n\t\t{\n\t\t\t\"frame\": \"" + str(int(vid.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]")
                    f = open("logs/tmp/Vehicle_" + str(car_id) + "/plate_track.json", "w")
                    f.write(data)
                    f.close()

            ############################

            # run the cropped image through the character detector
            # only detect numbers 0-9 and letters A-Z
            character_results = character_detector.readtext(plate_crop, allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") # allow multiple string detections per frame
            
            # if there are any characters detected draw a cornered bounding box of the plate area  on the original frame using the color white
            # if not then draw the cornered bounding box of the plate on the original frame using the color red and display "UNKNOWN"
            if len(character_results) > 0:
                # cv2.rectangle(frame, (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1])), (255, 0, 255), 4)

                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1]) + 20), (255, 255, 255), 4) # top left y
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[0]) + int(car[0]) + 20, int(plate[1]) + int(car[1])), (255, 255, 255), 4) # top left x
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[2]) + int(car[0]), int(plate[1]) + int(car[1]) + 20), (255, 255, 255), 4) # top right y
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[2]) + int(car[0]) - 20, int(plate[1]) + int(car[1])), (255, 255, 255), 4) # top right x
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[0]) + int(car[0]), int(plate[3]) + int(car[1]) - 20), (255, 255, 255), 4) # bottom left y
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[0]) + int(car[0]) + 20, int(plate[3]) + int(car[1])), (255, 255, 255), 4) # bottom left x
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1]) - 20), (255, 255, 255), 4) # bottom right y
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[2]) + int(car[0]) - 20, int(plate[3]) + int(car[1])), (255, 255, 255), 4) # bottom right x
            else:
                # cv2.rectangle(frame, (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1])), (0, 255, 255), 4)
                
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1]) + 20), (0, 0, 255), 4) # top left y
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[0]) + int(car[0]) + 20, int(plate[1]) + int(car[1])), (0, 0, 255), 4) # top left x
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[2]) + int(car[0]), int(plate[1]) + int(car[1]) + 20), (0, 0, 255), 4) # top right y
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[1]) + int(car[1])), (int(plate[2]) + int(car[0]) - 20, int(plate[1]) + int(car[1])), (0, 0, 255), 4) # top right x
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[0]) + int(car[0]), int(plate[3]) + int(car[1]) - 20), (0, 0, 255), 4) # bottom left y
                cv2.line(frame, (int(plate[0]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[0]) + int(car[0]) + 20, int(plate[3]) + int(car[1])), (0, 0, 255), 4) # bottom left x
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1]) - 20), (0, 0, 255), 4) # bottom right y
                cv2.line(frame, (int(plate[2]) + int(car[0]), int(plate[3]) + int(car[1])), (int(plate[2]) + int(car[0]) - 20, int(plate[3]) + int(car[1])), (0, 0, 255), 4) # bottom right x
                
                cv2.putText(frame, "UNKNOWN", (int(plate[0]) + int(car[0]), int(plate[1]) - 20 + int(car[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)

            ############################

            # add the voted plate string to the plate area label if it exists
            if os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/plates.json"):
                # if the json file exists, that means there are plates detected for this vehicle, so get the plate strings
                plate_strings = json.load(open("logs/tmp/Vehicle_" + str(car_id) + "/plates.json"))

                # extract the plates from the JSON data
                plates = plate_strings['plates']

                # get the number of plates detected
                num_plates = len(plates)

                # apply the temporal redundancy voting algorithm
                voted_plate = temporal_redundancy_voting(plates)

                # add the voted plate string to the plate area label
                cv2.putText(frame, "Voted: " + voted_plate + " (" + str(num_plates) + ")", (int(plate[0]) + int(car[0]), int(plate[1]) - 60 + int(car[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)

            ############################

            # if there are characters detected, get the bounding box coordinates of each string detected by looping through each array
            for character in character_results:
                
                # get the string
                characters = character[1]

                # get the confidence score of the string and convert it to a 2-digit percentage (xx%)
                confidence = str(int(character[2] * 100))

                # print out the plate string and confidence score
                print("License Plate: " + characters + " [" + confidence + "%]")

                # get the coordinates of the bounding box
                x1, y1, x2, y2 = int(character[0][0][0]), int(character[0][0][1]), int(character[0][2][0]), int(character[0][2][1])
    
                # draw the bounding box of the character string on the original frame (re-calculate the x&y coords by adding the car & plate coords)
                # if the license plate string is less the 3 characters, it is most likely a false positive, so use the color orange
                # if the license plate string is 3 or more characters but the confidence score is less than 50%, use the color yellow
                # if the license plate string is 3 or more characters AND the confidence score is greater than 50%, use the color green
                if len(characters) >= 3 and int(confidence) >= 50:
                    cv2.rectangle(frame, (x1 + int(car[0]) + int(plate[0]), y1 + int(car[1]) + int(plate[1])), (x2 + int(car[0]) + int(plate[0]), y2 + int(car[1]) + int(plate[1])), (0, 255, 0), 4)
                    cv2.putText(frame, "Active: " + characters + " [" + confidence + "%]", (x1 + int(car[0]) + int(plate[0]), y1 - 20 + int(car[1]) + int(plate[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
                    
                    # add the vehicle id to the target list if it is not already in it
                    if car_id not in target_vehicles:
                        target_vehicles.append(car_id)

                    # if the directory for the vehicle does not exist, create it
                    if not os.path.exists("logs/tmp/Vehicle_" + str(car_id)):
                        os.makedirs("logs/tmp/Vehicle_" + str(car_id))

                    # then log the same data into a json file in the root log folder
                    if not os.path.exists("logs/tmp/Vehicle_" + str(car_id) + "/plates.json"):
                        f = open("logs/tmp/Vehicle_" + str(car_id) + "/plates.json", "w")
                        f.write("{\n\t\"plates\": [\n\t\t{\n\t\t\t\"plate\": \"" + characters + "\",\n\t\t\t\"confidence\": \"" + confidence + "\",\n\t\t\t\"timestamp\": \"" + str(time.time()) + "\"\n\t\t}\n\t]\n}")
                        f.close()
                    else:
                        f = open("logs/tmp/Vehicle_" + str(car_id) + "/plates.json", "r")
                        data = f.read()
                        f.close()
                        data = data.replace("]", ",\n\t\t{\n\t\t\t\"plate\": \"" + characters + "\",\n\t\t\t\"confidence\": \"" + confidence + "\",\n\t\t\t\"timestamp\": \"" + str(time.time()) + "\"\n\t\t}\n\t]")
                        f = open("logs/tmp/Vehicle_" + str(car_id) + "/plates.json", "w")
                        f.write(data)
                        f.close()

                elif len(characters) >= 3:
                    cv2.rectangle(frame, (x1 + int(car[0]) + int(plate[0]), y1 + int(car[1]) + int(plate[1])), (x2 + int(car[0]) + int(plate[0]), y2 + int(car[1]) + int(plate[1])), (0, 255, 255), 4)
                    cv2.putText(frame, "Active: " + characters + " [" + confidence + "%]", (x1 + int(car[0]) + int(plate[0]), y1 - 20 + int(car[1]) + int(plate[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 2)
                elif len(characters) > 0:
                    cv2.rectangle(frame, (x1 + int(car[0]) + int(plate[0]), y1 + int(car[1]) + int(plate[1])), (x2 + int(car[0]) + int(plate[0]), y2 + int(car[1]) + int(plate[1])), (0, 165, 255), 4)
                    cv2.putText(frame, "Active: " + characters + " [" + confidence + "%]", (x1 + int(car[0]) + int(plate[0]), y1 - 20 + int(car[1]) + int(plate[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 2)

                ############################

    # save the frame as current_frame.jpg
    cv2.imwrite("frames/current_frame.jpg", frame)

    # write the frame to the output video
    out.write(frame)

# if the video is over, release the video capture and video writer
vid.release()
out.release()