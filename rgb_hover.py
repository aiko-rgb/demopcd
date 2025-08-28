import sys
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame
)
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

# --- BARU: Subclass QLabel untuk mendeteksi hover mouse ---
class InteractiveImageLabel(QLabel):
    # Definisikan sinyal kustom. 
    # Satu untuk mengirim info warna, satu lagi untuk saat mouse keluar.
    pixel_info_signal = pyqtSignal(QColor, QPoint)
    mouse_left_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.original_pixmap_ref = None

    def set_original_pixmap(self, pixmap):
        """Simpan referensi ke pixmap asli untuk perhitungan koordinat."""
        self.original_pixmap_ref = pixmap

    def mouseMoveEvent(self, event):
        """Dipanggil setiap kali mouse bergerak di atas label ini."""
        # Jika tidak ada gambar, jangan lakukan apa-apa
        if self.pixmap() is None or self.original_pixmap_ref is None:
            return

        # Dapatkan posisi mouse relatif terhadap label
        label_pos = event.position()

        # --- Logika Kunci: Konversi koordinat label ke koordinat gambar asli ---
        # 1. Dapatkan ukuran label dan gambar yang ditampilkan (scaled pixmap)
        label_size = self.size()
        pixmap_size = self.pixmap().size()

        # 2. Hitung offset (area kosong/letterboxing) karena gambar di-center
        offset_x = (label_size.width() - pixmap_size.width()) / 2
        offset_y = (label_size.height() - pixmap_size.height()) / 2

        # 3. Hitung posisi mouse relatif terhadap gambar yang ditampilkan
        img_pos_x = label_pos.x() - offset_x
        img_pos_y = label_pos.y() - offset_y

        # 4. Periksa apakah mouse berada di dalam batas gambar (bukan di area kosong)
        if 0 <= img_pos_x < pixmap_size.width() and 0 <= img_pos_y < pixmap_size.height():
            # 5. Konversi koordinat dari gambar yang di-skala ke gambar asli
            original_size = self.original_pixmap_ref.size()
            
            scale_ratio_w = original_size.width() / pixmap_size.width()
            scale_ratio_h = original_size.height() / pixmap_size.height()

            original_x = int(img_pos_x * scale_ratio_w)
            original_y = int(img_pos_y * scale_ratio_h)

            # 6. Ambil warna piksel dari gambar asli (via QImage)
            image = self.original_pixmap_ref.toImage()
            color = image.pixelColor(original_x, original_y)

            # 7. Kirim sinyal dengan informasi warna dan koordinat
            self.pixel_info_signal.emit(color, QPoint(original_x, original_y))
        else:
            # Jika mouse di area kosong, kirim sinyal 'mouse left' untuk clear status bar
            self.mouse_left_signal.emit()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Dipanggil saat mouse meninggalkan area label."""
        self.mouse_left_signal.emit()
        super().leaveEvent(event)
# --- Akhir dari class baru ---


class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Viewer - Hover Info & Grayscale Channels")
        self.setGeometry(100, 100, 900, 900)

        self.original_pixmap = None
        self.initUI()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- BARU: Gunakan class InteractiveImageLabel yang kita buat ---
        self.image_label = InteractiveImageLabel("Pilih gambar untuk melihat komponen R, G, B-nya.")
        # ---
        
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(300, 300)
        self.image_label.setStyleSheet("QLabel { border: 2px dashed #aaa; color: #888; }")
        main_layout.addWidget(self.image_label, 1)

        # ... (Kode untuk channel grayscale tetap sama) ...
        channels_container = QWidget()
        channels_layout = QHBoxLayout(channels_container)
        channels_layout.setContentsMargins(0, 10, 0, 5)
        self.red_channel_label = self.create_channel_widget(channels_layout, "Red Channel (Grayscale)")
        self.green_channel_label = self.create_channel_widget(channels_layout, "Green Channel (Grayscale)")
        self.blue_channel_label = self.create_channel_widget(channels_layout, "Blue Channel (Grayscale)")
        main_layout.addWidget(channels_container)

        self.load_button = QPushButton("Load Gambar")
        main_layout.addWidget(self.load_button)

        # --- BARU: Inisialisasi status bar ---
        self.statusBar().showMessage("Arahkan mouse ke gambar untuk melihat nilai piksel.")

        # --- BARU: Hubungkan sinyal dari label kustom ke slot di window utama ---
        self.load_button.clicked.connect(self.load_image)
        self.image_label.pixel_info_signal.connect(self.update_pixel_info)
        self.image_label.mouse_left_signal.connect(self.clear_pixel_info)

    # ... (create_channel_widget tetap sama) ...
    def create_channel_widget(self, parent_layout, title):
        widget = QWidget()
        layout = QVBoxLayout(widget); layout.setContentsMargins(5,0,5,0)
        title_label = QLabel(f"<b>{title}</b>"); title_label.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(title_label)
        image_label = QLabel(); image_label.setFrameShape(QFrame.Shape.StyledPanel); image_label.setMinimumSize(200, 200); image_label.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(image_label)
        parent_layout.addWidget(widget)
        return image_label

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Gambar", "", "File Gambar (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.original_pixmap = QPixmap(file_path)
            if self.original_pixmap.isNull():
                self.image_label.setText("Gagal memuat gambar.")
                self.original_pixmap = None
                self.image_label.set_original_pixmap(None) # --- BARU: Reset referensi
                self.clear_channel_images()
            else:
                self.image_label.setStyleSheet("")
                # --- BARU: Berikan referensi pixmap asli ke label kustom kita ---
                self.image_label.set_original_pixmap(self.original_pixmap)
                # ---
                self.update_image_display()
                self.process_and_display_channels()
                self.clear_pixel_info()

    # ... (Fungsi lain tetap sama) ...
    def update_image_display(self):
        if self.original_pixmap is None: return
        label_size = self.image_label.size()
        image_size = self.original_pixmap.size()
        if image_size.width() > label_size.width() or image_size.height() > label_size.height():
            scaled_pixmap = self.original_pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            scaled_pixmap = self.original_pixmap
        self.image_label.setPixmap(scaled_pixmap)

    def process_and_display_channels(self):
        if self.original_pixmap is None: return
        qimage = self.original_pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())
        arr = np.array(ptr).reshape(qimage.height(), qimage.width(), 4)
        grayscale_template = np.zeros_like(arr); grayscale_template[:, :, 3] = 255
        red_channel_data = arr[:, :, 2]; red_grayscale = grayscale_template.copy(); red_grayscale[:, :, 0:3] = red_channel_data[:, :, np.newaxis]
        green_channel_data = arr[:, :, 1]; green_grayscale = grayscale_template.copy(); green_grayscale[:, :, 0:3] = green_channel_data[:, :, np.newaxis]
        blue_channel_data = arr[:, :, 0]; blue_grayscale = grayscale_template.copy(); blue_grayscale[:, :, 0:3] = blue_channel_data[:, :, np.newaxis]
        self.display_channel_image(red_grayscale, self.red_channel_label)
        self.display_channel_image(green_grayscale, self.green_channel_label)
        self.display_channel_image(blue_grayscale, self.blue_channel_label)
    
    def display_channel_image(self, arr, label):
        height, width, _ = arr.shape
        bytes_per_line = 4 * width
        qimage = QImage(arr.data.tobytes(), width, height, bytes_per_line, QImage.Format.Format_ARGB32)
        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled_pixmap)

    def clear_channel_images(self):
        self.red_channel_label.clear(); self.green_channel_label.clear(); self.blue_channel_label.clear()

    # --- BARU: Slot untuk menangani sinyal dari label kustom ---
    def update_pixel_info(self, color, pos):
        """Slot yang dipanggil saat mouse bergerak di atas gambar."""
        if color.isValid():
            info_text = (
                f"Pos: ({pos.x()}, {pos.y()}) | "
                f"RGB: ({color.red()}, {color.green()}, {color.blue()})"
            )
            self.statusBar().showMessage(info_text)

    def clear_pixel_info(self):
        """Slot yang dipanggil saat mouse meninggalkan gambar."""
        self.statusBar().showMessage("Arahkan mouse ke gambar untuk melihat nilai piksel.")

    def resizeEvent(self, event):
        self.update_image_display()
        super().resizeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageViewer()
    window.show()
    sys.exit(app.exec())