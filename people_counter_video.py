# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 11:52:55 2020

@author: Layi
"""

# USAGE
# To read and write back out to video:
# python people_counter.py --mode vertical \
# 	--input videos/vertical_01.mp4 --output output/vertical_01.avi
#
# To read from webcam and write back out to disk:
# python people_counter.py --mode vertical \
# 	--output output/webcam_output.avi

# import the necessary packages
import directioncounter
import centroidtracker
import Trackableobject
#from multiprocessing import Process
#from multiprocessing import Queue
#from multiprocessing import Value
from imutils.video import VideoStream
from imutils.video import FPS
import argparse
import imutils
import time
import cv2

#def write_video(outputPath, writeVideo, frameQueue, W, H):
	# initialize the FourCC and video writer object
#	fourcc = cv2.VideoWriter_fourcc(*"MJPG")
#		(W, H), True)

	# loop while the write flag is set or the output frame queue is
	# not empty
#	while writeVideo.value or not frameQueue.empty():
		# check if the output frame queue is not empty
#		if not frameQueue.empty():
			# get the frame from the queue and write the frame
#			frame = frameQueue.get()
#			writer.write(frame)

	# release the video writer object
#	writer.release()

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-m", "--mode", type=str, required=True,
	choices=["horizontal", "vertical"],
	help="direction in which people will be moving")
ap.add_argument("-i", "--input", type=str,
	help="path to optional input video file")
ap.add_argument("-o", "--output", type=str,
	help="path to optional output video file")
ap.add_argument("-s", "--skip-frames", type=int, default=0,
	help="# of skip frames between detections")
args = vars(ap.parse_args())

# if a video path was not supplied, grab a reference to the webcam
if not args.get("input", False):
	print("[INFO] starting video stream...")
	vs = VideoStream(src=0).start()
	#vs = VideoStream(usePiCamera=True).start()
	time.sleep(2.0)

# otherwise, grab a reference to the video file
else:
	print("[INFO] opening video file...")
	vs = cv2.VideoCapture(args["input"])

# initialize the video writing process object (we'll instantiate
# later if need be) along with the frame dimensions
writerProcess = None
W = None
H = None

# instantiate our centroid tracker, then initialize a list to store
# each of our dlib correlation trackers, followed by a dictionary to
# map each unique object ID to a trackable object
ct = centroidtracker.CentroidTracker(maxDisappeared=15, maxDistance=100)
trackers = []
trackableObjects = {}

# initialize the direction info variable (used to store information
# such as up/down or left/right people count)
directionInfo = None

# initialize the MOG foreground background subtractor and start the
# frames per second throughput estimator
mog = cv2.createBackgroundSubtractorMOG2()
fps = FPS().start()

# loop over frames from the video stream
while True:
	# grab the next frame and handle if we are reading from either
	# VideoCapture or VideoStream
	frame = vs.read()
	frame = frame[1] if args.get("input", False) else frame

	# if we are viewing a video and we did not grab a frame then we
	# have reached the end of the video
	if args["input"] is not None and frame is None:
		break

	# set the frame dimensions and instantiate direction counter
	# object if required
	if W is None or H is None:
		(H, W) = frame.shape[:2]
		dc = directioncounter.DirectionCounter(args["mode"], H, W)

	# begin writing the video to disk if required
	#if args["output"] is not None and writerProcess is None:
		# set the value of the write flag (used to communicate when to stop the writing process
		
        
		#writeVideo = Value('i', 1)
		vid_writer = cv2.VideoWriter("my_vid.mp4",cv2.VideoWriter_fourcc('M','J','P','G'), 10, (W,H))
		print("[INFO] writing video file")
		#frameQueue = Queue()
		#writerProcess = Process(target=write_video, args=(
		#	args["output"], writeVideo, frameQueue, W, H))
		#writerProcess.start()

	# initialize a list to store the bounding box rectangles returned
	# by background subtraction model
	rects = []

	# convert the frame to grayscale and smoothen it using a
	# gaussian kernel
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (5, 5), 0)

	# apply the MOG background subtraction model
	mask = mog.apply(gray)

	# apply a series of erosions to break apart connected
	# components, then find contours in the mask
	erode = cv2.erode(mask, (7, 7), iterations=2)
	cnts = cv2.findContours(erode.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)
	cnts = imutils.grab_contours(cnts)

	# loop over each contour
	for c in cnts:
		# if the contour area is less than the minimum area
		# required then ignore the object
		if cv2.contourArea(c) < 2000:
			continue

		# compute the bounding box coordinates of the contour
		(x, y, w, h) = cv2.boundingRect(c)
		(startX, startY, endX, endY) = (x, y, x + w, y + h)

		# add the bounding box coordinates to the rectangles list
		rects.append((startX, startY, endX, endY))

	# check if the direction is vertical
	if args["mode"] == "vertical":
		# draw a horizontal line in the center of the frame -- once an
		# object crosses this line we will determine whether they were
		# moving 'up' or 'down'
		cv2.line(frame, (0, H // 2), (W, H // 2), (0, 255, 255), 2)

	# otherwise, the direction is horizontal
	else:
		# draw a vertical line in the center of the frame -- once an
		# object crosses this line we will determine whether they
		# were moving 'left' or 'right'
		cv2.line(frame, (W // 2, 0), (W // 2, H), (0, 255, 255), 2)

	# use the centroid tracker to associate the (1) old object
	# centroids with (2) the newly computed object centroids
	objects = ct.update(rects)

	# loop over the tracked objects
	for (objectID, centroid) in objects.items():
		# grab the trackable object via its object ID
		to = trackableObjects.get(objectID, None)
		color = (0, 0, 255)

		# create a new trackable object if needed
		if to is None:
			to = Trackableobject.TrackableObject(objectID, centroid)

		# otherwise, there is a trackable object so we can utilize it
		# to determine direction
		else:
			# find the direction and update the list of centroids
			dc.find_direction(to, centroid)
			to.centroids.append(centroid)

			# check to see if the object has been counted or not
			if not to.counted:
				# find the direction of motion of the people
				directionInfo = dc.count_object(to, centroid)

			# otherwise, the object has been counted and set the
			# color to green indicate it has been counted
			else:
				color = (0, 255, 0)

		# store the trackable object in our dictionary
		trackableObjects[objectID] = to

		# draw both the ID of the object and the centroid of the
		# object on the output frame
		text = "ID {}".format(objectID)
		cv2.putText(frame, text, (centroid[0] - 10,	centroid[1] - 10),
			cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
		cv2.circle(frame, (centroid[0], centroid[1]), 4, color, -1)

	# extract the people counts and write/draw them
	if directionInfo is not None:#
		for (i, (k, v)) in enumerate(directionInfo):
			text = "{}: {}".format(k, v)
			cv2.putText(frame, text, (10, H - ((i * 20) + 20)),
				cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

	# put frame into the shared queue for video writing
	#if writerProcess is not None:#
	#	frameQueue.put(frame)

	# show the output frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF

	vid_writer.write(frame)
	if key == ord("q"):
		break

	
	fps.update()

# stop the timer and display FPS information
fps.stop()
print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# terminate the video writer process
#if writerProcess is not None:
print("video writing completed")
    #writeVideo.value = 0
    #writerProcess.join()
    
# if we are not using a video file, stop the camera video stream
if not args.get("input", False):
	vs.stop()

# otherwise, release the video file pointer
else:
	vs.release()

vid_writer.release()
cv2.destroyAllWindows()