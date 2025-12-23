import sys
import os
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                             QGraphicsScene, QGraphicsPixmapItem, QFileDialog, 
                             QVBoxLayout, QWidget, QToolBar, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QAction, QPen, QWheelEvent, QIcon

from pdf2image import convert_from_path
from PIL import Image

# Modern Style Sheet
STYLESHEET = """
QMainWindow {
    background-color: #2b2b2b;
}
QToolBar {
    background-color: #333333;
    border-bottom: 1px solid #444;
    padding: 5px;
    spacing: 10px;
}
QToolBar QToolButton {
    background-color: #444;
    color: white;
    border-radius: 4px;
    padding: 5px 10px;
}
QToolBar QToolButton:hover {
    background-color: #555;
    border: 1px solid #0078d4;
}
QLabel {
    color: #00d4ff;
    font-weight: bold;
    font-size: 14px;
}
QGraphicsView {
    border: 2px dashed #555;
    background-color: #1e1e1e;
}
"""

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setAcceptDrops(True) # Ensure view accepts drops
        self._parent = parent

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.25
            zoom_out_factor = 1 / zoom_in_factor
            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
        else:
            super().wheelEvent(event)

    # Propagate drag events to main window
    def dragEnterEvent(self, event):
        self._parent.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        self._parent.dragMoveEvent(event)

    def dropEvent(self, event):
        self._parent.dropEvent(event)

class MosaicScene(QGraphicsScene):
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
            # Selection rectangle color: Neon Cyan
            self.current_rect_item = self.addRect(QRectF(self.start_point, self.start_point), 
                                                  QPen(QColor("#00d4ff"), 2), 
                                                  QColor(0, 212, 255, 40))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing and self.current_rect_item:
            current_pos = event.scenePos()
            rect = QRectF(self.start_point, current_pos).normalized()
            self.current_rect_item.setRect(rect)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_drawing and event.button() == Qt.MouseButton.LeftButton:
            self.is_drawing = False
            if self.current_rect_item:
                rect = self.current_rect_item.rect()
                self.removeItem(self.current_rect_item)
                self.current_rect_item = None
                if rect.width() > 5 and rect.height() > 5:
                    self.area_selected.emit(rect)
        super().mouseReleaseEvent(event)


class PDFMosaicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro PDF Mosaic Tool")
        self.resize(1200, 900)
        self.setStyleSheet(STYLESHEET)
        
        # Requirement 1: Global Drag and Drop
        self.setAcceptDrops(True)

        self.pages_images = [] 
        self.current_page_index = 0
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # File Actions
        open_action = QAction("📂 Open PDF", self)
        open_action.triggered.connect(self.open_pdf_dialog)
        self.toolbar.addAction(open_action)

        save_action = QAction("💾 Save PDF", self)
        save_action.triggered.connect(self.save_pdf)
        self.toolbar.addAction(save_action)

        self.toolbar.addSeparator()

        # Zoom Actions
        zoom_in_act = QAction("🔍+", self)
        zoom_in_act.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        self.toolbar.addAction(zoom_in_act)

        zoom_out_act = QAction("🔍-", self)
        zoom_out_act.triggered.connect(lambda: self.view.scale(0.8, 0.8))
        self.toolbar.addAction(zoom_out_act)

        self.toolbar.addSeparator()

        # Navigation
        self.prev_btn = QAction("◀ Prev", self)
        self.prev_btn.triggered.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        self.toolbar.addAction(self.prev_btn)

        self.lbl_page = QLabel(" No PDF Loaded ")
        self.toolbar.addWidget(self.lbl_page)

        self.next_btn = QAction("Next ▶", self)
        self.next_btn.triggered.connect(self.next_page)
        self.next_btn.setEnabled(False)
        self.toolbar.addAction(self.next_btn)

        self.scene = MosaicScene()
        self.scene.area_selected.connect(self.apply_mosaic)
        
        self.view = ZoomableGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        layout.addWidget(self.view)

    # --- DRAG AND DROP HANDLERS ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if f.lower().endswith(".pdf"):
                self.load_pdf(f)
                break 

    def open_pdf_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if fname: self.load_pdf(fname)

    def load_pdf(self, file_path):
        try:
            self.lbl_page.setText(" Rendering High Quality... ")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
            # Requirement 3: Improved Quality (DPI=200 is clear, 300 is crystal but slower)
            self.pages_images = convert_from_path(file_path, dpi=300) 
            
            QApplication.restoreOverrideCursor()
            self.current_page_index = 0
            self.update_display(reset_zoom=True)
            self.update_controls()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Could not load PDF.\nError: {str(e)}")

    def update_display(self, reset_zoom=False):
        if not self.pages_images:
            return
        
        pil_image = self.pages_images[self.current_page_index].convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)
        
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        
        if reset_zoom:
            self.view.resetTransform()
            view_w = self.view.viewport().width()
            scale = view_w / pixmap.width()
            self.view.scale(scale * 0.95, scale * 0.95)

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

    def apply_mosaic(self, rect_f):
        if not self.pages_images:
            return

        pil_img = self.pages_images[self.current_page_index]
        img_w, img_h = pil_img.size

        x1, y1 = max(0, int(rect_f.x())), max(0, int(rect_f.y()))
        x2, y2 = min(img_w, int(rect_f.x() + rect_f.width())), min(img_h, int(rect_f.y() + rect_f.height()))

        w, h = x2 - x1, y2 - y1
        if w <= 1 or h <= 1: return
        
        # Mosaic effect logic
        block_size = 8 
        num_blocks_w = max(1, w // block_size)
        num_blocks_h = max(1, h // block_size)
        
        random_grid = np.random.choice([0, 255], size=(num_blocks_h, num_blocks_w)).astype(np.uint8)
        mosaic_small = Image.fromarray(random_grid, mode='L')
        final_mosaic = mosaic_small.resize((w, h), resample=Image.Resampling.NEAREST)

        final_region = final_mosaic.convert(pil_img.mode)
        pil_img.paste(final_region, (x1, y1, x2, y2))
        
        self.update_display()
        
    def save_pdf(self):
        if not self.pages_images: return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if save_path:
            try:
                # Requirement 3: Ensure saving keeps the quality from the loaded images
                pdf_pages = [img.convert("RGB") for img in self.pages_images]
                pdf_pages[0].save(save_path, "PDF", save_all=True, append_images=pdf_pages[1:], resolution=300.0, quality=95)
                QMessageBox.information(self, "Success", "High Quality PDF Saved!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFMosaicApp()
    window.show()
    sys.exit(app.exec())