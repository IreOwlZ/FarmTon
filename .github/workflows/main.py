import requests
import json
import urllib.parse
import time
import threading
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich import box
from datetime import datetime

console = Console()

# الروابط الأساسية للـ API
BASE_URL = "https://farmton.auto-crypto.click/api"
ENDPOINTS = {
    "login": f"{BASE_URL}/login?ref=undefined",
    "user_me": f"{BASE_URL}/user/me",
    "crop_states": f"{BASE_URL}/crop/states",
    "plant": f"{BASE_URL}/crop/plant",
    "water": f"{BASE_URL}/crop/water",
    "harvest": f"{BASE_URL}/crop/harvest",
    "buy_seeds": f"{BASE_URL}/market/buy-seeds",
    "buy_water": f"{BASE_URL}/market/buy-water",
    "sell_wheat": f"{BASE_URL}/market/sell-wheat"
}

# الرؤوس (headers)
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "referer": "https://farmton.auto-crypto.click/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

class FarmtonAccount:
    def __init__(self, account_id, init_data):
        self.account_id = account_id
        self.init_data = init_data
        self.status = "Initializing"
        self.coins = 0
        self.seeds = 0
        self.water = 0
        self.wheat = 0
        self.plots = [{"state": "unknown", "timer": 0} for _ in range(9)]
        self.last_update = datetime.now().strftime("%H:%M:%S")
        self.headers = HEADERS.copy()
        self.setup_headers()

    def setup_headers(self):
        """إعداد headers مع Telegram data"""
        try:
            init_data_unsafe = self.parse_init_data(self.init_data)
            if init_data_unsafe:
                telegram_data = {
                    "initData": self.init_data,
                    "initDataUnsafe": init_data_unsafe
                }
                self.headers["x-window-telegram"] = json.dumps(telegram_data)
                return True
        except Exception as e:
            self.status = f"Invalid Data: {str(e)[:20]}"
        return False

    def parse_init_data(self, init_data):
        """فك تشفير initData"""
        parsed = urllib.parse.parse_qs(init_data)
        return {
            "query_id": parsed.get("query_id", [""])[0],
            "user": json.loads(urllib.parse.unquote(parsed.get("user", [""])[0])),
            "auth_date": parsed.get("auth_date", [""])[0],
            "signature": parsed.get("signature", [""])[0],
            "hash": parsed.get("hash", [""])[0]
        }

    def make_request(self, method, url, data=None):
        """إرسال طلب HTTP"""
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            else:
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            return response
        except Exception as e:
            return None

    def login(self):
        """تسجيل الدخول"""
        response = self.make_request("GET", ENDPOINTS["login"])
        return response and response.status_code == 200

    def update_user_data(self):
        """تحديث بيانات المستخدم"""
        response = self.make_request("GET", ENDPOINTS["user_me"])
        if response and response.status_code == 200:
            data = response.json().get("data", {})
            self.coins = data.get("coins", 0)
            self.seeds = data.get("seeds", 0)
            self.water = data.get("water", 0)
            self.wheat = data.get("wheat", 0)
            return True
        return False

    def update_crop_states(self):
        """تحديث حالة الأراضي"""
        response = self.make_request("GET", ENDPOINTS["crop_states"])
        if response and response.status_code == 200:
            crop_data = response.json()
            for plot_data in crop_data:
                plot_index = plot_data.get("plotIndex", 0)
                if 0 <= plot_index <= 8:
                    self.plots[plot_index] = {
                        "state": plot_data.get("state", "unknown"),
                        "timer": plot_data.get("timerRemaining", 0)
                    }
            return True
        return False

    def buy_seeds(self, amount):
        """شراء البذور"""
        response = self.make_request("POST", ENDPOINTS["buy_seeds"], {"amount": amount})
        if response and response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                user_data = result.get("user", {})
                self.coins = user_data.get("coins", self.coins)
                self.seeds = user_data.get("seeds", self.seeds)
                return True
        return False

    def buy_water(self, amount):
        """شراء الماء"""
        response = self.make_request("POST", ENDPOINTS["buy_water"], {"amount": amount})
        if response and response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                user_data = result.get("user", {})
                self.coins = user_data.get("coins", self.coins)
                self.water = user_data.get("water", self.water)
                return True
        return False

    def plant_plot(self, plot_index):
        """زراعة قطعة أرض"""
        response = self.make_request("POST", ENDPOINTS["plant"], {"plotIndex": plot_index})
        if response and response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                user_data = result.get("user", {})
                self.seeds = user_data.get("seeds", self.seeds)
                return True
        return False

    def water_plot(self, plot_index):
        """ري قطعة أرض"""
        response = self.make_request("POST", ENDPOINTS["water"], {"plotIndex": plot_index})
        if response and response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                user_data = result.get("user", {})
                self.water = user_data.get("water", self.water)
                return True
        return False

    def harvest_plot(self, plot_index):
        """حصاد قطعة أرض"""
        response = self.make_request("POST", ENDPOINTS["harvest"], {"plotIndex": plot_index})
        if response and response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                user_data = result.get("user", {})
                self.wheat = user_data.get("wheat", self.wheat)
                return True
        return False

    def sell_wheat(self):
        """بيع القمح"""
        if self.wheat > 0:
            response = self.make_request("POST", ENDPOINTS["sell_wheat"], {"amount": self.wheat})
            if response and response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    user_data = result.get("user", {})
                    self.coins = user_data.get("coins", self.coins)
                    self.wheat = user_data.get("wheat", self.wheat)
                    return True
        return False

    def process_plots(self):
        """معالجة جميع الأراضي"""
        actions_taken = False

        # معالجة كل قطعة أرض حسب حالتها
        for plot_index in range(9):
            plot = self.plots[plot_index]
            state = plot["state"]
            timer = plot["timer"]

            if state == "waiting_harvest" and timer == 0:
                # حصاد
                if self.harvest_plot(plot_index):
                    actions_taken = True

            elif state == "waiting_water" and timer == 0:
                # التأكد من توفر الماء
                if self.water < 1:
                    amount_needed = 9 - self.water
                    cost = amount_needed * 15
                    if self.coins >= cost:
                        self.buy_water(amount_needed)

                if self.water >= 1:
                    if self.water_plot(plot_index):
                        actions_taken = True

            elif state == "empty" and timer == 0:
                # التأكد من توفر البذور
                if self.seeds < 1:
                    amount_needed = 9 - self.seeds
                    cost = amount_needed * 5
                    if self.coins >= cost:
                        self.buy_seeds(amount_needed)

                if self.seeds >= 1:
                    if self.plant_plot(plot_index):
                        actions_taken = True

        # بيع القمح المتراكم
        if self.wheat > 0:
            self.sell_wheat()
            actions_taken = True

        return actions_taken

    def run_cycle(self):
        """تشغيل دورة كاملة للحساب"""
        # تسجيل الدخول
        if not self.login():
            self.status = "Login Failed"
            return

        # تحديث البيانات
        if not self.update_user_data():
            self.status = "Data Update Failed"
            return

        if not self.update_crop_states():
            self.status = "Crop States Failed"
            return

        # معالجة الأراضي
        actions_taken = self.process_plots()

        # إذا تم اتخاذ إجراءات، انتظر 30 ثانية ثم حدث البيانات
        if actions_taken:
            self.status = "Processing..."
            time.sleep(30)
            self.update_crop_states()
            self.update_user_data()

        self.status = "Active"
        self.last_update = datetime.now().strftime("%H:%M:%S")

