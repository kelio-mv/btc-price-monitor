import requests
import pystray
from PIL import Image
import threading
import time
from datetime import datetime
import json
import os

CONFIG_FILENAME = "eth_alarm_config.json"
UPDATE_INTERVAL = 10  # seconds


class EthereumPriceMonitor:
    def __init__(self):
        # Initial configuration
        self.current_price = 0.0
        self.reference_price = 0.0
        self.price_change_threshold = 1.0  # 1%
        self.last_update = ""
        self.running = True
        self.image = Image.open("icon.png")
        self.load_config()

        # Start the price monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_price)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # Create system tray icon
        self.create_tray_icon()

    def load_config(self):
        if os.path.exists(CONFIG_FILENAME):
            try:
                with open(CONFIG_FILENAME, "r") as f:
                    config = json.load(f)
                    self.reference_price = config["reference_price"]
                    self.price_change_threshold = config["price_change_threshold"]
            except:
                # If there's an error loading, use defaults
                pass

    def save_config(self):
        config = {
            "reference_price": self.reference_price,
            "price_change_threshold": self.price_change_threshold,
        }
        with open(CONFIG_FILENAME, "w") as f:
            json.dump(config, f)

    def get_eth_price(self):
        try:
            url = "https://www.okx.com/api/v5/market/ticker?instId=ETH-USDT"
            response = requests.get(url)
            data = response.json()

            if data["code"] == "0":
                self.current_price = float(data["data"][0]["last"])
                self.last_update = datetime.now().strftime("%H:%M:%S")

                # Set reference price on first run if it's zero
                if self.reference_price == 0.0:
                    self.reference_price = self.current_price
                    self.save_config()

                return True

        except Exception as e:
            print(f"Error fetching price: {e}")

        return False

    def calculate_change(self):
        if self.reference_price == 0:
            return 0.0
        return (
            (self.current_price - self.reference_price) / self.reference_price
        ) * 100

    def check_alert_condition(self):
        """Check if price change exceeds threshold"""
        change = self.calculate_change()
        return abs(change) >= self.price_change_threshold

    def monitor_price(self):
        while self.running:
            if self.get_eth_price():
                # Check for alert condition
                if self.check_alert_condition():
                    self.tray_icon.notify(
                        f"Price Alert: ETH changed by {self.calculate_change():.2f}% and is now at ${self.current_price:.2f}!"
                    )
                    # Update reference price to current price when alert triggers
                    self.reference_price = self.current_price
                    self.save_config()

                # Update the tray icon menu
                if hasattr(self, "tray_icon"):
                    self.tray_icon.menu = self.create_tray_menu()

            time.sleep(UPDATE_INTERVAL)

    def create_threshold_menu(self):
        return pystray.Menu(
            pystray.MenuItem("0.5%", lambda icon, item: self.set_alert_threshold(0.5)),
            pystray.MenuItem("1.0%", lambda icon, item: self.set_alert_threshold(1.0)),
            pystray.MenuItem("2.0%", lambda icon, item: self.set_alert_threshold(2.0)),
        )

    def create_tray_menu(self):
        menu_items = [
            pystray.MenuItem(
                (
                    f"ETH Price: ${self.current_price:.2f}"
                    if self.current_price > 0
                    else "Loading price..."
                ),
                lambda icon, item: None,
            ),
            pystray.MenuItem(
                f"Reference: ${self.reference_price:.2f}", lambda icon, item: None
            ),
            pystray.MenuItem(
                f"Change: {self.calculate_change():+.2f}%", lambda icon, item: None
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Set Current as Reference", self.set_current_price_as_reference
            ),
            pystray.MenuItem(
                f"Alert Threshold ({self.price_change_threshold}%)",
                self.create_threshold_menu(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                f"Last Update: {self.last_update}", lambda icon, item: None
            ),
            pystray.MenuItem("Exit", self.exit_program),
        ]
        return pystray.Menu(*menu_items)

    def set_current_price_as_reference(self, icon, item):
        if self.current_price > 0:
            self.reference_price = self.current_price
            self.save_config()
            icon.menu = self.create_tray_menu()

    def set_alert_threshold(self, threshold):
        self.price_change_threshold = threshold
        self.save_config()
        if hasattr(self, "tray_icon"):
            self.tray_icon.menu = self.create_tray_menu()

    def exit_program(self, icon, item):
        self.running = False
        icon.stop()

    def create_tray_icon(self):
        self.tray_icon = pystray.Icon(
            "eth_price_monitor",
            icon=self.image,
            menu=self.create_tray_menu(),
            title="Ethereum Price Monitor",
        )
        self.tray_icon.run()


if __name__ == "__main__":
    monitor = EthereumPriceMonitor()


# Fix the menu bug (kinda hard tho)
