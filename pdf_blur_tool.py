import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                             QGraphicsScene, QGraphicsPixmapItem, QFileDialog, 
                             QVBoxLayout, QWidget, QToolBar, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QAction, QPen

from pdf2image import convert_from_path
from PIL import Image, ImageFilter

class BlurScene(QGraphicsScene):
    """
    Custom Scene to handle mouse events for drawing the selection box.
    """
    area_selected = pyqtSignal(QRectF)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_point = None
        self.current_rect_item = None
        self.is_drawing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.scenePos()
            self.is_drawing = True
            # Create a visual selection box
            self.current_rect_item = self.addRect(QRectF(self.start_point, self.start_point), 
                                                  QPen(QColor("red"), 2), 
                                                  QColor(255, 0, 0, 50))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing and self.current_rect_item:
            current_pos = event.scenePos()
            # Update the rectangle as we drag
            rect = QRectF(self.start_point, current_pos).normalized()
            self.current_rect_item.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_drawing and event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            if self.current_rect_item:
                rect = self.current_rect_item.rect()
                
                # --- FIX START ---
                # 1. Remove the red box FIRST, before processing the image
                self.removeItem(self.current_rect_item)
                self.current_rect_item = None
                
                # 2. NOW emit the signal to blur the image
                self.area_selected.emit(rect)
                # --- FIX END ---
                
        super().mouseReleaseEvent(event)


class PDFBlurApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF Blur Tool - Fixed")
        self.resize(1000, 800)
        self.setAcceptDrops(True)

        self.pages_images = [] 
        self.current_page_index = 0
        self.current_file_path = None

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        open_action = QAction("Open PDF", self)
        open_action.triggered.connect(self.open_pdf_dialog)
        self.toolbar.addAction(open_action)

        save_action = QAction("Save PDF", self)
        save_action.triggered.connect(self.save_pdf)
        self.toolbar.addAction(save_action)

        self.toolbar.addSeparator()

        self.prev_btn = QAction("<< Previous", self)
        self.prev_btn.triggered.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        self.toolbar.addAction(self.prev_btn)

        self.lbl_page = QLabel(" Page: 0 / 0 ")
        self.toolbar.addWidget(self.lbl_page)

        self.next_btn = QAction("Next >>", self)
        self.next_btn.triggered.connect(self.next_page)
        self.next_btn.setEnabled(False)
        self.toolbar.addAction(self.next_btn)

        self.toolbar.addSeparator()
        info_lbl = QLabel("  (Drag PDF here -> Select area to Blur)")
        info_lbl.setStyleSheet("color: gray;")
        self.toolbar.addWidget(info_lbl)

        self.scene = BlurScene()
        self.scene.area_selected.connect(self.apply_blur)
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        layout.addWidget(self.view)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if f.lower().endswith(".pdf"):
                self.load_pdf(f)
                break 

    def open_pdf_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if fname:
            self.load_pdf(fname)

    def load_pdf(self, file_path):
        try:
            self.lbl_page.setText(" Loading... ")
            QApplication.processEvents()
            self.pages_images = convert_from_path(file_path)
            self.current_file_path = file_path
            self.current_page_index = 0
            self.update_display()
            self.update_controls()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load PDF.\nError: {str(e)}")
            self.lbl_page.setText(" Error ")

    def update_display(self):
        if not self.pages_images:
            return

        pil_image = self.pages_images[self.current_page_index]

        # Convert to RGBA for display
        pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        
        self.lbl_page.setText(f" Page: {self.current_page_index + 1} / {len(self.pages_images)} ")

    def update_controls(self):
        self.prev_btn.setEnabled(self.current_page_index > 0)
        self.next_btn.setEnabled(self.current_page_index < len(self.pages_images) - 1)

    def prev_page(self):
        if self.current_page_index > 0:
            self.current_page_index -= 1
            self.update_display()
            self.update_controls()

    def next_page(self):
        if self.current_page_index < len(self.pages_images) - 1:
            self.current_page_index += 1
            self.update_display()
            self.update_controls()

    def apply_blur(self, rect_f):
        if not self.pages_images:
            return

        pil_img = self.pages_images[self.current_page_index]
        img_w, img_h = pil_img.size

        # --- FIX: ROBUST COORDINATE CALCULATION ---
        # Convert to integers
        x1 = int(rect_f.x())
        y1 = int(rect_f.y())
        x2 = int(rect_f.x() + rect_f.width())
        y2 = int(rect_f.y() + rect_f.height())

        # Ensure we don't try to blur outside the image (prevents errors)
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(img_w, x2)
        y2 = min(img_h, y2)

        # Calculate width/height from clamped values
        w = x2 - x1
        h = y2 - y1

        # If selection is too small or invalid, do nothing
        if w <= 1 or h <= 1:
            return
        
        box = (x1, y1, x2, y2)
        region = pil_img.crop(box)
        
        # Apply Blur
        blurred_region = region.filter(ImageFilter.GaussianBlur(radius=15))
        
        pil_img.paste(blurred_region, box)
        self.pages_images[self.current_page_index] = pil_img
        
        self.update_display()

    def save_pdf(self):
        if not self.pages_images:
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save Blurred PDF", "", "PDF Files (*.pdf)")
        if save_path:
            try:
                # Convert back to RGB for saving as PDF
                pdf_pages = [img.convert("RGB") for img in self.pages_images]
                pdf_pages[0].save(
                    save_path, 
                    "PDF", 
                    resolution=100.0, 
                    save_all=True, 
                    append_images=pdf_pages[1:]
                )
                QMessageBox.information(self, "Success", "PDF Saved Successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save PDF: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFBlurApp()
    window.show()
    sys.exit(app.exec())