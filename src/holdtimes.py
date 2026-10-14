import sys
import time
import queue
from collections import defaultdict
import configparser
import os
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from pynput import keyboard

# --- Default Configurable Constants ---
DEFAULTS = {
    'keys': 'z,x',  # Comma-separated list of keys
    'BIN_WIDTH': '4',
    'MAX_AGE': '5',
    'LONG_HOLD_FADE': '1',
    'LONG_HOLD_THRESHOLD': '100',
    'SMOOTH_ALPHA': '0.1',
    'RESET_KEY': 'r',
    'NO_DECAY': 'False',
    'Y_AXIS_BASE': '10',
    'X_AXIS_STARTS_AT_ZERO': 'True',
    'COLORS': '0,0,255:255,0,0',  # Colon-separated list of RGB colors
    'WINDOW_WIDTH': '800',
    'WINDOW_HEIGHT': '400',
    'BACKGROUND_COLOR': '30,30,30'  # New default background color (dark gray)
}

SETTINGS_FILE = 'settings.ini'

# --- Global state ---
hold_times_queue = queue.Queue()
press_times = {}


class ColorButton(QtWidgets.QPushButton):
    def __init__(self, initial_color, parent=None):
        super().__init__(parent)
        self.set_color(initial_color)
        self.clicked.connect(self.choose_color)
        
    def set_color(self, color):
        self.color = color
        self.setStyleSheet(f"background-color: rgb({color}); border: 1px solid black;")
        
    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.set_color(f"{color.red()},{color.green()},{color.blue()}")