class FarmtonBot:
    def __init__(self):
        self.accounts = []
        self.running = True
        self.load_accounts()

    def load_accounts(self):
        """تحميل الحسابات من ملف data.txt"""
        try:
            with open("data.txt", "r", encoding="utf-8") as file:
                init_data_list = file.read().splitlines()

            for i, init_data in enumerate(init_data_list, 1):
                if init_data.strip():
                    account = FarmtonAccount(i, init_data.strip())
                    self.accounts.append(account)
        except FileNotFoundError:
            console.print("[red]File data.txt not found![/red]")

    def create_table(self):
        """إنشاء الجدول الديناميكي"""
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")

        # إضافة الأعمدة
        table.add_column("ID", style="cyan", width=3)
        table.add_column("Status", style="green", width=12)
        table.add_column("Coins", style="yellow", width=8)
        table.add_column("Seeds", style="blue", width=6)
        table.add_column("Water", style="cyan", width=6)
        table.add_column("Wheat", style="green", width=6)
        table.add_column("Plots", style="white", width=20)
        table.add_column("Timer", style="dim", width=8)

        # إضافة بيانات كل حساب
        for account in self.accounts:
            # إنشاء نص حالة الأراضي
            plots_status = ""
            next_timer = 0

            for i, plot in enumerate(account.plots):
                state = plot["state"]
                timer = plot["timer"]

                if state == "empty":
                    color = "dim"
                    symbol = "○"
                elif state == "waiting_water":
                    color = "blue"
                    symbol = "◐"
                elif state == "waiting_harvest":
                    color = "green"
                    symbol = "●"
                else:
                    color = "red"
                    symbol = "?"

                plots_status += f"[{color}]{symbol}[/{color}] "

                # العثور على أقل عداد متبقي
                if timer > 0 and (next_timer == 0 or timer < next_timer):
                    next_timer = timer

            # عرض العداد التالي أو "Ready" إذا لم يكن هناك عدادات
            timer_display = f"{next_timer}s" if next_timer > 0 else "Ready"

            # تحديد لون الحالة
            if account.status == "Active":
                status_color = "green"
            elif "Failed" in account.status:
                status_color = "red"
            elif account.status == "Processing...":
                status_color = "yellow"
            else:
                status_color = "blue"

            table.add_row(
                str(account.account_id),
                f"[{status_color}]{account.status}[/{status_color}]",
                str(account.coins),
                str(account.seeds),
                str(account.water),
                str(account.wheat),
                plots_status.strip(),
                timer_display
            )

        return table

    def worker(self, account):
        """Worker thread لكل حساب"""
        while self.running:
            try:
                account.run_cycle()
                time.sleep(1)  # انتظار قصير بين الدورات
            except Exception as e:
                account.status = f"Error: {str(e)[:10]}"
                time.sleep(5)

    def run(self):
        """تشغيل البوت الرئيسي"""
        if not self.accounts:
            console.print("[red]No accounts found in data.txt![/red]")
            return

        # بدء threads للحسابات
        threads = []
        for account in self.accounts:
            thread = threading.Thread(target=self.worker, args=(account,))
            thread.daemon = True
            thread.start()
            threads.append(thread)

        # عرض الجدول الديناميكي
        try:
            with Live(self.create_table(), refresh_per_second=2, screen=True) as live:
                while self.running:
                    live.update(self.create_table())
                    time.sleep(0.5)
        except KeyboardInterrupt:
            console.print("\n[yellow]Bot stopped by user[/yellow]")
            self.running = False

if __name__ == "__main__":
    console.print("[bold green]🌾 Farmton Bot Starting...[/bold green]")
    console.print("[dim]Legend: ○ = Empty | ◐ = Need Water | ● = Ready to Harvest[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    bot = FarmtonBot()
    bot.run()
