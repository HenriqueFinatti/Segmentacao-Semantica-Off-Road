import os
import cv2

class Video:

    def __init__(self, video_path, output_path):
        self.video_path = video_path
        self.output_path = output_path

    def extract_video(self):
        frame_id = 0

        images_dir = os.path.join("images", "images_to_segment")
        os.makedirs(images_dir, exist_ok=True)

        video = cv2.VideoCapture(self.video_path)

    def make_segmented_video(self):
        segmented_images_dir = os.path.join("images", "segmented_images")
        
