# Duplicate Image Finder

A Python desktop application (built with Tkinter and OpenCV) designed to detect duplicate and visually similar images across local drives and external storage.

It accurately identifies identical photos as well as matching scanned documents/prints against smartphone camera photos taken at angles or under different lighting conditions.

## Verification Methods
* **SHA-256 Hash**: Instant 100% byte-for-byte binary matching.
* **Perceptual Hashing (pHash)**: Visual similarity matching for resized or recompressed images.
* **OpenCV ORB + RANSAC**: Feature point and homography matching for scanned vs. camera-shot photo pairs.

## Requirements & Installation

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
