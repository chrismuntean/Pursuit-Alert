import os
import cv2
import time
from ultralytics import YOLO
import easyocr
from collections import Counter
import json
from colorama import Fore, Back, Style

# initialize models
vehicle_detector = YOLO('models/yolov8n.pt') # object detection
plate_detector = YOLO('models/license_plate.pt') # object detection
character_detector = easyocr.Reader(['en']) # optical character recognition

def clear_logs():

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

def calc_write_fps(stream, frame_skip):

    # calculate the coresponding re-write fps based on the frame_skip and the original video fps
    orig_fps = stream.get(cv2.CAP_PROP_FPS)
    if frame_skip == 0:
        write_fps = orig_fps
    else:
        write_fps = orig_fps / frame_skip

    print("Original FPS: " + str(orig_fps))
    print("Frame Skip: " + str(frame_skip))
    print("Write FPS: " + str(write_fps))

    return write_fps

#_# FOR DEVELOPMENT ONLY #_#
def create_dev_vid(stream, write_fps):

    # get the frame size from the original video stream
    frame_width = int(stream.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(stream.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Define the codec and create VideoWriter object to save the video to /logs/output.mp4
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('logs/dev_output.mp4', fourcc, write_fps, (frame_width, frame_height))

    return out
#^# FOR DEVELOPMENT ONLY #^#

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

def create_perm_log(veh_id, vid, write_fps):
    
    # Load plate strings and vehicle tracking data from JSON files if they exist
    with open(f"logs/tmp/Vehicle_{veh_id}/plates.json", "r") as file:
        plate_strings = json.load(file)
    
    if os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/vehicle_track.json"):
        with open(f"logs/tmp/Vehicle_{veh_id}/vehicle_track.json", "r") as file:
            vehicle_data = json.load(file)
            vehicle_data_found = True
    else:
        vehicle_data_found = False
    
    if os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/plate_track.json"):
        with open(f"logs/tmp/Vehicle_{veh_id}/plate_track.json", "r") as file:
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

    # Determine the correct directory name with a counter
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
    out = cv2.VideoWriter(f"{seen_path}/video.mp4", fourcc, write_fps, (width, height))

    # Restructure vehicle and plate tracking data
    if (vehicle_data_found):
        vehicle_frames_dict = {int(d['frame']): d for d in vehicle_data['frames']}

    if (plate_data_found):
        plate_frames_dict = {int(d['frame']): d for d in plate_track_data['frames']}

    # Process each frame and save one cropped image of the vehicle and plate
    frame_dir = f"logs/tmp/Vehicle_{veh_id}/frames"
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
    os.system("rm -rf logs/tmp/Vehicle_" + str(veh_id))

#_# ALPR functions #_#
def detect_chars(plate_crop, plate_plot, veh_plot, veh_id):

    # run the cropped image through the character detector
    # only detect numbers 0-9 and letters A-Z
    character_results = character_detector.readtext(plate_crop, allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") # allow multiple string detections per frame
            
    # if there are any characters detected draw a cornered bounding box of the plate area on the original frame using the color white
    # if not then draw the cornered bounding box of the plate on the original frame using the color red and display "UNKNOWN"
    if len(character_results) > 0:
        # cv2.rectangle(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (255, 0, 255), 4)

        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1]) + 20), (255, 255, 255), 4) # top left y
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]) + 20, int(plate_plot[1]) + int(veh_plot[1])), (255, 255, 255), 4) # top left x
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1]) + 20), (255, 255, 255), 4) # top right y
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]) - 20, int(plate_plot[1]) + int(veh_plot[1])), (255, 255, 255), 4) # top right x
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1]) - 20), (255, 255, 255), 4) # bottom left y
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]) + 20, int(plate_plot[3]) + int(veh_plot[1])), (255, 255, 255), 4) # bottom left x
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1]) - 20), (255, 255, 255), 4) # bottom right y
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]) - 20, int(plate_plot[3]) + int(veh_plot[1])), (255, 255, 255), 4) # bottom right x
    else:
        # cv2.rectangle(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (0, 255, 255), 4)
        
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1]) + 20), (0, 0, 255), 4) # top left y
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]) + 20, int(plate_plot[1]) + int(veh_plot[1])), (0, 0, 255), 4) # top left x
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1]) + 20), (0, 0, 255), 4) # top right y
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[1]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]) - 20, int(plate_plot[1]) + int(veh_plot[1])), (0, 0, 255), 4) # top right x
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1]) - 20), (0, 0, 255), 4) # bottom left y
        cv2.line(frame, (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[0]) + int(veh_plot[0]) + 20, int(plate_plot[3]) + int(veh_plot[1])), (0, 0, 255), 4) # bottom left x
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1]) - 20), (0, 0, 255), 4) # bottom right y
        cv2.line(frame, (int(plate_plot[2]) + int(veh_plot[0]), int(plate_plot[3]) + int(veh_plot[1])), (int(plate_plot[2]) + int(veh_plot[0]) - 20, int(plate_plot[3]) + int(veh_plot[1])), (0, 0, 255), 4) # bottom right x
        
        cv2.putText(frame, "UNKNOWN", (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) - 20 + int(veh_plot[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)

    ############################

    # add the voted plate string to the plate area label if it exists
    if os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/plates.json"):
        # if the json file exists, that means there are plates detected for this vehicle, so get the plate strings
        plate_strings = json.load(open("logs/tmp/Vehicle_" + str(veh_id) + "/plates.json"))

        # extract the plates from the JSON data
        plates = plate_strings['plates']

        # get the number of plates detected
        num_plates = len(plates)

        # apply the temporal redundancy voting algorithm
        voted_plate = temporal_redundancy_voting(plates)

        # print out the voted plate string and the vote count (number of plates detected)
        print(Fore.MAGENTA + "\nVoted Plate: " + voted_plate + " (" + str(num_plates) + ")" + Style.RESET_ALL)

        # add the voted plate string to the plate area label
        cv2.putText(frame, "Voted: " + voted_plate + " (" + str(num_plates) + ")", (int(plate_plot[0]) + int(veh_plot[0]), int(plate_plot[1]) - 60 + int(veh_plot[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)

    ############################

    # if there are characters detected, get the bounding box coordinates of each string detected by looping through each array
    for character in character_results:
        
        # get the string
        characters = character[1]

        # get the confidence score of the string and convert it to a 2-digit percentage (xx%)
        confidence = str(int(character[2] * 100))

        # print out the active plate string and confidence score
        # if the confidence score is more than 50% AND more than 3 characters use the color green
        # if the confidence score is less than 50% AND more than 3 characters use the color yellow
        # if the length of the string is less than 3 characters use the color red
        if len(characters) >= 3 and int(confidence) >= 50:
            print(Fore.GREEN + "\nActive Plate: " + characters + " [" + confidence + "%]" + Style.RESET_ALL) # green
        elif len(characters) >= 3:
            print(Fore.YELLOW + "\nActive Plate: " + characters + " [" + confidence + "%]" + Style.RESET_ALL) # yellow
        elif len(characters) > 0:
            print(Fore.LIGHTRED_EX + "\nActive Plate: " + characters + " [" + confidence + "%]" + Style.RESET_ALL) # red

        # print("Active Plate: " + characters + " [" + confidence + "%]")

        # get the coordinates of the bounding box
        x1, y1, x2, y2 = int(character[0][0][0]), int(character[0][0][1]), int(character[0][2][0]), int(character[0][2][1])

        # draw the bounding box of the character string on the original frame (re-calculate the x&y coords by adding the vehicle & plate coords)
        # if the license plate string is less the 3 characters, it is most likely inacurate, so use the color orange
        # if the license plate string is 3 or more characters BUT the confidence score is less than 50%, use the color yellow
        # if the license plate string is 3 or more characters AND the confidence score is greater than 50%, use the color green and log
        if len(characters) >= 3 and int(confidence) >= 50:
            cv2.rectangle(frame, (x1 + int(veh_plot[0]) + int(plate_plot[0]), y1 + int(veh_plot[1]) + int(plate_plot[1])), (x2 + int(veh_plot[0]) + int(plate_plot[0]), y2 + int(veh_plot[1]) + int(plate_plot[1])), (0, 255, 0), 4)
            cv2.putText(frame, "Active: " + characters + " [" + confidence + "%]", (x1 + int(veh_plot[0]) + int(plate_plot[0]), y1 - 20 + int(veh_plot[1]) + int(plate_plot[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 2)
            
            # add the vehicle id to the target list if it is not already in it
            if veh_id not in target_vehicles:
                target_vehicles.append(veh_id)

            # if the directory for the vehicle does not exist, create it
            if not os.path.exists("logs/tmp/Vehicle_" + str(veh_id)):
                os.makedirs("logs/tmp/Vehicle_" + str(veh_id))

            # then log the same data into a json file in the root log folder
            if not os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/plates.json"):
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/plates.json", "w")
                f.write("{\n\t\"plates\": [\n\t\t{\n\t\t\t\"plate\": \"" + characters + "\",\n\t\t\t\"confidence\": \"" + confidence + "\",\n\t\t\t\"timestamp\": \"" + str(time.time()) + "\"\n\t\t}\n\t]\n}")
                f.close()
            else:
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/plates.json", "r")
                data = f.read()
                f.close()
                data = data.replace("]", ",\n\t\t{\n\t\t\t\"plate\": \"" + characters + "\",\n\t\t\t\"confidence\": \"" + confidence + "\",\n\t\t\t\"timestamp\": \"" + str(time.time()) + "\"\n\t\t}\n\t]")
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/plates.json", "w")
                f.write(data)
                f.close()

        elif len(characters) >= 3:
            cv2.rectangle(frame, (x1 + int(veh_plot[0]) + int(plate_plot[0]), y1 + int(veh_plot[1]) + int(plate_plot[1])), (x2 + int(veh_plot[0]) + int(plate_plot[0]), y2 + int(veh_plot[1]) + int(plate_plot[1])), (0, 255, 255), 4)
            cv2.putText(frame, "Active: " + characters + " [" + confidence + "%]", (x1 + int(veh_plot[0]) + int(plate_plot[0]), y1 - 20 + int(veh_plot[1]) + int(plate_plot[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 2)
        elif len(characters) > 0:
            cv2.rectangle(frame, (x1 + int(veh_plot[0]) + int(plate_plot[0]), y1 + int(veh_plot[1]) + int(plate_plot[1])), (x2 + int(veh_plot[0]) + int(plate_plot[0]), y2 + int(veh_plot[1]) + int(plate_plot[1])), (0, 165, 255), 4)
            cv2.putText(frame, "Active: " + characters + " [" + confidence + "%]", (x1 + int(veh_plot[0]) + int(plate_plot[0]), y1 - 20 + int(veh_plot[1]) + int(plate_plot[1])), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 165, 255), 2)

        ############################

def detect_plate(veh_crop, veh_plot, veh_id, stream):

    # run the cropped image through the license plate detector
    plate_results = plate_detector(veh_crop, classes=0) # allow multiple plate detections per frame

    # if there are license plates detected, get the bounding box coordinates of each license plate detected by looping through each array
    for plate_plot in plate_results[0].boxes.data:
    
        # get the coordinates of the bounding box
        x1, y1, x2, y2 = int(plate_plot[0]), int(plate_plot[1]), int(plate_plot[2]), int(plate_plot[3])
    
        # crop the image to the bounding box using cv2
        plate_crop = veh_crop[y1:y2, x1:x2]

        # convert the cropped image to grayscale
        plate_crop = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)

        # save the cropped image as current_plate.jpg
        cv2.imwrite("frames/current_plate.jpg", plate_crop)

        ############################

        # if the vehicle id is in the target list create a json file under the vehicle's tmp folder called "plate_track.json" and write the frame number and coordinates to it
        if veh_id in target_vehicles:
            # if the json file does not exist, create it and add the frame number and coordinates
            if not os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/plate_track.json"):
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/plate_track.json", "w")
                f.write("{\n\t\"frames\": [\n\t\t{\n\t\t\t\"frame\": \"" + str(int(stream.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]\n}")
                f.close()
                # if the json file does exist, append the frame number and coordinates
            else:
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/plate_track.json", "r")
                data = f.read()
                f.close()
                data = data.replace("]", ",\n\t\t{\n\t\t\t\"frame\": \"" + str(int(stream.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]")
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/plate_track.json", "w")
                f.write(data)
                f.close()
        
        ############################

        # then run the cropped image through the character detector
        # the detect_chars() function will also draw the plate area data (with different colors depending on char results)
        detect_chars(plate_crop, plate_plot, veh_plot, veh_id)

def detect_vehicles(frame, stream):

    # detect the vehicle (veh) in the frame
    veh_results = vehicle_detector.track(frame, classes=2, persist=True)

    # create a list with all of the veh ids
    all_veh_ids = [int(veh[4]) for veh in veh_results[0].boxes.data]

    # loop through the target vehicles
    for veh_id in target_vehicles:
        # if the target vehicle is not in the frame
        if veh_id not in all_veh_ids:
            # remove the vehicle ID from the target list and execute the create_perm_log() function for that vehicle
            target_vehicles.remove(veh_id)
            create_perm_log(veh_id, stream, write_fps)

    # if there are vehicles detected, get the bounding box coordinates of each veh detected by looping through each array
    for index, veh_plot in enumerate(veh_results[0].boxes.data):

        # get the veh if it exists
        if veh_results[0][index].boxes.id is None:
            veh_id = 0
        else:
            veh_id = int(veh_results[0][index].boxes.id)

        # get the coordinates of the bounding box
        x1, y1, x2, y2 = int(veh_plot[0]), int(veh_plot[1]), int(veh_plot[2]), int(veh_plot[3])

        # crop the image to the bounding box using cv2
        veh_crop = frame[y1:y2, x1:x2]

        # save the cropped image as current_vehicle.jpg
        cv2.imwrite("frames/current_vehicle.jpg", veh_crop)

        ############################

        # if the veh id is in the target list create directorys under it's tmp folder called "vehicle_track" and "frames"
        # under the vehicle's tmp folder log the coordinates of the veh in a json file called "vehicle_track.json" and write the frame number and coordinates to it
        # also create a directory called "frames" and save the original frame as "<frame #>.jpg"
        if veh_id in target_vehicles:

            ### save original frame ###
            if not os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/frames"):
                os.makedirs("logs/tmp/Vehicle_" + str(veh_id) + "/frames")

            if not os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/frames/" + str(int(stream.get(cv2.CAP_PROP_POS_FRAMES))) + ".jpg"):
                cv2.imwrite("logs/tmp/Vehicle_" + str(veh_id) + "/frames/" + str(int(stream.get(cv2.CAP_PROP_POS_FRAMES))) + ".jpg", frame)
            ###

            ### write vehicle track data ###
            # if the json file does not exist, create it and add the frame number and coordinates
            if not os.path.exists("logs/tmp/Vehicle_" + str(veh_id) + "/vehicle_track.json"):
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/vehicle_track.json", "w")
                f.write("{\n\t\"frames\": [\n\t\t{\n\t\t\t\"frame\": \"" + str(int(stream.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]\n}")
                f.close()
            # if the json file does exist, append the frame number and coordinates
            else:
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/vehicle_track.json", "r")
                data = f.read()
                f.close()
                data = data.replace("]", ",\n\t\t{\n\t\t\t\"frame\": \"" + str(int(stream.get(cv2.CAP_PROP_POS_FRAMES))) + "\",\n\t\t\t\"x1\": \"" + str(x1) + "\",\n\t\t\t\"y1\": \"" + str(y1) + "\",\n\t\t\t\"x2\": \"" + str(x2) + "\",\n\t\t\t\"y2\": \"" + str(y2) + "\"\n\t\t}\n\t]")
                f = open("logs/tmp/Vehicle_" + str(veh_id) + "/vehicle_track.json", "w")
                f.write(data)
                f.close()
            ###

        ############################

        # draw the bounding box of the veh on the original frame using the color blue
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 4)

        # put the veh id on the original frame using the color blue
        cv2.putText(frame, "Vehicle " + str(veh_id), (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 2)

        ############################

        # run the cropped image through the license plate detector
        # the detect_plate() function will continue the process to char detection
        detect_plate(veh_crop, veh_plot, veh_id, stream)
#^# ALPR functions #^#

############################
############################
############################

# start by clearing the logs
clear_logs()

############################
### DO NOT EDIT ABOVE THIS LINE ###
#### CONFIGURATION  VARIABLES ####

# get the video file path
stream_path = 'test_files/test_vids/test_vid_7_(4k).mov'
# vid_path = 0 # for webcam
frame_skip = 10 # maxes out at the fps of original video/ camera stream
# frame_skip = 0 # no frame skipping

#### CONFIGURATION  VARIABLES ####
### DO NOT EDIT BELOW THIS LINE ###
############################

# create a video capture object from video stream
stream = cv2.VideoCapture(stream_path)

# calculate the write fps
write_fps = calc_write_fps(stream, frame_skip)

# create a video writer object for development
dev_out = create_dev_vid(stream, write_fps) # FOR DEVELOPMENT ONLY

# create a empty list to hold the target vehicles that have plate detections
target_vehicles = []

# create a loop to go through every frame
while True:

    # set the frame_skip on the video stream
    stream.set(cv2.CAP_PROP_POS_FRAMES, stream.get(cv2.CAP_PROP_POS_FRAMES) + frame_skip)

    # get the frame
    ret, frame = stream.read()
    
    # if the frame is empty (the video is over), break the loop
    if not ret:
        break

    # print the target vehicles
    print("\nTarget Vehicle IDs: " + str(target_vehicles))

    # start the ALPR process
    # detect_vehicles() -> detect_plate() -> detect_chars()
    detect_vehicles(frame, stream)

    # save the frame as current_frame.jpg
    cv2.imwrite("frames/current_frame.jpg", frame)
    
    dev_out.write(frame) # FOR DEVELOPMENT ONLY

# release the video capture object
stream.release()
dev_out.release() # FOR DEVELOPMENT ONLY