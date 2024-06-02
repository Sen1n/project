import os
import yaml
import time
import threading
from datetime import datetime
from tkinter import *
from tkinter import messagebox
import pyautogui
import schedule
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw


class Settings:
    def __init__(self, user_config="user.yaml", default_config="default.yaml"):
        self.user_config = os.path.join(os.path.dirname(__file__), user_config)
        self.default_config = os.path.join(os.path.dirname(__file__), default_config)
        self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.default_config):
            raise FileNotFoundError(f"Default configuration file '{self.default_config}' not found.")

        self.settings = self.load_default_settings()
        if os.path.exists(self.user_config):
            with open(self.user_config, 'r') as f:
                user_settings = yaml.safe_load(f) or {}
                self.settings.update(user_settings)

        self.interval = self.settings.get("interval", 60)
        self.save_path = self.settings.get("save_path", "screenshots")
        self.specific_time = self.settings.get("specific_time", "14:00")

        if not self._validate_time_format(self.specific_time):
            self.specific_time = "14:00"

        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    def load_default_settings(self):
        with open(self.default_config, 'r') as f:
            return yaml.safe_load(f)

    def save_settings(self):
        user_settings = {
            "interval": self.interval,
            "save_path": self.save_path,
            "specific_time": self.specific_time
        }
        with open(self.user_config, 'w') as f:
            yaml.safe_dump(user_settings, f)

    def _validate_time_format(self, time_str):
        try:
            time.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False


class ScreenshotMaker:
    def __init__(self, settings):
        self.settings = settings

    def take_screenshot(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        screenshot_path = os.path.join(self.settings.save_path, f"screenshot_{timestamp}.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        return screenshot_path


class ScreenshotManager:
    def __init__(self, settings, gui, root):
        self.settings = settings
        self.screenshot_maker = ScreenshotMaker(self.settings)
        self.gui = gui
        self.root = root
        self.running = False

        self.schedule_daily_screenshot()

    def start(self):
        self.running = True
        self._run()

    def stop(self):
        self.running = False

    def _run(self):
        if self.running:
            screenshot_path = self.screenshot_maker.take_screenshot()
            self.gui.update_status(f"Screenshot saved to {screenshot_path}")
            self.root.after(self.settings.interval * 1000, self._run)

    def schedule_daily_screenshot(self):
        if not self.settings._validate_time_format(self.settings.specific_time):
            print("Invalid time format for daily screenshot. Using default time '14:00'.")
            self.settings.specific_time = "14:00"

        schedule.every().day.at(self.settings.specific_time).do(self.screenshot_maker.take_screenshot)

        def run_schedule():
            while True:
                schedule.run_pending()
                time.sleep(1)

        threading.Thread(target=run_schedule, daemon=True).start()


class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screenshot Tool")

        self.settings = Settings()
        self.manager = ScreenshotManager(self.settings, self, root)

        self.interval_label = Label(root, text="Interval (seconds):")
        self.interval_label.pack()

        self.interval_entry = Entry(root)
        self.interval_entry.insert(0, str(self.settings.interval))
        self.interval_entry.pack()

        self.set_interval_button = Button(root, text="Set Interval", command=self.set_interval)
        self.set_interval_button.pack()

        self.specific_time_label = Label(root, text="Specific Time (HH:MM):")
        self.specific_time_label.pack()

        self.specific_time_entry = Entry(root)
        self.specific_time_entry.insert(0, self.settings.specific_time)
        self.specific_time_entry.pack()

        self.set_specific_time_button = Button(root, text="Set Specific Time", command=self.set_specific_time)
        self.set_specific_time_button.pack()

        self.screenshot_button = Button(root, text="Take Screenshot", command=self.take_screenshot)
        self.screenshot_button.pack()

        self.start_button = Button(root, text="Start Automatic Screenshots", command=self.start_screenshots)
        self.start_button.pack()

        self.stop_button = Button(root, text="Stop Automatic Screenshots", command=self.stop_screenshots)
        self.stop_button.pack()

        self.status_label = Label(root, text="Status: Ready")
        self.status_label.pack()

        # Закрити на хрестик - заховати в трей
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.create_tray_icon()

    def set_interval(self):
        try:
            interval = int(self.interval_entry.get())
            self.settings.interval = interval
            self.settings.save_settings()
            messagebox.showinfo("Info", f"Interval set to {interval} seconds")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def set_specific_time(self):
        specific_time = self.specific_time_entry.get()
        if self.settings._validate_time_format(specific_time):
            self.settings.specific_time = specific_time
            self.settings.save_settings()
            self.manager.schedule_daily_screenshot()  # Reschedule the daily screenshot with the new time
            messagebox.showinfo("Info", f"Specific time set to {specific_time}")
        else:
            messagebox.showerror("Error", "Please enter a valid time format (HH:MM)")

    def take_screenshot(self):
        screenshot_path = self.manager.screenshot_maker.take_screenshot()
        self.update_status(f"Screenshot saved to {screenshot_path}")

    def start_screenshots(self):
        self.manager.start()
        self.update_status("Automatic screenshots started")

    def stop_screenshots(self):
        self.manager.stop()
        self.update_status("Automatic screenshots stopped")

    def update_status(self, message):
        self.status_label.config(text=f"Status: {message}")

    def hide_window(self):
        self.root.withdraw()
        self.show_message("Screenshot Tool", "Running in background. Right-click the tray icon to exit.")

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 64, 64), fill=(0, 0, 0))

        self.tray_icon = pystray.Icon("screenshot_tool", image, "Screenshot Tool", menu=pystray.Menu(
            item('Show', self.show_window),
            item('Exit', self.exit_app)
        ))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.root.deiconify()

    def exit_app(self):
        self.tray_icon.stop()
        self.root.destroy()

    def show_message(self, title, message):
        self.tray_icon.notify(message, title)


if __name__ == "__main__":
    root = Tk()
    app = ScreenshotApp(root)
    root.mainloop()
