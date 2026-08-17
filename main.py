import os
import hashlib
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import imagehash
import cv2
import numpy as np

class DuplicateImageFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Duplicate Image Finder (Verified Matches)")
        self.root.geometry("1000x820")

        self.target_image_path = ""
        self.search_directories = []
        
        self.target_thumb_tk = None
        self.result_thumb_tk = None
        self.live_thumb_tk = None

        # --- Top Section: Target Image Selection ---
        frame_top = ttk.Frame(root)
        frame_top.pack(fill="x", padx=10, pady=5)

        frame_target = ttk.LabelFrame(frame_top, text=" 1. Selected Target Image ")
        frame_target.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self.lbl_target_path = ttk.Label(frame_target, text="No image selected", wraplength=360)
        self.lbl_target_path.pack(padx=10, pady=5)

        self.lbl_target_img = ttk.Label(frame_target, text="[No preview]")
        self.lbl_target_img.pack(padx=10, pady=5)

        btn_target = ttk.Button(frame_target, text="Browse Image...", command=self.select_target_image)
        btn_target.pack(padx=10, pady=10)

        # --- Top Section: Search Directories ---
        frame_dirs = ttk.LabelFrame(frame_top, text=" 2. Folders / Drives to Search ")
        frame_dirs.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.lbl_dirs = ttk.Label(frame_dirs, text="No folders selected", wraplength=360)
        self.lbl_dirs.pack(padx=10, pady=5)

        btn_dirs = ttk.Button(frame_dirs, text="Add Folder...", command=self.add_directory)
        btn_dirs.pack(padx=10, pady=10)

        # --- Middle Section: Search & Live Monitor ---
        frame_controls = ttk.LabelFrame(root, text=" Search & Live Progress ")
        frame_controls.pack(fill="x", padx=10, pady=5)

        frame_status_left = ttk.Frame(frame_controls)
        frame_status_left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.btn_start = ttk.Button(frame_status_left, text="Start Search", command=self.start_search)
        self.btn_start.pack(anchor="w", pady=(0, 5))

        self.lbl_status = ttk.Label(frame_status_left, text="Waiting to start...", wraplength=550)
        self.lbl_status.pack(anchor="w")

        frame_live = ttk.LabelFrame(frame_controls, text=" Currently Checking ")
        frame_live.pack(side="right", padx=10, pady=5)

        self.lbl_live_img = ttk.Label(frame_live, text="[Waiting]", width=20, anchor="center")
        self.lbl_live_img.pack(padx=10, pady=10)

        # --- Bottom Section: Results ---
        frame_bottom = ttk.Frame(root)
        frame_bottom.pack(fill="both", expand=True, padx=10, pady=5)

        frame_results = ttk.LabelFrame(frame_bottom, text=" Verified Matches ")
        frame_results.pack(side="left", fill="both", expand=True, padx=(0, 5))

        columns = ("path", "type")
        self.tree = ttk.Treeview(frame_results, columns=columns, show="headings")
        self.tree.heading("path", text="File Path")
        self.tree.heading("type", text="Verification Method")
        self.tree.column("path", width=420)
        self.tree.column("type", width=220)

        scrollbar = ttk.Scrollbar(frame_results, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_result_selected)

        # Preview on the right
        frame_preview = ttk.LabelFrame(frame_bottom, text=" Verified Image Preview ")
        frame_preview.pack(side="right", fill="both", expand=False, padx=(5, 0))

        self.lbl_result_img = ttk.Label(frame_preview, text="No verified\nmatch", width=25, anchor="center")
        self.lbl_result_img.pack(padx=15, pady=15)

    def select_target_image(self):
        path = filedialog.askopenfilename(
            title="Select Target Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff *.cr2 *.nef *.heic *.arw")]
        )
        if path:
            self.target_image_path = path
            self.lbl_target_path.config(text=path)
            self.show_thumbnail(path, self.lbl_target_img, is_target=True)

    def add_directory(self):
        path = filedialog.askdirectory(title="Select Folder or Drive Root")
        if path and path not in self.search_directories:
            self.search_directories.append(path)
            self.lbl_dirs.config(text="\n".join(self.search_directories))

    def show_thumbnail(self, image_path, label_widget, is_target=False, size=(160, 160)):
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size)
                tk_img = ImageTk.PhotoImage(img)
                label_widget.config(image=tk_img, text="")
                if is_target:
                    self.target_thumb_tk = tk_img
                else:
                    self.result_thumb_tk = tk_img
        except Exception:
            label_widget.config(image="", text="Cannot display image")

    def update_live_preview(self, filepath, count, filename):
        self.lbl_status.config(text=f"Checking ({count}): {filename}")
        try:
            with Image.open(filepath) as img:
                img.thumbnail((120, 120))
                tk_img = ImageTk.PhotoImage(img)
                self.lbl_live_img.config(image=tk_img, text="")
                self.live_thumb_tk = tk_img
        except Exception:
            self.lbl_live_img.config(image="", text="[No image]")

    def start_search(self):
        if not self.target_image_path:
            messagebox.showwarning("Missing Information", "Please select a target image first.")
            return
        if not self.search_directories:
            messagebox.showwarning("Missing Information", "Please select at least one folder or drive.")
            return

        self.btn_start.config(state="disabled")
        for item in self.tree.get_children():
            self.tree.delete(item)

        threading.Thread(target=self.run_search_process, daemon=True).start()

    def run_search_process(self):
        self.update_status("Calculating target image mathematical features...")

        target_sha = self.get_file_sha256(self.target_image_path)
        target_phash = self.get_image_phash(self.target_image_path)
        target_kp, target_des, orb = self.get_orb_descriptors(self.target_image_path)

        if not target_sha or not target_phash:
            self.update_status("Error reading target image.")
            self.btn_start.config(state="normal")
            return

        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.cr2', '.nef', '.heic', '.arw'}
        scanned_count = 0

        for drive in self.search_directories:
            for root, dirs, files in os.walk(drive):
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in valid_extensions:
                        full_path = os.path.join(root, file)
                        scanned_count += 1

                        self.root.after(0, self.update_live_preview, full_path, scanned_count, file)

                        if os.path.abspath(full_path) == os.path.abspath(self.target_image_path):
                            continue

                        # LEVEL 1: SHA-256 Binary Match
                        current_sha = self.get_file_sha256(full_path)
                        if current_sha and current_sha == target_sha:
                            self.root.after(0, self.add_verified_result, full_path, "Verified (100% Identical File)")
                            continue

                        # LEVEL 2: Strict Perceptual Hash (pHash <= 3)
                        current_phash = self.get_image_phash(full_path)
                        is_matched = False
                        if current_phash:
                            distance = target_phash - current_phash
                            if distance <= 3:
                                self.root.after(0, self.add_verified_result, full_path, f"Verified Image (pHash dist: {distance})")
                                is_matched = True

                        # LEVEL 3: OpenCV ORB + RANSAC Feature Matching
                        if not is_matched and target_des is not None and target_kp is not None:
                            curr_kp, curr_des, _ = self.get_orb_descriptors(full_path, orb_instance=orb)
                            if curr_des is not None and len(curr_des) >= 10:
                                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                                matches = bf.match(target_des, curr_des)
                                good_matches = [m for m in matches if m.distance < 45]
                                
                                if len(good_matches) >= 12:
                                    src_pts = np.float32([ target_kp[m.queryIdx].pt for m in good_matches ]).reshape(-1,1,2)
                                    dst_pts = np.float32([ curr_kp[m.trainIdx].pt for m in good_matches ]).reshape(-1,1,2)
                                    
                                    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                                    if mask is not None:
                                        inliers = int(np.sum(mask))
                                        if inliers >= 10:
                                            self.root.after(0, self.add_verified_result, full_path, f"Verified Camera/Scan ({inliers} geopoints)")

        self.update_status(f"Done! Scanned {scanned_count} images. Verified matches listed.")
        self.btn_start.config(state="normal")

    def get_orb_descriptors(self, filepath, orb_instance=None):
        try:
            if orb_instance is None:
                orb_instance = cv2.ORB_create(nfeatures=800)
                
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return None, None, orb_instance

            h, w = img.shape[:2]
            if max(h, w) > 800:
                scale = 800 / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))

            kp, des = orb_instance.detectAndCompute(img, None)
            return kp, des, orb_instance
        except Exception:
            return None, None, orb_instance

    def update_status(self, text):
        self.root.after(0, lambda: self.lbl_status.config(text=text))

    def add_verified_result(self, path, match_type):
        self.tree.insert("", "end", values=(path, match_type))
        self.show_thumbnail(path, self.lbl_result_img, is_target=False, size=(200, 200))

    def on_result_selected(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            item_values = self.tree.item(selected_items[0], "values")
            if item_values:
                file_path = item_values[0]
                self.show_thumbnail(file_path, self.lbl_result_img, is_target=False, size=(200, 200))

    def get_file_sha256(self, filepath):
        hasher = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def get_image_phash(self, filepath):
        try:
            with Image.open(filepath) as img:
                return imagehash.phash(img)
        except Exception:
            return None

if __name__ == "__main__":
    root = tk.Tk()
    app = DuplicateImageFinderApp(root)
    root.mainloop()