class KeySettingsWidget(QtWidgets.QWidget):
    def __init__(self, key='', color='0,0,255', parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        
        self.key_edit = QtWidgets.QLineEdit(key)
        self.key_edit.setMaxLength(1)
        self.color_btn = ColorButton(color)
        
        layout.addWidget(QtWidgets.QLabel("Key:"))
        layout.addWidget(self.key_edit)
        layout.addWidget(QtWidgets.QLabel("Color:"))
        layout.addWidget(self.color_btn)
        layout.addStretch()

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("Settings - Select Keys & Constants")
        self.setFixedSize(450, 600)  # Increased size for additional field

        layout = QtWidgets.QVBoxLayout()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(content)
        
        # Parse keys and colors
        keys = settings.get('keys', DEFAULTS['keys']).split(',')
        colors = settings.get('COLORS', DEFAULTS['COLORS']).split(':')
        
        # Ensure we have enough colors
        while len(colors) < len(keys):
            colors.append(f"{QtGui.QColor().red()},{QtGui.QColor().green()},{QtGui.QColor().blue()}")
        
        # Key settings widgets
        self.key_widgets = []
        for i, (key, color) in enumerate(zip(keys, colors)):
            widget = KeySettingsWidget(key, color)
            self.key_widgets.append(widget)
            form.addRow(f"Key {i+1}:", widget)
        
        # Add/remove key buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.add_btn = QtWidgets.QPushButton("Add Key")
        self.add_btn.clicked.connect(self.add_key)
        self.remove_btn = QtWidgets.QPushButton("Remove Key")
        self.remove_btn.clicked.connect(self.remove_key)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        form.addRow(btn_layout)

        # Add background color selector
        self.bg_color_btn = ColorButton(settings.get('BACKGROUND_COLOR', DEFAULTS['BACKGROUND_COLOR']))
        form.addRow("Background Color:", self.bg_color_btn)

        # Reset key field
        self.reset_key = QtWidgets.QLineEdit(settings.get('RESET_KEY', DEFAULTS['RESET_KEY']))
        self.reset_key.setMaxLength(1)
        form.addRow("Reset Graph Hotkey:", self.reset_key)

        # Numeric fields for constants
        self.bin_width = QtWidgets.QLineEdit(settings.get('BIN_WIDTH', DEFAULTS['BIN_WIDTH']))
        self.max_age = QtWidgets.QLineEdit(settings.get('MAX_AGE', DEFAULTS['MAX_AGE']))
        self.long_hold_fade = QtWidgets.QLineEdit(settings.get('LONG_HOLD_FADE', DEFAULTS['LONG_HOLD_FADE']))
        self.long_hold_threshold = QtWidgets.QLineEdit(settings.get('LONG_HOLD_THRESHOLD', DEFAULTS['LONG_HOLD_THRESHOLD']))
        self.smooth_alpha = QtWidgets.QLineEdit(settings.get('SMOOTH_ALPHA', DEFAULTS['SMOOTH_ALPHA']))
        self.y_axis_base = QtWidgets.QLineEdit(settings.get('Y_AXIS_BASE', DEFAULTS['Y_AXIS_BASE']))
        self.window_width = QtWidgets.QLineEdit(settings.get('WINDOW_WIDTH', DEFAULTS['WINDOW_WIDTH']))
        self.window_height = QtWidgets.QLineEdit(settings.get('WINDOW_HEIGHT', DEFAULTS['WINDOW_HEIGHT']))

        form.addRow("Bin Width (ms):", self.bin_width)
        form.addRow("Max Age (s):", self.max_age)
        form.addRow("Long Hold Fade (s):", self.long_hold_fade)
        form.addRow("Long Hold Threshold (ms):", self.long_hold_threshold)
        form.addRow("Smooth Alpha (0-1):", self.smooth_alpha)
        form.addRow("Y-Axis Base for Scaling:", self.y_axis_base)
        form.addRow("Default Window Width:", self.window_width)
        form.addRow("Default Window Height:", self.window_height)

        # Checkbox for No Decay
        self.no_decay_checkbox = QtWidgets.QCheckBox()
        no_decay_val = settings.get('NO_DECAY', DEFAULTS['NO_DECAY']).lower() == 'true'
        self.no_decay_checkbox.setChecked(no_decay_val)
        form.addRow("No Decay (disable fade):", self.no_decay_checkbox)

        # Checkbox for X axis start at zero
        self.x_axis_zero_checkbox = QtWidgets.QCheckBox()
        x_axis_zero_val = settings.get('X_AXIS_STARTS_AT_ZERO', DEFAULTS['X_AXIS_STARTS_AT_ZERO']).lower() == 'true'
        self.x_axis_zero_checkbox.setChecked(x_axis_zero_val)
        form.addRow("X-Axis Always Starts at 0:", self.x_axis_zero_checkbox)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
    
    def add_key(self):
        widget = KeySettingsWidget()
        self.key_widgets.append(widget)
        form_layout = self.layout().itemAt(0).widget().widget().layout()
        form_layout.insertRow(len(self.key_widgets) - 1, f"Key {len(self.key_widgets)}:", widget)
    
    def remove_key(self):
        if len(self.key_widgets) > 1:  # Keep at least one key
            widget = self.key_widgets.pop()
            form_layout = self.layout().itemAt(0).widget().widget().layout()
            
            # Remove the row before buttons (which is the last key row)
            form_layout.removeRow(len(self.key_widgets))
            
            # Update the numbering of remaining keys
            for i in range(len(self.key_widgets)):
                label_item = form_layout.itemAt(i, QtWidgets.QFormLayout.LabelRole)
                if label_item:
                    label_item.widget().setText(f"Key {i+1}:")

    def get_settings(self):
        keys = []
        colors = []
        for widget in self.key_widgets:
            key = widget.key_edit.text().lower()
            if key:  # Only add if key is not empty
                keys.append(key)
                colors.append(widget.color_btn.color)
        
        return {
            'keys': ','.join(keys),
            'COLORS': ':'.join(colors),
            'BACKGROUND_COLOR': self.bg_color_btn.color,
            'RESET_KEY': self.reset_key.text().lower(),
            'BIN_WIDTH': self.bin_width.text(),
            'MAX_AGE': self.max_age.text(),
            'LONG_HOLD_FADE': self.long_hold_fade.text(),
            'LONG_HOLD_THRESHOLD': self.long_hold_threshold.text(),
            'SMOOTH_ALPHA': self.smooth_alpha.text(),
            'NO_DECAY': str(self.no_decay_checkbox.isChecked()),
            'Y_AXIS_BASE': self.y_axis_base.text(),
            'X_AXIS_STARTS_AT_ZERO': str(self.x_axis_zero_checkbox.isChecked()),
            'WINDOW_WIDTH': self.window_width.text(),
            'WINDOW_HEIGHT': self.window_height.text()
        }

class KeyHoldPlot(QtWidgets.QMainWindow):
    settings_changed = QtCore.pyqtSignal(dict)
    
    def __init__(self, keys, colors, bin_width, max_age, long_hold_fade, long_hold_threshold,
                 smooth_alpha, reset_key, no_decay, y_axis_base, x_axis_starts_at_zero, bg_color):
        super().__init__()
        self.keys = keys
        self.selected_keys = set(keys)
        self.setWindowTitle(" vs ".join(k.upper() for k in keys) + " Hold Times")
        
        # Load saved window size or use defaults
        config = load_settings()
        settings = config['Settings']
        width = int(settings.get('WINDOW_WIDTH', DEFAULTS['WINDOW_WIDTH']))
        height = int(settings.get('WINDOW_HEIGHT', DEFAULTS['WINDOW_HEIGHT']))
        self.resize(width, height)

        self.BIN_WIDTH = bin_width
        self.MAX_AGE = max_age
        self.LONG_HOLD_FADE = long_hold_fade
        self.LONG_HOLD_THRESHOLD = long_hold_threshold
        self.SMOOTH_ALPHA = smooth_alpha
        self.RESET_KEY = reset_key
        self.NO_DECAY = no_decay
        self.Y_AXIS_BASE = y_axis_base
        self.X_AXIS_STARTS_AT_ZERO = x_axis_starts_at_zero
        
        # Parse colors
        self.key_colors = []
        for color in colors:
            rgb = color.split(',')
            if len(rgb) == 3:
                self.key_colors.append(tuple(map(int, rgb)) + (150,))
            else:
                self.key_colors.append((0, 0, 255, 150))  # Default blue
        
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        
        # Set background color
        bg_rgb = tuple(map(int, bg_color.split(',')))
        self.plot_widget.setBackground(QtGui.QColor(*bg_rgb))
        
        # Set axis colors based on background brightness
        brightness = sum(bg_rgb)/3
        text_color = 'k' if brightness > 128 else 'w'
        self.plot_widget.setLabel('bottom', 'Hold Time (ms)', color=text_color, **{'font-size': '14pt'})
        self.plot_widget.setLabel('left', 'Count', color=text_color, **{'font-size': '14pt'})
        self.plot_widget.getAxis('bottom').setPen(text_color)
        self.plot_widget.getAxis('left').setPen(text_color)
        self.plot_widget.showGrid(x=False, y=False, alpha=0.5)

        self.data = []
        self.avgs = [0.0] * len(keys)
        self.timestamps = [[] for _ in keys]

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)

        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

        reset_btn = QtWidgets.QPushButton("Reset Graph")
        reset_btn.clicked.connect(self.reset_data)
        toolbar = self.addToolBar("Controls")
        toolbar.addWidget(reset_btn)

        # Connect the settings changed signal
        self.settings_changed.connect(self.update_settings)

    def update_settings(self, new_settings):
        """Update the plot with new settings"""
        new_keys = new_settings.get('keys', '').split(',')
        new_colors = new_settings.get('COLORS', '').split(':')
        
        # Only update if keys have actually changed
        if set(new_keys) != set(self.keys):
            self.keys = new_keys
            self.selected_keys = set(new_keys)
            self.setWindowTitle(" vs ".join(k.upper() for k in new_keys) + " Hold Times")
            
            # Update colors
            self.key_colors = []
            for color in new_colors:
                rgb = color.split(',')
                if len(rgb) == 3:
                    self.key_colors.append(tuple(map(int, rgb)) + (150,))
                else:
                    self.key_colors.append((0, 0, 255, 150))  # Default blue
            
            # Reset data when keys change
            self.reset_data()

    def closeEvent(self, event):
        # Save window size when closing
        config = load_settings()
        config['Settings']['WINDOW_WIDTH'] = str(self.width())
        config['Settings']['WINDOW_HEIGHT'] = str(self.height())
        save_settings(config['Settings'])
        super().closeEvent(event)

    def on_press(self, key):
        try:
            c = key.char.lower()
        except:
            return

        if c == self.RESET_KEY:
            self.reset_data()
            return

        if c in self.selected_keys and c not in press_times:
            press_times[c] = time.perf_counter()

    def on_release(self, key):
        try:
            c = key.char.lower()
        except:
            return
        if c in self.selected_keys and c in press_times:
            duration = (time.perf_counter() - press_times[c]) * 1000
            hold_times_queue.put((c, duration))
            del press_times[c]

            now = time.perf_counter()
            if c in self.keys:
                idx = self.keys.index(c)
                self.timestamps[idx].append(now)

    def reset_data(self):
        self.data.clear()
        for ts in self.timestamps:
            ts.clear()
        press_times.clear()

    def update_plot(self):
        now = time.perf_counter()

        # Live CPS
        live_cps = []
        for i in range(len(self.keys)):
            self.timestamps[i] = [t for t in self.timestamps[i] if t >= now - 1.0]
            live_cps.append(len(self.timestamps[i]))

        while not hold_times_queue.empty():
            k, t = hold_times_queue.get()
            self.data.append((k, t, now))

        # Prune old data if decay is enabled
        if not self.NO_DECAY:
            self.data = [(k, t, ts) for (k, t, ts) in self.data if now - ts <= self.MAX_AGE]

        # Initialize bins and stats for each key
        bins = [defaultdict(float) for _ in self.keys]
        total_weights = [0.0] * len(self.keys)
        weighted_sums = [0.0] * len(self.keys)

        for k, t, ts in self.data:
            age = now - ts
            fade_time = self.LONG_HOLD_FADE if t > self.LONG_HOLD_THRESHOLD else self.MAX_AGE
            weight = 1.0 if self.NO_DECAY else max(0, 1 - age / fade_time)
            if weight <= 0:
                continue

            bin_index = int((t + self.BIN_WIDTH / 2) // self.BIN_WIDTH) * self.BIN_WIDTH

            if k in self.keys:
                idx = self.keys.index(k)
                bins[idx][bin_index] += weight
                total_weights[idx] += weight
                weighted_sums[idx] += t * weight

        self.plot_widget.clear()

        width = self.BIN_WIDTH * 1.5
        all_bins = []
        
        # Plot bars for each key
        for i, (bin_data, color) in enumerate(zip(bins, self.key_colors)):
            x, y = zip(*sorted(bin_data.items())) if bin_data else ([], [])
            if x:
                bar = pg.BarGraphItem(x=x, height=y, width=width, brush=color)
                self.plot_widget.addItem(bar)
                all_bins.extend(x)

        # Set X range
        if self.X_AXIS_STARTS_AT_ZERO:
            min_x = 0
        else:
            min_x = min(all_bins) if all_bins else 0
        max_x = max(all_bins) + self.BIN_WIDTH if all_bins else 100
        self.plot_widget.setXRange(min_x, max_x)

        # Handle Y axis scaling based on base
        max_y_val = max([max(bin.values()) for bin in bins if bin] + [0])
        y_base = self.Y_AXIS_BASE

        if max_y_val < y_base:
            self.plot_widget.setYRange(0, y_base)
        else:
            self.plot_widget.setYRange(0, max_y_val * 1.2)

        # Update smoothed averages and draw labels
        view_range = self.plot_widget.viewRange()
        x_max = view_range[0][1]
        y_max = view_range[1][1]
        text_font = QtGui.QFont('Arial', 12, QtGui.QFont.Bold)

        for i in range(len(self.keys)):
            # Update average
            avg = weighted_sums[i] / total_weights[i] if total_weights[i] > 0 else 0
            self.avgs[i] = self.SMOOTH_ALPHA * avg + (1 - self.SMOOTH_ALPHA) * self.avgs[i]
            
            # Create label
            key_color = QtGui.QColor(*self.key_colors[i][:3])
            label = pg.TextItem(
                f"{self.keys[i].upper()} Avg: {self.avgs[i]:.1f} ms ({live_cps[i]} CPS)",
                anchor=(1, 0), color=key_color
            )
            label.setFont(text_font)
            label.setPos(x_max, y_max * (0.92 ** i))  # Stack labels vertically
            self.plot_widget.addItem(label)

def load_settings():
    config = configparser.ConfigParser()
    if not os.path.exists(SETTINGS_FILE):
        config['Settings'] = DEFAULTS
        with open(SETTINGS_FILE, 'w') as f:
            config.write(f)
    else:
        config.read(SETTINGS_FILE)
        if 'Settings' not in config:
            config['Settings'] = DEFAULTS
        for k, v in DEFAULTS.items():
            if k not in config['Settings']:
                config['Settings'][k] = v
    return config

def save_settings(settings_dict):
    config = configparser.ConfigParser()
    config['Settings'] = settings_dict
    with open(SETTINGS_FILE, 'w') as f:
        config.write(f)

def main():
    config = load_settings()
    settings = config['Settings']

    app = QtWidgets.QApplication(sys.argv)
    dialog = SettingsDialog(settings)
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        sys.exit()

    new_settings = dialog.get_settings()
    save_settings(new_settings)

    def parse_float(key, fallback):
        try:
            return float(new_settings.get(key, fallback))
        except:
            return fallback

    def parse_int(key, fallback):
        try:
            return int(float(new_settings.get(key, fallback)))
        except:
            return fallback

    keys = new_settings.get('keys', DEFAULTS['keys']).split(',')
    colors = new_settings.get('COLORS', DEFAULTS['COLORS']).split(':')
    reset_key = new_settings.get('RESET_KEY', DEFAULTS['RESET_KEY'])
    bin_width = parse_int('BIN_WIDTH', int(DEFAULTS['BIN_WIDTH']))
    max_age = parse_float('MAX_AGE', float(DEFAULTS['MAX_AGE']))
    long_hold_fade = parse_float('LONG_HOLD_FADE', float(DEFAULTS['LONG_HOLD_FADE']))
    long_hold_threshold = parse_int('LONG_HOLD_THRESHOLD', int(DEFAULTS['LONG_HOLD_THRESHOLD']))
    smooth_alpha = parse_float('SMOOTH_ALPHA', float(DEFAULTS['SMOOTH_ALPHA']))
    smooth_alpha = max(0.0, min(smooth_alpha, 1.0))
    no_decay = new_settings.get('NO_DECAY', DEFAULTS['NO_DECAY']).lower() == 'true'
    y_axis_base = parse_int('Y_AXIS_BASE', int(DEFAULTS['Y_AXIS_BASE']))
    x_axis_starts_at_zero = new_settings.get('X_AXIS_STARTS_AT_ZERO', DEFAULTS['X_AXIS_STARTS_AT_ZERO']).lower() == 'true'
    bg_color = new_settings.get('BACKGROUND_COLOR', DEFAULTS['BACKGROUND_COLOR'])

    window = KeyHoldPlot(keys, colors, bin_width, max_age, long_hold_fade,
                         long_hold_threshold, smooth_alpha, reset_key,
                         no_decay, y_axis_base, x_axis_starts_at_zero, bg_color)
    window.show()
    
    # Emit the signal with the new settings
    window.settings_changed.emit(new_settings)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()