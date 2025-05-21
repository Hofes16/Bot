import wx
import wx.lib.scrolledpanel as scrolled
try:
    from plyer import notification
except ImportError:
    notification = None
from logic import BotLogic
from datetime import datetime
import pygame
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='islem_log.txt',
    filemode='a'
)

class BotGUI(wx.Frame):
    def __init__(self, logic_manager):
        super().__init__(None, title="Coin Trade Bot", size=(420, 610))
        self.logic = logic_manager
        self.bg_color = "#1e1e1e"
        self.fg_color = "white"
        self.SetBackgroundColour(self.bg_color)
        wx.SystemOptions.SetOption("msw.dark-mode", 0)
        self.selected_coin = self.logic.long_settings['symbol']
        self.current_tab = "long"
        self.long_form = {}
        self.short_form = {}
        self.hour_vars = {h: h in self.logic.long_settings['allowed_hours'] for h in range(24)}
        self.coin_list_cache = None
        self.sync_settings = False
        try:
            self._setup_ui()
            self.refresh_ui()
            self._start_ui_loop()
            logging.debug("BotGUI initialized")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.__init__] GUI başlatma hatası: {e}")
            print(f"GUI başlatma hatası: {e}")
            raise

    def refresh_ui(self):
        try:
            balance_text = f"💵 Bakiye 💵: {self.logic.balance or 0:.2f}"
            if self.logic.current_long_position or self.logic.current_short_position:
                balance_text += f" (+{self.logic.position_profit:.2f})"
            self.usdt_balance_label.SetLabel(balance_text)
            self.usdt_balance_label.SetForegroundColour(wx.Colour(0, 255, 0))
            self.usdt_balance_label.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            price = self.logic.last_price or 0
            price_format = f"{price:.4f}" if price < 1 else f"{price:.2f}"
            self.dot_price_label.SetLabel(f"{self.logic.symbol} Fiyatı: {price_format}")
            self.dot_rsi_label.SetLabel(f"RSI(6): {self.logic.last_rsi or 0:.2f}")
            self.dot_distance_label.SetLabel(f"MA7'ye Uzaklık: {self.logic.last_ma7_distance or 0:.2f}%")
            self.son_islem_kar_label.SetLabel(f"Toplam İşlem Kar: {self.logic.last_trade_profit or 0:.2f} USDT")
            self.btc_label.SetLabel(f"BTC USDT: {self.logic.btc_price or 0:.2f}")
            self.btc_label.SetForegroundColour(wx.Colour(255, 165, 0))
            self.eth_label.SetLabel(f"ETH / USDT: {self.logic.eth_price or 0:.2f}")
            self.eth_label.SetForegroundColour(wx.Colour(0, 128, 0))
            self.mesaj_label.SetLabel(f"Durum: {'Durduruldu' if not self.logic.bot_running else 'Çalışıyor'}")
            self._refresh_theme()
            logging.debug("UI refreshed")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.refresh_ui] UI yenileme hatası: {e}")
            print(f"UI yenileme hatası: {e}")

    def _start_ui_loop(self):
        try:
            self.refresh_ui()
            if self.logic.bot_running:
                self._update_data()
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, lambda evt: self._start_ui_loop(), self.timer)
            self.timer.Start(10000)
            logging.debug("UI loop started")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._start_ui_loop] UI döngü hatası: {e}")
            print(f"UI döngü hatası: {e}")

    def _update_data(self):
        try:
            if self.logic.mum_sonu_bekle:
                self._check_candle_close()
            else:
                self.logic.trade_logic()
            logging.debug("Data updated")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._update_data] Veri güncelleme hatası: {e}")
            print(f"Veri güncelleme hatası: {e}")

    def _check_candle_close(self):
        try:
            current_time = datetime.now()
            seconds_to_next_candle = 900 - (current_time.minute % 15 * 60 + current_time.second)
            if seconds_to_next_candle <= 0:
                self.mesaj_label.SetLabel("Durum: Çalışıyor")
                self.logic.trade_logic()
                wx.CallLater(1000, self._check_candle_close)
            else:
                self.mesaj_label.SetLabel(f"Mum kapanışı için {seconds_to_next_candle} saniye bekleniyor...")
                self.logic.update_data()
                wx.CallLater(min(seconds_to_next_candle * 1000, 60000), self._check_candle_close)
            logging.debug("Candle close checked")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._check_candle_close] Mum kapanış hatası: {e}")
            print(f"Mum kapanış hatası: {e}")

    def _refresh_theme(self):
        try:
            for widget in self.GetChildren():
                if isinstance(widget, (wx.StaticText, wx.Button, wx.TextCtrl, wx.CheckBox, wx.ListBox, wx.StaticBitmap)):
                    if 'Bakiye' in widget.GetLabel():
                        widget.SetForegroundColour(wx.Colour(0, 255, 0))
                        widget.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                        if '(+' in widget.GetLabel() or '(-' in widget.GetLabel():
                            widget.SetLabel(widget.GetLabel().split(' (')[0] + f" (+{self.logic.position_profit:.2f})")
                            widget.SetForegroundColour(wx.Colour(255, 165, 0))
                    elif 'BTC USDT' in widget.GetLabel():
                        widget.SetForegroundColour(wx.Colour(255, 165, 0))
                        widget.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    elif 'ETH / USDT' in widget.GetLabel():
                        widget.SetForegroundColour(wx.Colour(0, 128, 0))
                        widget.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    elif widget in [self.log_button, self.stats_button]:
                        widget.SetForegroundColour(wx.Colour("white"))
                        widget.SetBackgroundColour(self.bg_color)
                        widget.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    elif widget == self.baslat_button:
                        widget.SetForegroundColour(wx.Colour("white"))
                        widget.SetBackgroundColour(wx.Colour("#006400" if self.baslat_button.GetLabel() == "BAŞLAT" else "#FF0000"))
                        widget.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    else:
                        widget.SetForegroundColour(wx.Colour(self.fg_color))
                        widget.SetBackgroundColour(self.bg_color)
                        if isinstance(widget, wx.StaticText):
                            widget.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                    if isinstance(widget, wx.Button):
                        widget.SetWindowStyleFlag(wx.BORDER_SIMPLE)
            logging.debug("Theme refreshed for main frame")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._refresh_theme] Tema yenileme hatası: {e}")
            print(f"Tema yenileme hatası: {e}")

    def _refresh_settings_theme(self):
        try:
            if hasattr(self, 'ayar_pencere') and self.ayar_pencere:
                self.ayar_pencere.Freeze()
                self.ayar_pencere.SetBackgroundColour(self.bg_color)
                self.settings_panel.SetBackgroundColour(self.bg_color)
                for widget in self.ayar_pencere.GetChildren():
                    self._apply_widget_theme(widget)
                self.settings_panel.Refresh()
                self.settings_panel.Update()
                self.settings_panel.Layout()
                self.ayar_pencere.Thaw()
            logging.debug("Settings theme refreshed")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._refresh_settings_theme] Ayar tema yenileme hatası: {e}")
            print(f"Ayar tema yenileme hatası: {e}")

    def _apply_widget_theme(self, widget):
        try:
            if isinstance(widget, (wx.StaticText, wx.Button, wx.TextCtrl, wx.CheckBox, wx.Choice, wx.ListBox, wx.StaticBitmap)):
                widget.SetForegroundColour(wx.Colour(self.fg_color))
                widget.SetBackgroundColour(self.bg_color if not isinstance(widget, wx.TextCtrl) else "#2e2e2e")
                if isinstance(widget, wx.Button):
                    if widget == self.long_button:
                        widget.SetBackgroundColour(wx.Colour("gray" if self.current_tab == "long" else "#008000"))
                        widget.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                        return
                    if widget == self.short_button:
                        widget.SetBackgroundColour(wx.Colour("gray" if self.current_tab == "short" else "#FF0000"))
                        widget.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                        return
                    if widget == self.tum_ayarlari_kaydet_button:
                        widget.SetBackgroundColour(wx.Colour("gray"))
                        widget.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                        return
                if isinstance(widget, (wx.StaticText, wx.TextCtrl, wx.Choice)) and any(label in widget.GetLabel() for label in ["Coin", "TP", "SL", "Kaldıraç", "RSI", "MA7", "Bollinger", "Volatilite", "Veri", "Devre", "İşlem için"]):
                    widget.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                elif isinstance(widget, wx.CheckBox):
                    widget.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            for child in widget.GetChildren():
                self._apply_widget_theme(child)
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._apply_widget_theme] Widget tema uygulama hatası: {e}")
            print(f"Widget tema uygulama hatası: {e}")

    def _setup_ui(self):
        try:
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            top_panel = wx.Panel(self, style=wx.BORDER_NONE)
            top_panel.SetBackgroundColour(self.bg_color)
            top_sizer = wx.GridBagSizer(5, 5)
            try:
                settings_icon = wx.Image("settings_icon.png", wx.BITMAP_TYPE_PNG).Scale(70, 70)
                self.settings_img = wx.Bitmap(settings_icon)
                self.icon_label = wx.StaticBitmap(top_panel, bitmap=self.settings_img)
                self.icon_label.Bind(wx.EVT_LEFT_DOWN, lambda evt: self.ayarlar_penceresi())
                top_sizer.Add(self.icon_label, pos=(0, 0), span=(2, 1), flag=wx.ALL, border=10)
            except Exception as e:
                logging.error(f"İkon yüklenemedi: {e}")
                self.icon_label = wx.StaticText(top_panel, label="⚙️")
                self.icon_label.SetFont(wx.Font(48, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                self.icon_label.SetForegroundColour(wx.Colour("white"))
                self.icon_label.Bind(wx.EVT_LEFT_DOWN, lambda evt: self.ayarlar_penceresi())
                top_sizer.Add(self.icon_label, pos=(0, 0), span=(2, 1), flag=wx.ALL, border=10)
            settings_button = wx.Button(top_panel, label="Ayarlar", style=wx.BORDER_NONE)
            settings_button.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            settings_button.SetForegroundColour(wx.Colour("blue"))
            settings_button.SetBackgroundColour(self.bg_color)
            settings_button.Bind(wx.EVT_BUTTON, lambda evt: self.ayarlar_penceresi())
            top_sizer.Add(settings_button, pos=(2, 0), flag=wx.ALL, border=0)
            title_sizer = wx.BoxSizer(wx.HORIZONTAL)
            title_label = wx.StaticText(top_panel, label="TRADE BOT")
            title_label.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            title_label.SetForegroundColour(wx.Colour(self.fg_color))
            title_sizer.Add(title_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            try:
                globe_icon = wx.Image("globe_emoji.png", wx.BITMAP_TYPE_PNG).Scale(50, 50)
                self.globe_img = wx.Bitmap(globe_icon)
                self.globe_label = wx.StaticBitmap(top_panel, bitmap=self.globe_img)
                title_sizer.Add(self.globe_label, 0, wx.ALIGN_CENTER_VERTICAL)
            except Exception as e:
                logging.error(f"Globe emoji yüklenemedi: {e}")
                self.globe_label = wx.StaticText(top_panel, label="🌎")
                self.globe_label.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                self.globe_label.SetForegroundColour(wx.Colour(self.fg_color))
                title_sizer.Add(self.globe_label, 0, wx.ALIGN_CENTER_VERTICAL)
            top_sizer.Add(title_sizer, pos=(0, 1), flag=wx.ALL | wx.ALIGN_CENTER, border=10)
            top_panel.SetSizer(top_sizer)
            main_sizer.Add(top_panel, 0, wx.ALL, 10)
            self.usdt_balance_label = wx.StaticText(self, label="💵 Bakiye 💵: ---")
            self.usdt_balance_label.SetForegroundColour(wx.Colour(0, 255, 0))
            self.usdt_balance_label.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            main_sizer.Add(self.usdt_balance_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.baslat_button = wx.Button(self, label="BAŞLAT", style=wx.BORDER_SIMPLE)
            self.baslat_button.SetBackgroundColour(wx.Colour("#006400"))
            self.baslat_button.SetForegroundColour(wx.Colour("white"))
            self.baslat_button.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.baslat_button.SetMinSize((120, 50))
            self.baslat_button.Bind(wx.EVT_BUTTON, self.botu_baslat_durdur)
            main_sizer.Add(self.baslat_button, 0, wx.ALL | wx.ALIGN_CENTER, 10)
            logging.debug(f"Başlat button added to main_sizer, position: {self.baslat_button.GetPosition()}, visible: {self.baslat_button.IsShown()}")
            self.dot_price_label = wx.StaticText(self, label=f"{self.logic.symbol} Fiyatı: ---")
            main_sizer.Add(self.dot_price_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.mesaj_label = wx.StaticText(self, label="Durum Bilgisi: İşlem Yok")
            main_sizer.Add(self.mesaj_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.dot_rsi_label = wx.StaticText(self, label="RSI(6): ---")
            main_sizer.Add(self.dot_rsi_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.dot_distance_label = wx.StaticText(self, label="MA7'ye Uzaklık: ---")
            main_sizer.Add(self.dot_distance_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.son_islem_kar_label = wx.StaticText(self, label="Toplam İşlem Kar: --- USDT")
            main_sizer.Add(self.son_islem_kar_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.btc_label = wx.StaticText(self, label="BTC USDT: ---")
            self.btc_label.SetForegroundColour(wx.Colour(255, 165, 0))
            main_sizer.Add(self.btc_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            self.eth_label = wx.StaticText(self, label="ETH / USDT: ---")
            self.eth_label.SetForegroundColour(wx.Colour(0, 128, 0))
            main_sizer.Add(self.eth_label, 0, wx.ALL | wx.ALIGN_CENTER, 5)
            log_panel = wx.Panel(self, style=wx.BORDER_NONE)
            log_panel.SetBackgroundColour(self.bg_color)
            log_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.log_button = wx.StaticText(log_panel, label="LOG")
            self.log_button.SetForegroundColour(wx.Colour("white"))
            self.log_button.SetBackgroundColour(self.bg_color)
            self.log_button.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.log_button.Bind(wx.EVT_LEFT_DOWN, self.log_goster)
            log_sizer.Add(self.log_button, 0, wx.ALL, 20)
            log_panel.SetSizer(log_sizer)
            stats_panel = wx.Panel(self, style=wx.BORDER_NONE)
            stats_panel.SetBackgroundColour(self.bg_color)
            stats_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.stats_button = wx.StaticText(stats_panel, label="İstatistik")
            self.stats_button.SetForegroundColour(wx.Colour("white"))
            self.stats_button.SetBackgroundColour(self.bg_color)
            self.stats_button.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.stats_button.Bind(wx.EVT_LEFT_DOWN, self.istatistik_penceresi)
            stats_sizer.Add(self.stats_button, 0, wx.ALL, 20)
            stats_panel.SetSizer(stats_sizer)
            bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
            bottom_sizer.Add(log_panel, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
            bottom_sizer.AddStretchSpacer()
            bottom_sizer.Add(stats_panel, 0, wx.ALIGN_CENTER_VERTICAL)
            main_sizer.Add(bottom_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
            self.SetSizer(main_sizer)
            self._refresh_theme()
            logging.debug("UI setup completed")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._setup_ui] UI kurulum hatası: {e}")
            print(f"UI kurulum hatası: {e}")
            raise

    def botu_baslat_durdur(self, event):
        try:
            if self.logic.bot_running:
                self.logic.stop_bot()
                self.baslat_button.SetLabel("BAŞLAT")
                self.baslat_button.SetBackgroundColour(wx.Colour("#006400"))
                self.mesaj_label.SetLabel("Durum: Durduruldu")
                self.play_sound("Bot_durduruldu.wav")
            else:
                self.logic.start_bot()
                self.baslat_button.SetLabel("DURDUR")
                self.baslat_button.SetBackgroundColour(wx.Colour("#FF0000"))
                self.mesaj_label.SetLabel("Durum: Çalışıyor")
                if notification:
                    notification.notify(title="Bot Aktif", message="Bot çalışmaya başladı.", timeout=5)
            self._refresh_theme()
            logging.debug(f"Bot status changed: {'running' if self.logic.bot_running else 'stopped'}")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.botu_baslat_durdur] Bot başlatma/durdurma hatası: {e}")
            print(f"Bot başlatma/durdurma hatası: {e}")
            self.mesaj_label.SetLabel(f"Hata: {e}")

    def play_sound(self, sound_path):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.play_sound] Ses çalınamadı: {e}")
            print(f"Ses çalınamadı: {e}")

    def ayarlar_penceresi(self):
        try:
            if hasattr(self, 'ayar_pencere') and self.ayar_pencere:
                self.ayar_pencere.Destroy()
                self.ayar_pencere = None
            self.long_form = {}
            self.short_form = {}
            self.ayar_pencere = wx.Frame(self, title="Ayarlar", size=(800, 900))
            self.ayar_pencere.SetBackgroundColour(self.bg_color)
            self.ayar_pencere.Bind(wx.EVT_CLOSE, lambda evt: self.ayar_pencere.Destroy())
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            top_panel = wx.Panel(self.ayar_pencere, style=wx.BORDER_NONE)
            top_panel.SetBackgroundColour(self.bg_color)
            top_sizer = wx.BoxSizer(wx.HORIZONTAL)
            try:
                settings_icon = wx.Image("settings_icon.png", wx.BITMAP_TYPE_PNG).Scale(70, 70)
                self.ayar_icon = wx.Bitmap(settings_icon)
                self.ayar_icon_label = wx.StaticBitmap(top_panel, bitmap=self.ayar_icon)
                top_sizer.Add(self.ayar_icon_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
            except Exception as e:
                logging.error(f"Ayarlar ikonu yüklenemedi: {e}")
                ayar_icon_label = wx.StaticText(top_panel, label="⚙️")
                ayar_icon_label.SetFont(wx.Font(32, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
                ayar_icon_label.SetForegroundColour(wx.Colour("white"))
                top_sizer.Add(ayar_icon_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
            title_label = wx.StaticText(top_panel, label="AYARLAR")
            title_label.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            title_label.SetForegroundColour(wx.Colour("blue"))
            top_sizer.Add(title_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            self.tum_ayarlari_kaydet_button = wx.Button(top_panel, label="KAYDET 💾", style=wx.BORDER_NONE)
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("gray")
            self.tum_ayarlari_kaydet_button.SetForegroundColour(wx.Colour("white"))
            self.tum_ayarlari_kaydet_button.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.tum_ayarlari_kaydet_button.Bind(wx.EVT_BUTTON, self.tum_ayarlari_kaydet)
            top_sizer.Add(self.tum_ayarlari_kaydet_button, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
            top_panel.SetSizer(top_sizer)
            main_sizer.Add(top_panel, 0, wx.ALL, 10)
            tab_panel = wx.Panel(self.ayar_pencere, style=wx.BORDER_NONE)
            tab_panel.SetBackgroundColour(self.bg_color)
            tab_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.long_button = wx.Button(tab_panel, label="Long Şartları", style=wx.BORDER_NONE)
            self.long_button.SetBackgroundColour(wx.Colour("green"))
            self.long_button.SetForegroundColour(wx.Colour("white"))
            self.long_button.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.long_button.Bind(wx.EVT_BUTTON, lambda evt: self.switch_tab("long"))
            tab_sizer.Add(self.long_button, 0, wx.ALL, 5)
            self.short_button = wx.Button(tab_panel, label="Short Şartları", style=wx.BORDER_NONE)
            self.short_button.SetBackgroundColour(wx.Colour("red"))
            self.short_button.SetForegroundColour(wx.Colour("white"))
            self.short_button.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.short_button.Bind(wx.EVT_BUTTON, lambda evt: self.switch_tab("short"))
            tab_sizer.Add(self.short_button, 0, wx.ALL, 5)
            sync_label = wx.StaticText(tab_panel, label="↔️")
            sync_label.SetForegroundColour(wx.Colour("white"))
            sync_label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            tab_sizer.Add(sync_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            self.sync_checkbox = wx.CheckBox(tab_panel, label="Ayarları Senkronize Et")
            self.sync_checkbox.SetForegroundColour(wx.Colour("white"))
            self.sync_checkbox.SetBackgroundColour(self.bg_color)
            self.sync_checkbox.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            self.sync_checkbox.Bind(wx.EVT_CHECKBOX, self.on_sync_checkbox)
            tab_sizer.Add(self.sync_checkbox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            tab_panel.SetSizer(tab_sizer)
            main_sizer.Add(tab_panel, 0, wx.EXPAND | wx.ALL, 10)
            self.settings_panel = scrolled.ScrolledPanel(self.ayar_pencere, style=wx.BORDER_NONE)
            self.settings_panel.SetBackgroundColour(self.bg_color)
            self.settings_sizer = wx.BoxSizer(wx.VERTICAL)
            self.settings_panel.SetSizer(self.settings_sizer)
            self.settings_panel.SetupScrolling()
            main_sizer.Add(self.settings_panel, 1, wx.EXPAND | wx.ALL, 10)
            self.ayar_pencere.SetSizer(main_sizer)
            self.switch_tab("long")
            self._refresh_settings_theme()
            self.ayar_pencere.Show()
            logging.debug("Ayarlar penceresi açıldı")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.ayarlar_penceresi] Ayarlar penceresi hatası: {e}")
            print(f"Ayarlar penceresi hatası: {e}")

    def on_sync_checkbox(self, event):
        self.sync_settings = event.GetEventObject().GetValue()
        logging.debug(f"Sync settings: {self.sync_settings}")

    def switch_tab(self, tab):
        try:
            if self.current_tab == "long" and self.long_form:
                self._save_form_to_settings("long")
            elif self.current_tab == "short" and self.short_form:
                self._save_form_to_settings("short")
            self.current_tab = tab
            if tab == "long":
                self.long_button.SetBackgroundColour(wx.Colour("gray"))
                self.short_button.SetBackgroundColour(wx.Colour("red"))
            else:
                self.long_button.SetBackgroundColour(wx.Colour("green"))
                self.short_button.SetBackgroundColour(wx.Colour("gray"))
            self.ayar_pencere.Freeze()
            self._create_settings_frame()
            self._refresh_settings_theme()
            self.settings_panel.Refresh()
            self.settings_panel.Update()
            self.settings_panel.Layout()
            self.settings_panel.SetupScrolling()
            for child in self.settings_panel.GetChildren():
                child.Refresh()
                child.Update()
            self.ayar_pencere.Thaw()
            logging.debug(f"Tab switched to: {tab}")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.switch_tab] Sekme değiştirme hatası: {e}")
            print(f"Sekme değiştirme hatası: {e}")

    def _save_form_to_settings(self, tab):
        try:
            form_dict = self.long_form if tab == "long" else self.short_form
            settings = self.logic.long_settings if tab == "long" else self.logic.short_settings
            if not form_dict:
                return
            settings['rsi_condition'] = form_dict['rsi_condition_var'].GetStringSelection()
            settings['tp_percent'] = float(form_dict['tp_entry'].GetValue().replace(',', '.')) / 100 if form_dict['tp_check'].GetValue() and form_dict['tp_entry'].GetValue() else None
            settings['sl_percent'] = float(form_dict['sl_entry'].GetValue().replace(',', '.')) / 100 if form_dict['sl_check'].GetValue() and form_dict['sl_entry'].GetValue() else None
            settings['rsi_threshold'] = float(form_dict['rsi_entry'].GetValue().replace(',', '.')) if form_dict['rsi_check'].GetValue() and form_dict['rsi_entry'].GetValue() else None
            settings['leverage'] = int(float(form_dict['leverage_entry'].GetValue().strip())) if form_dict['leverage_check'].GetValue() and form_dict['leverage_entry'].GetValue() else None
            settings['ma7_threshold'] = float(form_dict['ma7_threshold_entry'].GetValue().replace(',', '.')) / 100 if form_dict['ma7_check'].GetValue() and form_dict['ma7_threshold_entry'].GetValue() else None
            settings['bollinger_band_break_pct'] = float(form_dict['bollinger_entry'].GetValue().replace(',', '.')) / 100 if form_dict['bollinger_check'].GetValue() and form_dict['bollinger_entry'].GetValue() else None
            settings['volatility_threshold'] = float(form_dict['volatility_entry'].GetValue().replace(',', '.')) / 100 if form_dict['volatility_check'].GetValue() and form_dict['volatility_entry'].GetValue() else None
            settings['symbol'] = self.selected_coin
            settings['allowed_hours'] = [h for h in range(24) if self.hour_vars.get(h, False)]
            if tab == "long":
                self.logic.update_long_settings(**settings)
            else:
                self.logic.update_short_settings(**settings)
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._save_form_to_settings] Form kaydetme hatası: {e}")
            print(f"Form kaydetme hatası: {e}")

    def _create_settings_frame(self):
        try:
            for child in self.settings_panel.GetChildren():
                child.Destroy()
            settings = self.logic.long_settings if self.current_tab == "long" else self.logic.short_settings
            form_dict = self.long_form if self.current_tab == "long" else self.short_form
            form_dict.clear()
            main_panel = wx.Panel(self.settings_panel, style=wx.BORDER_NONE)
            main_panel.SetBackgroundColour(self.bg_color)
            main_sizer = wx.BoxSizer(wx.HORIZONTAL)
            left_panel = wx.Panel(main_panel, style=wx.BORDER_NONE)
            left_panel.SetBackgroundColour(self.bg_color)
            left_sizer = wx.BoxSizer(wx.VERTICAL)
            coin_label = wx.StaticText(left_panel, label="Coin Seçin:")
            coin_label.SetForegroundColour(wx.Colour(self.fg_color))
            coin_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            left_sizer.Add(coin_label, 0, wx.ALL, 5)
            self.coin_entry = wx.TextCtrl(left_panel, value=self.selected_coin, size=(150, -1))
            self.coin_entry.SetBackgroundColour("#2e2e2e")
            self.coin_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.coin_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            left_sizer.Add(self.coin_entry, 0, wx.ALL, 5)
            self.coin_listbox = wx.ListBox(left_panel, size=(150, 60))
            self.coin_listbox.SetBackgroundColour("#2e2e2e")
            self.coin_listbox.SetForegroundColour(wx.Colour(self.fg_color))
            self.coin_listbox.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            left_sizer.Add(self.coin_listbox, 0, wx.ALL, 5)
            if self.coin_list_cache is None:
                self.coin_list_cache = self.logic.get_coin_list()
            for coin in self.coin_list_cache:
                self.coin_listbox.Append(coin)
            def update_listbox(event):
                search_term = self.coin_entry.GetValue().upper()
                self.coin_listbox.Clear()
                for coin in self.coin_list_cache:
                    if search_term == "" or coin.upper().startswith(search_term):
                        self.coin_listbox.Append(coin)
            def select_coin(event):
                selection = self.coin_listbox.GetSelection()
                if selection != wx.NOT_FOUND:
                    selected = self.coin_listbox.GetString(selection)
                    self.selected_coin = selected
                    self.coin_entry.SetValue(selected)
            self.coin_entry.Bind(wx.EVT_TEXT, update_listbox)
            self.coin_listbox.Bind(wx.EVT_LISTBOX, select_coin)
            tp_panel = wx.Panel(left_panel, style=wx.BORDER_NONE)
            tp_panel.SetBackgroundColour(self.bg_color)
            tp_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.tp_check = wx.CheckBox(tp_panel)
            self.tp_check.SetValue(settings['tp_percent'] is not None)
            self.tp_check.SetBackgroundColour(self.bg_color)
            self.tp_check.SetForegroundColour(wx.Colour(self.fg_color))
            tp_sizer.Add(self.tp_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            tp_label = wx.StaticText(tp_panel, label="TP (%):")
            tp_label.SetForegroundColour(wx.Colour(self.fg_color))
            tp_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            tp_sizer.Add(tp_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.tp_entry = wx.TextCtrl(tp_panel, value=str(settings['tp_percent'] * 100) if settings['tp_percent'] is not None else "1.0", size=(100, -1))
            self.tp_entry.SetBackgroundColour("#2e2e2e")
            self.tp_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.tp_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            tp_sizer.Add(self.tp_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            tp_panel.SetSizer(tp_sizer)
            left_sizer.Add(tp_panel, 0, wx.ALL, 5)
            form_dict['tp_check'] = self.tp_check
            form_dict['tp_entry'] = self.tp_entry
            sl_panel = wx.Panel(left_panel, style=wx.BORDER_NONE)
            sl_panel.SetBackgroundColour(self.bg_color)
            sl_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.sl_check = wx.CheckBox(sl_panel)
            self.sl_check.SetValue(settings['sl_percent'] is not None)
            self.sl_check.SetBackgroundColour(self.bg_color)
            self.sl_check.SetForegroundColour(wx.Colour(self.fg_color))
            sl_sizer.Add(self.sl_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            sl_label = wx.StaticText(sl_panel, label="SL (%):")
            sl_label.SetForegroundColour(wx.Colour(self.fg_color))
            sl_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            sl_sizer.Add(sl_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.sl_entry = wx.TextCtrl(sl_panel, value=str(settings['sl_percent'] * 100) if settings['sl_percent'] is not None else "1.7", size=(100, -1))
            self.sl_entry.SetBackgroundColour("#2e2e2e")
            self.sl_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.sl_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            sl_sizer.Add(self.sl_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            sl_panel.SetSizer(sl_sizer)
            left_sizer.Add(sl_panel, 0, wx.ALL, 5)
            form_dict['sl_check'] = self.sl_check
            form_dict['sl_entry'] = self.sl_entry
            leverage_panel = wx.Panel(left_panel, style=wx.BORDER_NONE)
            leverage_panel.SetBackgroundColour(self.bg_color)
            leverage_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.leverage_check = wx.CheckBox(leverage_panel)
            self.leverage_check.SetValue(settings['leverage'] is not None)
            self.leverage_check.SetBackgroundColour(self.bg_color)
            self.leverage_check.SetForegroundColour(wx.Colour(self.fg_color))
            leverage_sizer.Add(self.leverage_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            leverage_label = wx.StaticText(leverage_panel, label="Kaldıraç:")
            leverage_label.SetForegroundColour(wx.Colour(self.fg_color))
            leverage_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            leverage_sizer.Add(leverage_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.leverage_entry = wx.TextCtrl(leverage_panel, value=str(settings['leverage']) if settings['leverage'] is not None else "15", size=(100, -1))
            self.leverage_entry.SetBackgroundColour("#2e2e2e")
            self.leverage_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.leverage_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            leverage_sizer.Add(self.leverage_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            leverage_panel.SetSizer(leverage_sizer)
            left_sizer.Add(leverage_panel, 0, wx.ALL, 5)
            form_dict['leverage_check'] = self.leverage_check
            form_dict['leverage_entry'] = self.leverage_entry
            rsi_condition_label = wx.StaticText(left_panel, label="RSI(6) Koşulu:")
            rsi_condition_label.SetForegroundColour(wx.Colour(self.fg_color))
            rsi_condition_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            left_sizer.Add(rsi_condition_label, 0, wx.ALL, 5)
            rsi_condition_choices = ["Büyüktür", "Küçüktür"]
            self.rsi_condition_var = wx.Choice(left_panel, choices=rsi_condition_choices)
            self.rsi_condition_var.SetStringSelection(settings['rsi_condition'])
            self.rsi_condition_var.SetBackgroundColour(self.bg_color)
            self.rsi_condition_var.SetForegroundColour(wx.Colour(self.fg_color))
            self.rsi_condition_var.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            left_sizer.Add(self.rsi_condition_var, 0, wx.ALL, 5)
            form_dict['rsi_condition_var'] = self.rsi_condition_var
            rsi_panel = wx.Panel(left_panel, style=wx.BORDER_NONE)
            rsi_panel.SetBackgroundColour(self.bg_color)
            rsi_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.rsi_check = wx.CheckBox(rsi_panel)
            self.rsi_check.SetValue(settings['rsi_threshold'] is not None)
            self.rsi_check.SetBackgroundColour(self.bg_color)
            self.rsi_check.SetForegroundColour(wx.Colour(self.fg_color))
            rsi_sizer.Add(self.rsi_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            rsi_label = wx.StaticText(rsi_panel, label="RSI Eşiği:")
            rsi_label.SetForegroundColour(wx.Colour(self.fg_color))
            rsi_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            rsi_sizer.Add(rsi_label, 0, wx.ALIGN_CENTER_VERTICAL)
            rsi_default = "20.0" if self.current_tab == "long" else "80.0"
            self.rsi_entry = wx.TextCtrl(rsi_panel, value=str(settings['rsi_threshold']) if settings['rsi_threshold'] is not None else rsi_default, size=(100, -1))
            self.rsi_entry.SetBackgroundColour("#2e2e2e")
            self.rsi_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.rsi_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            rsi_sizer.Add(self.rsi_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            rsi_panel.SetSizer(rsi_sizer)
            left_sizer.Add(rsi_panel, 0, wx.ALL, 5)
            form_dict['rsi_check'] = self.rsi_check
            form_dict['rsi_entry'] = self.rsi_entry
            ma7_panel = wx.Panel(left_panel, style=wx.BORDER_NONE)
            ma7_panel.SetBackgroundColour(self.bg_color)
            ma7_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.ma7_check = wx.CheckBox(ma7_panel)
            self.ma7_check.SetValue(settings['ma7_threshold'] is not None)
            self.ma7_check.SetBackgroundColour(self.bg_color)
            self.ma7_check.SetForegroundColour(wx.Colour(self.fg_color))
            ma7_sizer.Add(self.ma7_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            ma7_label = wx.StaticText(ma7_panel, label="MA7 Uzaklık Eşiği (%):")
            ma7_label.SetForegroundColour(wx.Colour(self.fg_color))
            ma7_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            ma7_sizer.Add(ma7_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.ma7_threshold_entry = wx.TextCtrl(ma7_panel, value=str(settings['ma7_threshold'] * 100) if settings['ma7_threshold'] is not None else "0.7", size=(100, -1))
            self.ma7_threshold_entry.SetBackgroundColour("#2e2e2e")
            self.ma7_threshold_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.ma7_threshold_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            ma7_sizer.Add(self.ma7_threshold_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            ma7_panel.SetSizer(ma7_sizer)
            left_sizer.Add(ma7_panel, 0, wx.ALL, 5)
            form_dict['ma7_check'] = self.ma7_check
            form_dict['ma7_threshold_entry'] = self.ma7_threshold_entry
            left_panel.SetSizer(left_sizer)
            main_sizer.Add(left_panel, 0, wx.ALL, 0)
            right_panel = wx.Panel(main_panel, style=wx.BORDER_NONE)
            right_panel.SetBackgroundColour(self.bg_color)
            right_sizer = wx.BoxSizer(wx.VERTICAL)
            font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            dc = wx.ClientDC(self.short_button)
            dc.SetFont(font)
            text_extent = dc.GetTextExtent("Sh")
            offset_x = text_extent[0]
            bollinger_panel = wx.Panel(right_panel, style=wx.BORDER_NONE)
            bollinger_panel.SetBackgroundColour(self.bg_color)
            bollinger_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.bollinger_check = wx.CheckBox(bollinger_panel)
            self.bollinger_check.SetValue(settings['bollinger_band_break_pct'] is not None)
            self.bollinger_check.SetBackgroundColour(self.bg_color)
            self.bollinger_check.SetForegroundColour(wx.Colour(self.fg_color))
            bollinger_sizer.Add(self.bollinger_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            bollinger_label = wx.StaticText(bollinger_panel, label="Bollinger Kesme (%):")
            bollinger_label.SetForegroundColour(wx.Colour(self.fg_color))
            bollinger_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            bollinger_sizer.Add(bollinger_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.bollinger_entry = wx.TextCtrl(bollinger_panel, value=str(settings['bollinger_band_break_pct'] * 100) if settings['bollinger_band_break_pct'] is not None else "0.25", size=(100, -1))
            self.bollinger_entry.SetBackgroundColour("#2e2e2e")
            self.bollinger_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.bollinger_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            bollinger_sizer.Add(self.bollinger_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            bollinger_panel.SetSizer(bollinger_sizer)
            right_sizer.Add(bollinger_panel, 0, wx.LEFT | wx.TOP, border=offset_x)
            form_dict['bollinger_check'] = self.bollinger_check
            form_dict['bollinger_entry'] = self.bollinger_entry
            volatility_panel = wx.Panel(right_panel, style=wx.BORDER_NONE)
            volatility_panel.SetBackgroundColour(self.bg_color)
            volatility_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.volatility_check = wx.CheckBox(volatility_panel)
            self.volatility_check.SetValue(settings['volatility_threshold'] is not None)
            self.volatility_check.SetBackgroundColour(self.bg_color)
            self.volatility_check.SetForegroundColour(wx.Colour(self.fg_color))
            volatility_sizer.Add(self.volatility_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
            volatility_label = wx.StaticText(volatility_panel, label="Volatilite Eşiği (%):")
            volatility_label.SetForegroundColour(wx.Colour(self.fg_color))
            volatility_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            volatility_sizer.Add(volatility_label, 0, wx.ALIGN_CENTER_VERTICAL)
            self.volatility_entry = wx.TextCtrl(volatility_panel, value=str(settings['volatility_threshold'] * 100) if settings['volatility_threshold'] is not None else "50.0", size=(100, -1))
            self.volatility_entry.SetBackgroundColour("#2e2e2e")
            self.volatility_entry.SetForegroundColour(wx.Colour(self.fg_color))
            self.volatility_entry.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            volatility_sizer.Add(self.volatility_entry, 0, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
            volatility_panel.SetSizer(volatility_sizer)
            right_sizer.Add(volatility_panel, 0, wx.LEFT | wx.TOP, border=offset_x)
            form_dict['volatility_check'] = self.volatility_check
            form_dict['volatility_entry'] = self.volatility_entry
            data_source_label = wx.StaticText(right_panel, label="Veri Kaynağı:")
            data_source_label.SetForegroundColour(wx.Colour(self.fg_color))
            data_source_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            right_sizer.Add(data_source_label, 0, wx.LEFT | wx.TOP, border=offset_x)
            data_source_choices = ["gateio", "binance"]
            self.data_source_choice = wx.Choice(right_panel, choices=data_source_choices)
            self.data_source_choice.SetStringSelection(self.logic.data_source)
            self.data_source_choice.SetBackgroundColour(self.bg_color)
            self.data_source_choice.SetForegroundColour(wx.Colour(self.fg_color))
            self.data_source_choice.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            right_sizer.Add(self.data_source_choice, 0, wx.LEFT | wx.TOP, border=offset_x)
            form_dict['data_source_choice'] = self.data_source_choice
            disable_position_label = wx.StaticText(right_panel, label="Devre Dışı Bırak:")
            disable_position_label.SetForegroundColour(wx.Colour(self.fg_color))
            disable_position_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            right_sizer.Add(disable_position_label, 0, wx.LEFT | wx.TOP, border=offset_x)
            disable_position_choices = ["Hiçbiri", "Long", "Short"]
            self.disable_position_choice = wx.Choice(right_panel, choices=disable_position_choices)
            self.disable_position_choice.SetStringSelection(self.logic.disable_position)
            self.disable_position_choice.SetBackgroundColour(self.bg_color)
            self.disable_position_choice.SetForegroundColour(wx.Colour(self.fg_color))
            self.disable_position_choice.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            right_sizer.Add(self.disable_position_choice, 0, wx.LEFT | wx.TOP, border=offset_x)
            form_dict['disable_position_choice'] = self.disable_position_choice
            mum_sonu_check_panel = wx.Panel(right_panel, style=wx.BORDER_NONE)
            mum_sonu_check_panel.SetBackgroundColour(self.bg_color)
            mum_sonu_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.mum_sonu_check = wx.CheckBox(mum_sonu_check_panel, label="Mum Sonu Bekle")
            self.mum_sonu_check.SetValue(self.logic.mum_sonu_bekle)
            self.mum_sonu_check.SetBackgroundColour(self.bg_color)
            self.mum_sonu_check.SetForegroundColour(wx.Colour(self.fg_color))
            self.mum_sonu_check.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            mum_sonu_sizer.Add(self.mum_sonu_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=offset_x)
            mum_sonu_check_panel.SetSizer(mum_sonu_sizer)
            right_sizer.Add(mum_sonu_check_panel, 0, wx.TOP, 5)
            form_dict['mum_sonu_check'] = self.mum_sonu_check
            hours_label = wx.StaticText(right_panel, label="İşlem için uygun saatler:")
            hours_label.SetForegroundColour(wx.Colour(self.fg_color))
            hours_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            right_sizer.Add(hours_label, 0, wx.LEFT | wx.TOP, border=offset_x)
            hours_panel = wx.Panel(right_panel, style=wx.BORDER_NONE)
            hours_panel.SetBackgroundColour(self.bg_color)
            hours_sizer = wx.GridSizer(rows=4, cols=6, vgap=5, hgap=5)
            self.hour_checkboxes = {}
            for hour in range(24):
                checkbox = wx.CheckBox(hours_panel, label=str(hour))
                checkbox.SetValue(self.hour_vars.get(hour, False))
                checkbox.SetBackgroundColour(self.bg_color)
                checkbox.SetForegroundColour(wx.Colour(self.fg_color))
                checkbox.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                checkbox.Bind(wx.EVT_CHECKBOX, lambda evt, h=hour: self.on_hour_checkbox(evt, h))
                hours_sizer.Add(checkbox, 0, wx.ALL, 5)
                self.hour_checkboxes[hour] = checkbox
            hours_panel.SetSizer(hours_sizer)
            right_sizer.Add(hours_panel, 0, wx.LEFT | wx.TOP, border=offset_x)
            right_panel.SetSizer(right_sizer)
            main_sizer.Add(right_panel, 0, wx.ALL, 0)
            main_panel.SetSizer(main_sizer)
            self.settings_sizer.Add(main_panel, 0, wx.ALL, 0)
            logging.debug("Settings frame created")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI._create_settings_frame] Ayar çerçevesi oluşturma hatası: {e}")
            print(f"Ayar çerçevesi oluşturma hatası: {e}")

    def on_hour_checkbox(self, event, hour):
        try:
            self.hour_vars[hour] = event.GetEventObject().GetValue()
            logging.debug(f"Hour {hour} checkbox updated: {self.hour_vars[hour]}")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.on_hour_checkbox] Saat checkbox hatası: {e}")
            print(f"Saat checkbox hatası: {e}")

    def tum_ayarlari_kaydet(self, event):
        try:
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("green")
            self.tum_ayarlari_kaydet_button.Refresh()
            wx.Yield()
            wx.MilliSleep(500)
            self._save_form_to_settings(self.current_tab)
            long_settings = self.logic.long_settings.copy()
            short_settings = self.logic.short_settings.copy()
            if self.sync_settings:
                synced_settings = {
                    'leverage': long_settings['leverage'],
                    'ma7_threshold': long_settings['ma7_threshold'],
                    'bollinger_band_break_pct': long_settings['bollinger_band_break_pct'],
                    'volatility_threshold': long_settings['volatility_threshold'],
                    'allowed_hours': long_settings['allowed_hours']
                }
                short_settings.update(synced_settings)
                long_settings.update(synced_settings)
                self.logic.update_long_settings(**long_settings)
                self.logic.update_short_settings(**short_settings)
            self.logic.set_data_source(self.long_form.get('data_source_choice', self.short_form.get('data_source_choice')).GetStringSelection())
            self.logic.set_mum_sonu_bekle(self.long_form.get('mum_sonu_check', self.short_form.get('mum_sonu_check')).GetValue())
            self.logic.set_disable_position(self.long_form.get('disable_position_choice', self.short_form.get('disable_position_choice')).GetStringSelection())
            self.logic.save_selected_coins(self.selected_coin, self.selected_coin)
            logging.info(f"Ayarlar kaydedildi: Long={long_settings}, Short={short_settings}")
            wx.MessageBox("✔️ Ayarlar başarıyla kaydedildi!", "Başarılı", wx.OK | wx.ICON_INFORMATION)
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("gray")
            self.tum_ayarlari_kaydet_button.Refresh()
        except ValueError as ve:
            logging.error(f"[gui.py:BotGUI.tum_ayarlari_kaydet] Geçersiz giriş: {ve}")
            wx.MessageBox(f"Geçersiz giriş: {ve}", "Hata", wx.OK | wx.ICON_ERROR)
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("red")
            self.tum_ayarlari_kaydet_button.Refresh()
            wx.MilliSleep(500)
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("gray")
            self.tum_ayarlari_kaydet_button.Refresh()
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.tum_ayarlari_kaydet] Ayar kaydetme hatası: {e}")
            wx.MessageBox(f"Ayarlar kaydedilemedi: {e}", "Hata", wx.OK | wx.ICON_ERROR)
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("red")
            self.tum_ayarlari_kaydet_button.Refresh()
            wx.MilliSleep(500)
            self.tum_ayarlari_kaydet_button.SetBackgroundColour("gray")
            self.tum_ayarlari_kaydet_button.Refresh()

    def log_goster(self, event):
        try:
            log_frame = wx.Frame(self, title="Log", size=(600, 400))
            log_frame.SetBackgroundColour(self.bg_color)
            log_text = wx.TextCtrl(log_frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
            log_text.SetBackgroundColour("#2e2e2e")
            log_text.SetForegroundColour(wx.Colour(self.fg_color))
            log_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            try:
                with open("islem_log.txt", "r", encoding="utf-8") as f:
                    log_text.SetValue(f.read())
            except Exception as e:
                log_text.SetValue(f"Log dosyası okunamadı: {e}")
            log_frame.Show()
            logging.debug("Log penceresi açıldı")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.log_goster] Log gösterme hatası: {e}")
            print(f"Log gösterme hatası: {e}")

    def istatistik_penceresi(self, event):
        try:
            stats_frame = wx.Frame(self, title="İstatistikler", size=(400, 300))
            stats_frame.SetBackgroundColour(self.bg_color)
            stats_sizer = wx.BoxSizer(wx.VERTICAL)
            stats_text = wx.TextCtrl(stats_frame, style=wx.TE_MULTILINE | wx.TE_READONLY)
            stats_text.SetBackgroundColour("#2e2e2e")
            stats_text.SetForegroundColour(wx.Colour(self.fg_color))
            stats_text.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            stats_content = (
                f"Long Başarılı: {self.logic.long_basarili}\n"
                f"Long Başarısız: {self.logic.long_basarisiz}\n"
                f"Short Başarılı: {self.logic.short_basarili}\n"
                f"Short Başarısız: {self.logic.short_basarisiz}\n"
            )
            stats_text.SetValue(stats_content)
            stats_sizer.Add(stats_text, 1, wx.EXPAND | wx.ALL, 10)
            stats_frame.SetSizer(stats_sizer)
            stats_frame.Show()
            logging.debug("İstatistik penceresi açıldı")
        except Exception as e:
            logging.error(f"[gui.py:BotGUI.istatistik_penceresi] İstatistik penceresi hatası: {e}")
            print(f"İstatistik penceresi hatası: {e}")

if __name__ == "__main__":
    try:
        print("Program başlatılıyor...")
        logic = BotLogic()
        app = wx.App(False)
        frame = BotGUI(logic)
        frame.Show()
        app.MainLoop()
    except Exception as e:
        print(f"Program başlatma hatası: {e}")
        logging.error(f"[gui.py:main] Program başlatma hatası: {e}")