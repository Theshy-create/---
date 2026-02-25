import sys, os, json, csv, io, ctypes, ctypes.wintypes, webbrowser, urllib.request
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import db

APP_NAME = "密盾 AegisVault"
APP_NAME_SHORT = "密盾"
AUTO_LOCK_MINUTES = 30

# ═══════════════════ Windows Title Bar ═══════════════════

class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint), ("AnimationId", ctypes.c_int)]
class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int), ("Data", ctypes.POINTER(ACCENT_POLICY)), ("SizeOfData", ctypes.c_size_t)]
class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int)]

def _to_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3: h = h[0]*2 + h[1]*2 + h[2]*2
    if len(h) < 6: h = h.ljust(6, '0')
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def _rgba(h, a=1.0):
    r, g, b = _to_rgb(h)
    return f"rgba({r},{g},{b},{a})"

def set_titlebar_color(hwnd, bg_hex, is_dark=True):
    try:
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1 if is_dark else 0)), 4)
        r, g, b = _to_rgb(bg_hex)
        c = ctypes.c_uint(r | (g << 8) | (b << 16))
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c), 4)
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(c), 4)
    except: pass

# ═══════════════════ Theme ═══════════════════

DARK_THEME = {
    "bg": "#0B0B12", "bg2": "#13131C", "card": "#191924", "card_hover": "#20202E",
    "border": "rgba(255,255,255,0.06)", "text": "#E8E8ED", "text2": "#8585A0", "muted": "#50506A",
    "input_bg": "#101018", "accent": "#7B6CF0", "accent2": "#4EA4F6", "accent_hover": "#9385F5",
    "accent_bg": "rgba(123,108,240,0.12)",
    "sidebar": "#0E0E16", "sb_border": "rgba(255,255,255,0.04)", "topbar": "#0E0E16",
    "menu_bg": "#1A1A28", "scroll": "rgba(255,255,255,0.06)", "red": "#F87171", "green": "#4ADE80",
    "orange": "#FBBF24", "yellow": "#FDE68A", "is_dark": True,
}
LIGHT_THEME = {
    "bg": "#F2F2F8", "bg2": "#FFFFFF", "card": "#FFFFFF", "card_hover": "#F6F6FC",
    "border": "rgba(0,0,0,0.07)", "text": "#181830", "text2": "#6E6E88", "muted": "#A0A0B8",
    "input_bg": "#F4F4FA", "accent": "#6C5CE7", "accent2": "#4EA4F6", "accent_hover": "#5B4BD6",
    "accent_bg": "rgba(108,92,231,0.07)",
    "sidebar": "#F8F8FE", "sb_border": "rgba(0,0,0,0.05)", "topbar": "rgba(255,255,255,0.9)",
    "menu_bg": "#FFFFFF", "scroll": "rgba(0,0,0,0.05)", "red": "#DC2626", "green": "#16A34A",
    "orange": "#D97706", "yellow": "#CA8A04", "is_dark": False,
}
_current_theme = DARK_THEME

CAT_COLORS = {
    "AI对话": "#7B6CF0", "AI开发": "#10B981", "AI绘图": "#F97316", "办公AI": "#3B82F6",
    "社交通讯": "#EAB308", "游戏娱乐": "#A78BFA", "购物电商": "#EC4899", "金融支付": "#06B6D4", "其他": "#6B7280",
}
STATUS_COLORS = {"inventory": ("#6B7280", "库存"), "rented": ("#3B82F6", "已出租"), "sold": ("#10B981", "已售出"), "recycled": ("#F97316", "已回收")}

NAV_ICONS = {"dashboard":"📊","all":"📋","customers":"👥","finance":"💰","security":"🛡️","recycle":"🗑️","logs":"📝"}

def build_qss(t):
    a1, a2 = t['accent'], t.get('accent2', t['accent_hover'])
    return f"""
* {{ font-family: 'Segoe UI Variable', 'Microsoft YaHei UI', system-ui, sans-serif; font-size: 13px; }}
QMainWindow, QWidget#content {{ background: {t['bg']}; }}
QDialog {{ background: {t['bg2']}; }}
QWidget#sidebar {{ background: {t['sidebar']}; border-right: 1px solid {t['sb_border']}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ width: 4px; background: transparent; margin: 4px 1px; }}
QScrollBar::handle:vertical {{ background: {t['scroll']}; border-radius: 2px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QLabel {{ color: {t['text']}; background: transparent; border: none; }}
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background: {t['input_bg']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 8px 12px; color: {t['text']}; font-size: 13px; selection-background-color: {t['accent_bg']};
}}
QLineEdit:focus, QTextEdit:focus {{ border-color: {a1}; }}
QComboBox {{
    background: {t['input_bg']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 8px 12px; color: {t['text']}; font-size: 13px;
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{ background: {t['menu_bg']}; border: 1px solid {t['border']}; color: {t['text']}; selection-background-color: {t['accent_bg']}; padding: 4px; border-radius: 8px; }}
QPushButton {{
    background: {t['card']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 8px 16px; color: {t['text']}; font-size: 13px; font-weight: 500;
}}
QPushButton:hover {{ background: {t['card_hover']}; }}
QPushButton#primary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {a1},stop:1 {a2});
    color: #FFFFFF; border: none; font-weight: 600; border-radius: 8px; padding: 8px 16px;
}}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {t['accent_hover']},stop:1 {a2}); }}
QPushButton#primary:disabled {{ background: {t['muted']}; color: rgba(255,255,255,0.4); }}
QPushButton#danger {{ background: {_rgba(t['red'], 0.08)}; border: 1px solid {_rgba(t['red'], 0.12)}; color: {t['red']}; border-radius: 8px; }}
QPushButton#danger:hover {{ background: {_rgba(t['red'], 0.16)}; }}
QPushButton#ghost {{ background: transparent; border: none; color: {a1}; padding: 6px 12px; font-weight: 500; border-radius: 8px; }}
QPushButton#ghost:hover {{ background: {t['accent_bg']}; }}
QPushButton#nav {{
    background: transparent; border: none; border-radius: 8px; padding: 9px 12px;
    color: {t['text2']}; font-size: 13px; font-weight: 500; text-align: left;
}}
QPushButton#nav:hover {{ background: {t['accent_bg']}; }}
QPushButton#nav:checked {{ background: {t['accent_bg']}; color: {a1}; font-weight: 700; border-left: 3px solid {a1}; }}
QCheckBox {{ color: {t['text']}; font-size: 13px; spacing: 6px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1.5px solid {t['muted']}; }}
QCheckBox::indicator:checked {{ background: {a1}; border-color: {a1}; }}
QMenu {{ background: {t['menu_bg']}; border: 1px solid {t['border']}; border-radius: 10px; padding: 4px; }}
QMenu::item {{ padding: 8px 20px 8px 14px; color: {t['text']}; border-radius: 6px; font-size: 13px; }}
QMenu::item:selected {{ background: {t['accent_bg']}; color: {a1}; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
QToolTip {{ background: {t['menu_bg']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 6px; padding: 6px 10px; font-size: 12px; }}
QStatusBar {{ background: {t['sidebar']}; color: {t['text2']}; font-size: 11px; border-top: 1px solid {t['sb_border']}; padding: 2px 8px; }}
QTabWidget::pane {{ border: 1px solid {t['border']}; border-radius: 8px; background: {t['bg']}; }}
QTabBar::tab {{ padding: 9px 18px; font-size: 13px; color: {t['muted']}; border: none; background: transparent; font-weight: 500; }}
QTabBar::tab:hover {{ color: {t['text']}; }}
QTabBar::tab:selected {{ color: {a1}; font-weight: 600; border-bottom: 2px solid {a1}; }}
"""

# ═══════════════════ Card Components ═══════════════════

class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        t = _current_theme
        self.setStyleSheet(f"Card {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:10px; }} Card:hover {{ background:{t['card_hover']}; }}")

class StatCard(Card):
    ICONS = {"总账号":"📋","正常":"✅","即将到期":"⏰","已过期":"⛔","月支出":"💸","年投入":"📈","库存":"📦","出租中":"🔄","已售出":"✅","月收入":"💰","健康":"🛡️","弱密码":"⚠️","重复":"🔁","空密码":"🔓","月成本":"💸","月收入":"💰","月利润":"📊","利润率":"📉","年成本":"📅","客户":"👥","账号":"📋"}
    def __init__(self, label, value, color=None, parent=None):
        super().__init__(parent)
        t = _current_theme; a2 = t.get('accent2', t['accent_hover'])
        color = color or t['accent']
        self.setFixedHeight(96)
        self.setStyleSheet(f"StatCard {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:10px; border-top:3px solid {color}; }} StatCard:hover {{ background:{t['card_hover']}; }}")
        lay = QHBoxLayout(self); lay.setContentsMargins(18, 14, 18, 14)
        col = QVBoxLayout(); col.setSpacing(4)
        lb = QLabel(label); lb.setStyleSheet(f"font-size:11px;color:{t['text2']};font-weight:500;")
        vl = QLabel(str(value)); vl.setStyleSheet(f"font-size:26px;font-weight:800;color:{color};")
        col.addWidget(lb); col.addWidget(vl)
        lay.addLayout(col); lay.addStretch()
        icon = self.ICONS.get(label, "")
        if icon:
            ic = QLabel(icon); ic.setStyleSheet(f"font-size:28px;color:{t['muted']};"); lay.addWidget(ic)
        self.val_label = vl

# ═══════════════════ Account Card ═══════════════════

class AccountCard(Card):
    edit_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    star_clicked = pyqtSignal(int)
    copy_clicked = pyqtSignal(str)
    focused = pyqtSignal(int)

    def __init__(self, acc, ws_type="personal", parent=None):
        super().__init__(parent)
        self.acc = acc; self.pwd_visible = False
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx_menu)
        if acc.get("notes"): self.setToolTip(acc["notes"])
        self._build(ws_type)

    def _build(self, ws_type):
        t = _current_theme; a = self.acc
        lay = QVBoxLayout(self); lay.setContentsMargins(20, 18, 20, 14); lay.setSpacing(0)

        top = QHBoxLayout(); top.setSpacing(8)
        star = QPushButton("★" if a["starred"] else "☆")
        star.setFixedSize(26, 26); star.setCursor(Qt.CursorShape.PointingHandCursor)
        star.setStyleSheet(f"border:none;background:transparent;font-size:16px;color:{'#FBBF24' if a['starred'] else t['muted']};padding:0;")
        star.clicked.connect(lambda: self.star_clicked.emit(a["id"])); top.addWidget(star)
        nm = QLabel(a["name"]); nm.setStyleSheet(f"font-size:16px;font-weight:700;color:{t['text']};"); top.addWidget(nm)
        if a["platform"]:
            pl = QLabel(f"· {a['platform']}"); pl.setStyleSheet(f"font-size:12px;color:{t['muted']};font-weight:400;"); top.addWidget(pl)
        top.addStretch()
        cc = CAT_COLORS.get(a["category"], "#6B7280")
        badge = QLabel(a["category"]); badge.setStyleSheet(f"font-size:10px;color:#fff;background:{cc};padding:3px 12px;border-radius:12px;font-weight:600;")
        top.addWidget(badge)
        s_map = {"active": ("正常", t["green"]), "expiring": ("即将到期", t["orange"]), "expired": ("已过期", t["red"])}
        st, stc = s_map.get(a["status"], ("正常", t["green"]))
        sb = QLabel(st); sb.setStyleSheet(f"font-size:10px;color:{stc};background:{_rgba(stc,0.15)};padding:3px 12px;border-radius:12px;font-weight:600;")
        top.addWidget(sb)
        if ws_type == "merchant":
            ac, at = STATUS_COLORS.get(a.get("account_status","inventory"), ("#6B7280","库存"))
            ab = QLabel(at); ab.setStyleSheet(f"font-size:10px;color:#fff;background:{ac};padding:3px 10px;border-radius:12px;font-weight:600;")
            top.addWidget(ab)
        lay.addLayout(top); lay.addSpacing(10)

        if a.get("customer_name") and ws_type == "merchant":
            cl = QLabel(f"👤 {a['customer_name']}"); cl.setStyleSheet(f"font-size:12px;color:{t['accent']};font-weight:500;"); lay.addWidget(cl); lay.addSpacing(6)

        cred = QHBoxLayout(); cred.setSpacing(6)
        if a["username"]:
            ub = QPushButton(f"👤 {a['username']}"); ub.setCursor(Qt.CursorShape.PointingHandCursor); ub.setToolTip("点击复制")
            ub.setStyleSheet(f"font-size:12px;color:{t['text2']};background:{t['input_bg']};padding:5px 10px;border-radius:6px;border:1px solid {t['border']};font-family:'Cascadia Code','Consolas',monospace;text-align:left;")
            ub.clicked.connect(lambda: self.copy_clicked.emit(a["username"])); cred.addWidget(ub)
        self.pwd_label = QLabel("🔒 ••••••••")
        self.pwd_label.setStyleSheet(f"font-size:12px;color:{t['muted']};background:{t['input_bg']};padding:5px 10px;border-radius:6px;border:1px solid {t['border']};font-family:'Cascadia Code','Consolas',monospace;")
        cred.addWidget(self.pwd_label)
        for icon, handler in [("👁", self._toggle_pwd), ("📋", lambda: self.copy_clicked.emit(a.get("password","")))]:
            b = QPushButton(icon); b.setFixedSize(30, 30); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"font-size:13px;padding:0;background:{t['accent_bg']};border:none;border-radius:8px;")
            b.clicked.connect(handler); cred.addWidget(b)
        cred.addStretch(); lay.addLayout(cred); lay.addSpacing(8)

        tags = a.get("tags", [])
        if isinstance(tags, str):
            try: tags = json.loads(tags) if tags else []
            except: tags = [x.strip() for x in tags.split(",") if x.strip()]
        if tags:
            tr = QHBoxLayout(); tr.setSpacing(4)
            for i, tag in enumerate(tags[:5]):
                tc = list(CAT_COLORS.values())[i % len(CAT_COLORS)]
                tl = QLabel(f"#{tag}"); tl.setStyleSheet(f"font-size:10px;color:{tc};background:{_rgba(tc,0.1)};padding:3px 10px;border-radius:10px;font-weight:500;")
                tr.addWidget(tl)
            tr.addStretch(); lay.addLayout(tr); lay.addSpacing(4)

        if a.get("api_key"):
            kl = QLabel(f"🔑 {a['api_key'][:16]}..."); kl.setStyleSheet(f"font-size:11px;color:{t['muted']};background:{t['input_bg']};padding:5px 12px;border-radius:10px;border:1px solid {t['border']};font-family:'Cascadia Code','Consolas',monospace;")
            lay.addWidget(kl); lay.addSpacing(4)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{t['border']};border:none;"); lay.addWidget(sep); lay.addSpacing(8)

        bot = QHBoxLayout(); bot.setSpacing(8)
        info_parts = []
        if a["monthly_cost"]: info_parts.append(f"💸 ¥{a['monthly_cost']}/月")
        if a.get("sell_price") and ws_type == "merchant": info_parts.append(f"💰 售¥{a['sell_price']}")
        if a["expire_date"]:
            dl = a.get("days_left")
            if dl is not None:
                dtxt = f"过期{abs(dl)}天" if dl < 0 else "今天到期" if dl == 0 else f"{dl}天后"
                clr = t["red"] if dl < 0 else t["orange"] if dl <= 7 else t['muted']
                el = QLabel(f"⏰ {dtxt}"); el.setStyleSheet(f"font-size:11px;color:{clr};font-weight:600;"); bot.addWidget(el)
        if a.get("auto_renew"):
            ar = QLabel("🔄 自动续费"); ar.setStyleSheet(f"font-size:10px;color:{t['green']};background:{_rgba(t['green'],0.1)};padding:2px 10px;border-radius:10px;font-weight:600;"); bot.addWidget(ar)
        if info_parts:
            il = QLabel("  ".join(info_parts)); il.setStyleSheet(f"font-size:11px;color:{t['muted']};"); bot.addWidget(il)
        bot.addStretch()
        for txt, handler, is_danger in [("打开", lambda: webbrowser.open(a["url"]), False), ("编辑", lambda: self.edit_clicked.emit(a["id"]), False), ("删除", lambda: self.delete_clicked.emit(a["id"]), True)]:
            if txt == "打开" and not a.get("url"): continue
            b = QPushButton(txt); b.setFixedHeight(30); b.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_danger:
                b.setStyleSheet(f"font-size:11px;padding:4px 14px;border-radius:10px;border:1px solid {_rgba(t['red'],0.15)};background:{_rgba(t['red'],0.06)};color:{t['red']};font-weight:500;")
            else:
                b.setStyleSheet(f"font-size:11px;padding:4px 14px;border-radius:10px;border:1px solid {t['border']};background:transparent;color:{t['accent']};font-weight:500;")
            b.clicked.connect(handler); bot.addWidget(b)
        lay.addLayout(bot)

    def mousePressEvent(self, e):
        super().mousePressEvent(e); self.focused.emit(self.acc["id"])
    def mouseDoubleClickEvent(self, e):
        super().mouseDoubleClickEvent(e); self.copy_clicked.emit(self.acc.get("password",""))
    def _toggle_pwd(self):
        t = _current_theme; self.pwd_visible = not self.pwd_visible
        if self.pwd_visible:
            self.pwd_label.setText(f"🔓 {self.acc.get('password','')}"); self.pwd_label.setStyleSheet(f"font-size:12px;color:{t['text']};background:{t['input_bg']};padding:5px 10px;border-radius:6px;border:1px solid {t['border']};font-family:'Cascadia Code','Consolas',monospace;")
            db.mark_accessed(self.acc["id"])
        else:
            self.pwd_label.setText("🔒 ••••••••"); self.pwd_label.setStyleSheet(f"font-size:12px;color:{t['muted']};background:{t['input_bg']};padding:5px 10px;border-radius:6px;border:1px solid {t['border']};font-family:'Cascadia Code','Consolas',monospace;")

    def _ctx_menu(self, pos):
        a = self.acc; m = QMenu(self)
        m.addAction("复制账号+密码", lambda: self.copy_clicked.emit(f"{a['username']}\n{a.get('password','')}"))
        m.addAction("复制用户名", lambda: self.copy_clicked.emit(a["username"]))
        m.addAction("复制密码", lambda: self.copy_clicked.emit(a.get("password","")))
        lines = [f"名称: {a['name']}"]
        if a.get("platform"): lines.append(f"平台: {a['platform']}")
        if a.get("username"): lines.append(f"用户名: {a['username']}")
        if a.get("password"): lines.append(f"密码: {a['password']}")
        if a.get("url"): lines.append(f"网址: {a['url']}")
        if a.get("api_key"): lines.append(f"API Key: {a['api_key']}")
        m.addAction("复制为文本", lambda: self.copy_clicked.emit("\n".join(lines)))
        m.addSeparator()
        if a.get("url"): m.addAction("打开网址", lambda: webbrowser.open(a["url"]))
        m.addAction("编辑", lambda: self.edit_clicked.emit(a["id"]))
        m.addSeparator()
        m.addAction("删除", lambda: self.delete_clicked.emit(a["id"]))
        m.exec(self.mapToGlobal(pos))

# ═══════════════════ Account Form Dialog ═══════════════════

class AccountDialog(QDialog):
    def __init__(self, parent, key, workspaces, cur_ws, ws_type, acc=None):
        super().__init__(parent)
        t = _current_theme; self.key = key; self.acc = acc
        self.setWindowTitle("编辑账号" if acc else "添加账号")
        self.setMinimumSize(560, 620)
        self.setStyleSheet(build_qss(t))
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        header = QWidget(); hl = QHBoxLayout(header); hl.setContentsMargins(32,20,32,12)
        title = QLabel("编辑账号" if acc else "添加账号"); title.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};")
        hl.addWidget(title); hl.addStretch(); root.addWidget(header)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        fw = QWidget(); form = QFormLayout(fw); form.setSpacing(8); form.setContentsMargins(32,8,32,20)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        sec_style = f"font-size:12px;font-weight:600;color:{t['text2']};padding:12px 0 4px 0;"

        s1 = QLabel("基本信息"); s1.setStyleSheet(sec_style); form.addRow(s1)
        self.ws_combo = QComboBox()
        for w in workspaces: self.ws_combo.addItem(f"{w['icon']} {w['name']}", w['name'])
        idx = self.ws_combo.findData(acc["workspace"] if acc else cur_ws)
        if idx >= 0: self.ws_combo.setCurrentIndex(idx)
        form.addRow("工作空间", self.ws_combo)
        self.cat_combo = QComboBox(); self.cat_combo.addItems(db.CATS); form.addRow("分类", self.cat_combo)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("例如 ChatGPT"); form.addRow("名称", self.name_edit)
        self.plat_edit = QLineEdit(); self.plat_edit.setPlaceholderText("例如 OpenAI"); form.addRow("平台", self.plat_edit)
        self.acc_status = QComboBox()
        for k, v in db.AS_MAP.items(): self.acc_status.addItem(v, k)
        form.addRow("业务状态", self.acc_status)

        s2 = QLabel("凭证"); s2.setStyleSheet(sec_style); form.addRow(s2)
        self.user_edit = QLineEdit(); self.user_edit.setPlaceholderText("邮箱 / 手机 / 用户名"); form.addRow("用户名", self.user_edit)
        self.pwd_edit = QLineEdit(); self.pwd_edit.setPlaceholderText("密码"); self.pwd_edit.textChanged.connect(self._upd_str); form.addRow("密码", self.pwd_edit)
        self.str_bar = QFrame(); self.str_bar.setFixedHeight(4); self.str_bar.setStyleSheet("background:transparent;border:none;border-radius:2px;")
        self.str_lbl = QLabel(""); self.str_lbl.setStyleSheet(f"font-size:12px;color:{t['muted']};")
        sr = QHBoxLayout(); sr.setSpacing(8); sr.addWidget(self.str_bar, 1); sr.addWidget(self.str_lbl); form.addRow("", sr)
        gr = QHBoxLayout(); gr.setSpacing(8)
        self.gen_result = QLineEdit(); self.gen_result.setReadOnly(True); self.gen_result.setPlaceholderText("点击生成随机密码")
        self.gen_result.setFixedHeight(34)
        gr.addWidget(self.gen_result)
        gb = QPushButton("生成"); gb.setObjectName("primary"); gb.setFixedSize(72, 34); gb.clicked.connect(self._gen_pwd); gr.addWidget(gb)
        ub = QPushButton("使用"); ub.setFixedSize(72, 34)
        ub.clicked.connect(lambda: (self.pwd_edit.setText(self.gen_result.text()), self._upd_str(self.gen_result.text()))); gr.addWidget(ub)
        form.addRow("随机密码", gr)
        gopts = QHBoxLayout(); gopts.setSpacing(12)
        self.gen_len = QSpinBox(); self.gen_len.setRange(8, 64); self.gen_len.setValue(16); self.gen_len.setFixedWidth(64); self.gen_len.setFixedHeight(28)
        gopts.addWidget(QLabel("长度")); gopts.addWidget(self.gen_len)
        self.gen_upper = QCheckBox("大写"); self.gen_upper.setChecked(True); gopts.addWidget(self.gen_upper)
        self.gen_digit = QCheckBox("数字"); self.gen_digit.setChecked(True); gopts.addWidget(self.gen_digit)
        self.gen_sym = QCheckBox("符号"); self.gen_sym.setChecked(True); gopts.addWidget(self.gen_sym)
        gopts.addStretch()
        form.addRow("", gopts)
        self.key_edit = QLineEdit(); self.key_edit.setPlaceholderText("sk-..."); form.addRow("API Key", self.key_edit)
        self.url_edit = QLineEdit(); self.url_edit.setPlaceholderText("https://..."); form.addRow("网址", self.url_edit)

        s3 = QLabel("费用"); s3.setStyleSheet(sec_style); form.addRow(s3)
        self.cost_edit = QDoubleSpinBox(); self.cost_edit.setMaximum(99999); self.cost_edit.setDecimals(2); form.addRow("月成本", self.cost_edit)
        self.sell_label = QLabel("售价/月"); self.sell_edit = QDoubleSpinBox(); self.sell_edit.setMaximum(99999); self.sell_edit.setDecimals(2); form.addRow(self.sell_label, self.sell_edit)
        self.income_label = QLabel("累计收入"); self.income_edit = QDoubleSpinBox(); self.income_edit.setMaximum(999999); self.income_edit.setDecimals(2); form.addRow(self.income_label, self.income_edit)
        self.exp_edit = QDateEdit(); self.exp_edit.setCalendarPopup(True); self.exp_edit.setSpecialValueText("无"); form.addRow("到期日期", self.exp_edit)

        self.cust_sec = QLabel("客户"); self.cust_sec.setStyleSheet(sec_style); form.addRow(self.cust_sec)
        self.cust_name = QLineEdit(); self.cust_name.setPlaceholderText("客户姓名"); self.cust_label = QLabel("客户"); form.addRow(self.cust_label, self.cust_name)
        self.cust_contact = QLineEdit(); self.cust_contact.setPlaceholderText("联系方式"); self.cust_contact_label = QLabel("联系方式"); form.addRow(self.cust_contact_label, self.cust_contact)

        s5 = QLabel("其他"); s5.setStyleSheet(sec_style); form.addRow(s5)
        self.tags_edit = QLineEdit(); self.tags_edit.setPlaceholderText("逗号分隔: 重要, VIP"); form.addRow("标签", self.tags_edit)
        self.notes_edit = QTextEdit(); self.notes_edit.setMaximumHeight(68); self.notes_edit.setPlaceholderText("备注..."); form.addRow("备注", self.notes_edit)
        self.star_check = QCheckBox("星标"); self.renew_check = QCheckBox("自动续费")
        ck = QHBoxLayout(); ck.addWidget(self.star_check); ck.addWidget(self.renew_check); ck.addStretch(); form.addRow("", ck)
        scroll.setWidget(fw); root.addWidget(scroll, 1)

        self._update_merchant(ws_type); self.ws_combo.currentIndexChanged.connect(self._on_ws)
        footer = QWidget(); btns = QHBoxLayout(footer); btns.setContentsMargins(32,8,32,16); btns.addStretch()
        cancel = QPushButton("取消"); cancel.setObjectName("ghost"); cancel.clicked.connect(self.reject); btns.addWidget(cancel)
        save = QPushButton("保存"); save.setObjectName("primary"); save.clicked.connect(self._save); btns.addWidget(save)
        root.addWidget(footer)

        if acc:
            self.cat_combo.setCurrentText(acc["category"]); self.name_edit.setText(acc["name"]); self.plat_edit.setText(acc["platform"])
            idx = self.acc_status.findData(acc["account_status"])
            if idx >= 0: self.acc_status.setCurrentIndex(idx)
            self.user_edit.setText(acc["username"]); self.pwd_edit.setText(acc.get("password","")); self.key_edit.setText(acc.get("api_key",""))
            self.url_edit.setText(acc["url"]); self.cost_edit.setValue(acc["monthly_cost"] or 0)
            self.sell_edit.setValue(acc.get("sell_price",0) or 0); self.income_edit.setValue(acc.get("total_income",0) or 0)
            if acc["expire_date"]:
                try: self.exp_edit.setDate(QDate.fromString(acc["expire_date"],"yyyy-MM-dd"))
                except: pass
            self.cust_name.setText(acc.get("customer_name","")); self.cust_contact.setText(acc.get("customer_contact",""))
            tags = acc.get("tags",[])
            if isinstance(tags, list): self.tags_edit.setText(", ".join(tags))
            elif isinstance(tags, str): self.tags_edit.setText(tags)
            self.notes_edit.setPlainText(acc.get("notes","")); self.star_check.setChecked(acc["starred"]); self.renew_check.setChecked(acc["auto_renew"])

    def _gen_pwd(self):
        self.gen_result.setText(db.generate_password(
            length=self.gen_len.value(), uppercase=self.gen_upper.isChecked(),
            digits=self.gen_digit.isChecked(), symbols=self.gen_sym.isChecked()))
    def _on_ws(self):
        ws = self.ws_combo.currentData(); self._update_merchant(db.get_workspace_type(ws) if ws else "personal")
    def _update_merchant(self, wt):
        m = wt == "merchant"
        for w in [self.sell_label, self.sell_edit, self.income_label, self.income_edit, self.cust_sec, self.cust_label, self.cust_name, self.cust_contact_label, self.cust_contact]: w.setVisible(m)
    def _upd_str(self, pwd):
        if not pwd: self.str_bar.setStyleSheet("background:transparent;border:none;border-radius:2px;"); self.str_lbl.setText(""); return
        s = sum([len(pwd)>=8, len(pwd)>=12, any(c.isupper() for c in pwd) and any(c.islower() for c in pwd), any(c.isdigit() for c in pwd), any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/~`" for c in pwd)])
        lvl = [("#FF3B30","极弱",20),("#FF9500","弱",40),("#FFCC00","中",60),("#34C759","强",80),("#30D158","极强",100)]
        c, txt, pct = lvl[min(s,4)]
        self.str_bar.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {c},stop:{pct/100} {c},stop:{pct/100+0.01} transparent,stop:1 transparent);border:none;border-radius:2px;")
        self.str_lbl.setText(txt); self.str_lbl.setStyleSheet(f"font-size:12px;color:{c};font-weight:600;")
    def _save(self):
        name = self.name_edit.text().strip()
        if not name: QMessageBox.warning(self,"提示","请填写名称"); return
        exp = ""
        if self.exp_edit.date() != self.exp_edit.minimumDate(): exp = self.exp_edit.date().toString("yyyy-MM-dd")
        data = {"workspace":self.ws_combo.currentData() or "","category":self.cat_combo.currentText(),"name":name,"platform":self.plat_edit.text().strip(),
            "account_status":self.acc_status.currentData(),"username":self.user_edit.text().strip(),"password":self.pwd_edit.text(),
            "api_key":self.key_edit.text().strip(),"url":self.url_edit.text().strip(),"monthly_cost":self.cost_edit.value(),
            "sell_price":self.sell_edit.value(),"total_income":self.income_edit.value(),"expire_date":exp,
            "customer_name":self.cust_name.text().strip(),"customer_contact":self.cust_contact.text().strip(),
            "notes":self.notes_edit.toPlainText().strip(),"starred":self.star_check.isChecked(),"auto_renew":self.renew_check.isChecked(),
            "tags":[x.strip() for x in self.tags_edit.text().split(",") if x.strip()]}
        try:
            if self.acc: db.update_account(self.acc["id"], data, self.key)
            else: db.create_account(data, self.key)
            self.accept()
        except Exception as e: QMessageBox.critical(self,"错误",str(e))

# ═══════════════════ Workspace Dialog ═══════════════════

class WorkspaceDialog(QDialog):
    def __init__(self, parent, edit_ws=None):
        super().__init__(parent); t = _current_theme; self.edit_ws = edit_ws
        self.setWindowTitle("编辑空间" if edit_ws else "新建工作空间"); self.setMinimumWidth(380)
        self.setStyleSheet(build_qss(t))
        lay = QVBoxLayout(self); lay.setContentsMargins(32,20,32,20); lay.setSpacing(12)
        tl = QLabel("编辑空间" if edit_ws else "新建工作空间"); tl.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};"); lay.addWidget(tl)
        form = QFormLayout(); form.setSpacing(8)
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("空间名称"); form.addRow("名称", self.name_edit)
        self.icon_edit = QLineEdit("📁"); self.icon_edit.setFixedWidth(68); form.addRow("图标", self.icon_edit)
        self.type_combo = QComboBox(); self.type_combo.addItem("个人空间","personal"); self.type_combo.addItem("经营空间","merchant"); form.addRow("类型", self.type_combo)
        lay.addLayout(form)
        if edit_ws:
            self.name_edit.setText(edit_ws["name"]); self.icon_edit.setText(edit_ws["icon"])
            idx = self.type_combo.findData(edit_ws.get("ws_type","personal"))
            if idx >= 0: self.type_combo.setCurrentIndex(idx)
        btns = QHBoxLayout(); btns.addStretch()
        c = QPushButton("取消"); c.setObjectName("ghost"); c.clicked.connect(self.reject); btns.addWidget(c)
        s = QPushButton("保存"); s.setObjectName("primary"); s.clicked.connect(self._save); btns.addWidget(s)
        lay.addLayout(btns)
    def _save(self):
        name = self.name_edit.text().strip()
        if not name: QMessageBox.warning(self,"提示","请填写名称"); return
        self.result_data = {"name":name,"icon":self.icon_edit.text().strip() or "📁","ws_type":self.type_combo.currentData()}; self.accept()

# ═══════════════════ Login Dialog ═══════════════════

class LoginDialog(QDialog):
    def __init__(self, is_init=False):
        super().__init__(); t = _current_theme
        self.setWindowTitle(APP_NAME); self.setFixedSize(380, 320)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.key = None
        card = QFrame(self); card.setGeometry(0,0,380,320)
        bg = t['bg'] if t['is_dark'] else "#FFFFFF"
        card.setStyleSheet(f"QFrame{{background:{bg};border-radius:16px;}}")
        if not t["is_dark"]:
            shadow = QGraphicsDropShadowEffect(card); shadow.setBlurRadius(40); shadow.setColor(QColor(0,0,0,20)); shadow.setOffset(0,4); card.setGraphicsEffect(shadow)
        lay = QVBoxLayout(card); lay.setContentsMargins(44,36,44,32); lay.setSpacing(0); lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl = QLabel(APP_NAME_SHORT); tl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tl.setStyleSheet(f"font-size:28px;font-weight:700;color:{t['text']};"); lay.addWidget(tl)
        lay.addSpacing(2)
        sub = QLabel("AegisVault"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"font-size:12px;color:{t['muted']};letter-spacing:3px;"); lay.addWidget(sub)
        lay.addSpacing(24)
        desc = QLabel("首次使用，请设置主密码" if is_init else "输入密码解锁"); desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"font-size:14px;color:{t['text2']};"); lay.addWidget(desc)
        lay.addSpacing(12)
        self.pwd_input = QLineEdit(); self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password); self.pwd_input.setPlaceholderText("主密码")
        self.pwd_input.setFixedHeight(42)
        self.pwd_input.setStyleSheet(f"font-size:14px;padding:0 14px;border-radius:8px;background:{t['input_bg']};border:1px solid {t['border']};color:{t['text']};")
        self.pwd_input.returnPressed.connect(self._submit); lay.addWidget(self.pwd_input)
        lay.addSpacing(12)
        btn = QPushButton("解锁" if not is_init else "设置"); btn.setFixedHeight(42); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"font-size:14px;font-weight:600;border-radius:8px;background:{t['accent']};color:#fff;border:none;")
        btn.clicked.connect(self._submit); lay.addWidget(btn)
        lay.addSpacing(8)
        self.err = QLabel(""); self.err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.err.setStyleSheet(f"font-size:12px;color:{t['red']};"); lay.addWidget(self.err)
        self.is_init = is_init; self._drag_pos = None
    def _submit(self):
        pwd = self.pwd_input.text()
        if len(pwd) < 4: self.err.setText("密码至少4位"); return
        try:
            if self.is_init: self.key = db.set_master_password(pwd)
            else:
                self.key = db.verify_password(pwd)
                if not self.key: self.err.setText("密码错误"); return
            self.accept()
        except Exception as e: self.err.setText(str(e))
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: self._drag_pos = e.globalPosition().toPoint() - self.pos()
    def mouseMoveEvent(self, e):
        if self._drag_pos: self.move(e.globalPosition().toPoint() - self._drag_pos)
    def mouseReleaseEvent(self, e): self._drag_pos = None

# ═══════════════════ Spotlight Search ═══════════════════

class SpotlightDialog(QDialog):
    account_selected = pyqtSignal(str, int)
    def __init__(self, parent, key):
        super().__init__(parent); t = _current_theme; self.key = key
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setFixedSize(520,400)
        card = QFrame(self); card.setGeometry(0,0,520,400)
        card.setStyleSheet(f"QFrame{{background:{t['bg2']};border:1px solid {t['border']};border-radius:16px;}}")
        if not t["is_dark"]:
            sh = QGraphicsDropShadowEffect(card); sh.setBlurRadius(50); sh.setColor(QColor(0,0,0,30)); sh.setOffset(0,6); card.setGraphicsEffect(sh)
        lay = QVBoxLayout(card); lay.setContentsMargins(20,16,20,16); lay.setSpacing(8)
        self.input = QLineEdit(); self.input.setPlaceholderText("搜索所有账号..."); self.input.setFixedHeight(44)
        self.input.setStyleSheet(f"font-size:16px;padding:0 16px;border-radius:12px;background:{t['input_bg']};border:1px solid {t['border']};color:{t['text']};")
        self.input.textChanged.connect(self._search); lay.addWidget(self.input)
        self.ra = QScrollArea(); self.ra.setWidgetResizable(True); self.ra.setStyleSheet("border:none;background:transparent;")
        self.rw = QWidget(); self.rl = QVBoxLayout(self.rw); self.rl.setContentsMargins(0,0,0,0); self.rl.setSpacing(4)
        self.ra.setWidget(self.rw); lay.addWidget(self.ra)
        h = QLabel("Ctrl+K  ·  跨空间搜索"); h.setStyleSheet(f"font-size:12px;color:{t['muted']};"); h.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(h)
    def _search(self, q):
        t = _current_theme
        while self.rl.count():
            item = self.rl.takeAt(0); w = item.widget()
            if w: w.setParent(None); w.deleteLater()
        if not q.strip(): return
        ql = q.lower(); results = []
        for ws in db.list_workspaces():
            for a in db.list_accounts(self.key, ws["name"]):
                if ql in a["name"].lower() or ql in a["platform"].lower() or ql in a["username"].lower():
                    a["_ws"] = ws["name"]; a["_ws_icon"] = ws["icon"]; results.append(a)
        for a in results[:15]:
            row = QPushButton(f"{a['_ws_icon']} {a['name']}  ·  {a['platform'] or a['category']}  ·  {a['_ws']}")
            row.setStyleSheet(f"text-align:left;padding:10px 14px;border-radius:8px;background:{t['card']};border:1px solid {t['border']};color:{t['text']};font-size:14px;")
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.clicked.connect(lambda _, ws=a["_ws"], aid=a["id"]: (self.account_selected.emit(ws, aid), self.accept()))
            self.rl.addWidget(row)
        if not results:
            el = QLabel("无匹配结果"); el.setStyleSheet(f"color:{t['muted']};font-size:14px;padding:20px;"); el.setAlignment(Qt.AlignmentFlag.AlignCenter); self.rl.addWidget(el)
        self.rl.addStretch()
    def showEvent(self, e): super().showEvent(e); self.input.setFocus(); self.input.clear()

# ═══════════════════ DeepSeek AI ═══════════════════

def _config_path(): return db.APP_DIR / "aegis_config.json"
DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

def _load_ai_config():
    p = _config_path()
    if p.exists():
        try: return json.loads(p.read_text(encoding='utf-8'))
        except: pass
    return {}
def _save_ai_config(cfg):
    p = _config_path(); old = {}
    if p.exists():
        try: old = json.loads(p.read_text(encoding='utf-8'))
        except: pass
    old.update(cfg); p.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding='utf-8')

def _deepseek_chat(api_key, messages, temperature=0.7, api_url=None, model=None):
    data = json.dumps({"model":model or DEFAULT_MODEL,"messages":messages,"temperature":temperature,"max_tokens":2000}).encode('utf-8')
    req = urllib.request.Request(api_url or DEFAULT_API_URL, data=data, headers={"Content-Type":"application/json","Authorization":f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=60) as resp: return json.loads(resp.read().decode('utf-8'))["choices"][0]["message"]["content"]

class AIWorker(QThread):
    finished = pyqtSignal(str); error = pyqtSignal(str)
    def __init__(self, api_key, messages, temp=0.7, api_url=None, model=None):
        super().__init__(); self.api_key=api_key; self.messages=messages; self.temp=temp; self.api_url=api_url; self.model=model
    def run(self):
        try: self.finished.emit(_deepseek_chat(self.api_key, self.messages, self.temp, self.api_url, self.model))
        except urllib.error.HTTPError as e:
            m = {401:"API Key 无效",403:"权限不足",429:"请求频繁",500:"服务器错误"}; self.error.emit(m.get(e.code, f"HTTP {e.code}"))
        except urllib.error.URLError as e: self.error.emit(f"网络错误: {e.reason}")
        except Exception as e: self.error.emit(str(e))

class AIAssistantDialog(QDialog):
    import_ready = pyqtSignal(list)
    def __init__(self, parent, enc_key, accounts, cur_ws, ws_type):
        super().__init__(parent); self.enc_key=enc_key; self.accounts=accounts; self.cur_ws=cur_ws; self.ws_type=ws_type
        self.worker=None; self._import_cache=[]; t=_current_theme
        self.setWindowTitle(f"{APP_NAME_SHORT} AI"); self.setMinimumSize(680,560)
        self.setStyleSheet(build_qss(t))
        lay = QVBoxLayout(self); lay.setContentsMargins(24,20,24,16); lay.setSpacing(12)
        hl = QHBoxLayout()
        hl.addWidget(QLabel("AI 助手") if not (tl := QLabel("AI 助手")) else tl); tl.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};")
        hl.addStretch(); lay.addLayout(hl)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_import(), "智能导入"); self.tabs.addTab(self._tab_autofill(), "智能填充")
        self.tabs.addTab(self._tab_saver(), "省钱顾问"); self.tabs.addTab(self._tab_report(), "月度报告")
        self.tabs.addTab(self._tab_security(), "安全分析"); self.tabs.addTab(self._tab_chat(), "智能问答")
        self.tabs.addTab(self._tab_customer(), "客户话术")
        lay.addWidget(self.tabs)
        cfg = _load_ai_config(); cb = Card()
        cl = QVBoxLayout(cb); cl.setContentsMargins(12,8,12,8); cl.setSpacing(6)
        r1 = QHBoxLayout(); r1.addWidget(QLabel("API Key")); self.key_input = QLineEdit(); self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-..."); self.key_input.setText(cfg.get("api_key","")); r1.addWidget(self.key_input); cl.addLayout(r1)
        r2 = QHBoxLayout(); r2.addWidget(QLabel("接口"))
        self.url_input = QComboBox(); self.url_input.addItems(["https://api.deepseek.com/v1/chat/completions","https://api.deepseek.com/chat/completions","https://api.openai.com/v1/chat/completions"])
        su = cfg.get("api_url","")
        if su:
            idx = self.url_input.findText(su)
            if idx >= 0: self.url_input.setCurrentIndex(idx)
        r2.addWidget(self.url_input,1); r2.addWidget(QLabel("模型"))
        self.model_input = QComboBox(); self.model_input.setMaximumWidth(180)
        self.model_input.addItems(["deepseek-chat","deepseek-reasoner","gpt-4o","gpt-4o-mini","gpt-3.5-turbo"])
        sm = cfg.get("model","")
        if sm:
            idx = self.model_input.findText(sm)
            if idx >= 0: self.model_input.setCurrentIndex(idx)
        r2.addWidget(self.model_input); cl.addLayout(r2)
        r3 = QHBoxLayout()
        sb = QPushButton("保存配置"); sb.setObjectName("primary"); sb.setFixedHeight(30); sb.clicked.connect(self._save_cfg); r3.addWidget(sb)
        self.status_label = QLabel(""); self.status_label.setStyleSheet(f"font-size:12px;color:{t['muted']};"); r3.addWidget(self.status_label); r3.addStretch()
        cl.addLayout(r3); lay.addWidget(cb)

    def _save_cfg(self): _save_ai_config({"api_key":self.key_input.text().strip(),"api_url":self.url_input.currentText().strip(),"model":self.model_input.currentText().strip()}); self._toast("已保存")
    def _get_key(self):
        k = self.key_input.text().strip()
        if not k: self._toast("请设置 API Key"); return None
        return k
    def _toast(self, msg): self.status_label.setText(msg)
    def _loading(self, on): self.status_label.setText("处理中..." if on else ""); self.setCursor(Qt.CursorShape.WaitCursor if on else Qt.CursorShape.ArrowCursor)
    def _run(self, msgs, cb, temp=0.7):
        key = self._get_key()
        if not key: return
        self._loading(True)
        self.worker = AIWorker(key, msgs, temp, self.url_input.currentText().strip() or None, self.model_input.currentText().strip() or None)
        self.worker.finished.connect(lambda r: (self._loading(False), cb(r)))
        self.worker.error.connect(lambda e: (self._loading(False), self._toast(f"错误: {e}"))); self.worker.start()

    def _tab_import(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("粘贴包含账号信息的文本，AI 自动提取:"))
        self.import_input = QTextEdit(); self.import_input.setPlaceholderText("邮件、聊天记录、笔记等..."); self.import_input.setMinimumHeight(120); lay.addWidget(self.import_input)
        pb = QPushButton("AI 解析"); pb.setObjectName("primary"); pb.clicked.connect(self._do_parse); lay.addWidget(pb)
        self.import_result = QTextEdit(); self.import_result.setReadOnly(True); self.import_result.setPlaceholderText("解析结果..."); lay.addWidget(self.import_result)
        ib = QPushButton("确认导入"); ib.setObjectName("primary"); ib.clicked.connect(self._do_confirm); lay.addWidget(ib); return w
    def _do_parse(self):
        text = self.import_input.toPlainText().strip()
        if not text: self._toast("请粘贴文本"); return
        self._run([{"role":"system","content":"你是账号信息提取助手。从文本中提取账号信息，返回JSON数组。字段：name,platform,username,password,url,api_key,category(AI对话/AI开发/AI绘图/办公AI/社交通讯/游戏娱乐/购物电商/金融支付/其他),expire_date(yyyy-MM-dd),monthly_cost,notes。只返回JSON。"},{"role":"user","content":text}], self._on_parsed, 0.3)
    def _on_parsed(self, result):
        try:
            s, e = result.find('['), result.rfind(']')+1
            if s >= 0 and e > s:
                data = json.loads(result[s:e]); self._import_cache = data
                lines = []
                for i, d in enumerate(data):
                    lines.append(f"--- 账号 {i+1} ---"); lines.append(f"  名称: {d.get('name','')}"); lines.append(f"  平台: {d.get('platform','')}")
                    lines.append(f"  用户名: {d.get('username','')}"); lines.append(f"  密码: {d.get('password','')}"); lines.append(f"  分类: {d.get('category','')}"); lines.append("")
                self.import_result.setPlainText("\n".join(lines)); self._toast(f"解析到 {len(data)} 个账号")
            else: self.import_result.setPlainText(result); self._toast("格式异常")
        except Exception as ex: self.import_result.setPlainText(result); self._toast(f"解析失败: {ex}")
    def _do_confirm(self):
        if not self._import_cache: self._toast("请先解析"); return
        count = 0
        for d in self._import_cache:
            try:
                db.create_account({"workspace":self.cur_ws,"category":d.get("category","其他"),"name":d.get("name","未知"),"platform":d.get("platform",""),
                    "account_status":"inventory","username":d.get("username",""),"password":d.get("password",""),"api_key":d.get("api_key",""),
                    "url":d.get("url",""),"monthly_cost":float(d.get("monthly_cost",0) or 0),"sell_price":0,"total_income":0,
                    "expire_date":d.get("expire_date",""),"customer_name":"","customer_contact":"","notes":d.get("notes",""),
                    "starred":False,"auto_renew":False,"tags":[]}, self.enc_key); count += 1
            except: pass
        self._import_cache = []; self._toast(f"已导入 {count} 个"); self.import_ready.emit(self.accounts)

    def _tab_customer(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("选择客户，生成话术:"))
        self.cust_combo = QComboBox(); self._all_customers = {}
        for ws in db.list_workspaces():
            if ws.get("ws_type") != "merchant": continue
            for a in db.list_accounts(self.enc_key, ws["name"]):
                cn = (a.get("customer_name") or "").strip()
                if cn:
                    if cn not in self._all_customers: self._all_customers[cn] = []
                    a["_ws"] = ws["name"]; self._all_customers[cn].append(a)
        for cn in sorted(self._all_customers.keys()): self.cust_combo.addItem(f"{cn} ({len(self._all_customers[cn])}个账号)", cn)
        lay.addWidget(self.cust_combo)
        self.cust_type = QComboBox(); self.cust_type.addItems(["续费提醒","新品推荐","优惠活动","到期警告"]); lay.addWidget(self.cust_type)
        gb = QPushButton("生成话术"); gb.setObjectName("primary"); gb.clicked.connect(self._do_cust); lay.addWidget(gb)
        self.cust_result = QTextEdit(); self.cust_result.setReadOnly(True); self.cust_result.setPlaceholderText("话术..."); lay.addWidget(self.cust_result)
        cpb = QPushButton("复制"); cpb.setObjectName("ghost"); cpb.clicked.connect(lambda: QApplication.clipboard().setText(self.cust_result.toPlainText()) or self._toast("已复制")); lay.addWidget(cpb)
        if not self._all_customers: lay.addWidget(QLabel("暂无客户信息"))
        return w
    def _do_cust(self):
        cn = self.cust_combo.currentData()
        if not cn: self._toast("请选择客户"); return
        accs = self._all_customers.get(cn, []); mt = self.cust_type.currentText()
        info = "\n".join([f"- {a['name']}（{a['category']}），月费¥{a.get('sell_price',0) or a.get('monthly_cost',0)}，到期:{a.get('expire_date','未设置')}" for a in accs])
        self._run([{"role":"system","content":"你是客户服务助手。语气专业友好，直接输出可发给客户的消息。"},{"role":"user","content":f"客户：{cn}\n类型：{mt}\n账号：\n{info}\n\n生成{mt}消息。"}], lambda r: self.cust_result.setPlainText(r))

    def _tab_security(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("AI 分析账号安全状况:"))
        ab = QPushButton("开始分析"); ab.setObjectName("primary"); ab.clicked.connect(self._do_sec); lay.addWidget(ab)
        self.sec_result = QTextEdit(); self.sec_result.setReadOnly(True); self.sec_result.setPlaceholderText("分析报告..."); lay.addWidget(self.sec_result); return w
    def _do_sec(self):
        try: sec = db.security_analysis(self.enc_key, self.cur_ws)
        except: self._toast("分析失败"); return
        sm = sec["summary"]; details = []
        for a in sec["accounts"][:20]:
            issues = [x for x in [("弱密码" if a["weak"] else ""),("重复" if a["duplicate"] else ""),("空密码" if a["empty"] else "")] if x]
            details.append(f"- {a['name']}: {a['health']}分 {'，'.join(issues) if issues else '安全'}")
        self._run([{"role":"system","content":"你是安全顾问。分析数据给出建议：整体评价、高危、中危、改进建议。中文回答。"},
            {"role":"user","content":f"总账号:{sm['total']}\n平均健康:{sm['avg_health']}\n弱密码:{sm['weak']}\n重复:{sm['duplicate']}\n空密码:{sm['empty']}\n\n详情:\n"+"\n".join(details)}], lambda r: self.sec_result.setPlainText(r))

    def _acc_summary(self):
        lines = []
        for a in self.accounts[:50]:
            parts = [a['name']]
            if a.get('platform'): parts.append(f"平台:{a['platform']}")
            if a.get('category'): parts.append(f"分类:{a['category']}")
            if a.get('monthly_cost'): parts.append(f"月费:¥{a['monthly_cost']}")
            if a.get('expire_date'): parts.append(f"到期:{a['expire_date']}")
            if a.get('status') == 'expired': parts.append("已过期")
            elif a.get('status') == 'expiring': parts.append(f"{a.get('days_left','')}天后到期")
            if a.get('auto_renew'): parts.append("自动续费")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    def _tab_chat(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("基于你的账号数据智能问答（如：哪些账号下月到期？最贵的订阅是哪个？）"))
        self.chat_result = QTextEdit(); self.chat_result.setReadOnly(True); self.chat_result.setPlaceholderText("回答..."); lay.addWidget(self.chat_result)
        ir = QHBoxLayout()
        self.chat_input = QLineEdit(); self.chat_input.setPlaceholderText("输入问题..."); self.chat_input.returnPressed.connect(self._do_chat); ir.addWidget(self.chat_input)
        sb = QPushButton("发送"); sb.setObjectName("primary"); sb.setFixedWidth(70); sb.clicked.connect(self._do_chat); ir.addWidget(sb)
        lay.addLayout(ir); return w
    def _do_chat(self):
        q = self.chat_input.text().strip()
        if not q: return
        summary = self._acc_summary()
        ctx = f"用户空间「{self.cur_ws}」（{'经营' if self.ws_type=='merchant' else '个人'}），{len(self.accounts)}个账号。\n\n账号列表:\n{summary}"
        self.chat_input.clear(); prev = self.chat_result.toPlainText()
        self.chat_result.setPlainText(prev + ("\n\n" if prev else "") + f"Q: {q}\n\n思考中...")
        self._run([{"role":"system","content":f"你是密盾AI助手，可以回答关于用户账号的任何问题。根据以下数据回答，中文简洁。\n\n{ctx}"},{"role":"user","content":q}],
            lambda r: self.chat_result.setPlainText(prev + ("\n\n" if prev else "") + f"Q: {q}\n\nA: {r}"))

    def _tab_saver(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("AI 分析你的订阅，找出省钱方案:"))
        ab = QPushButton("分析省钱方案"); ab.setObjectName("primary"); ab.clicked.connect(self._do_saver); lay.addWidget(ab)
        self.saver_result = QTextEdit(); self.saver_result.setReadOnly(True); self.saver_result.setPlaceholderText("省钱分析报告..."); lay.addWidget(self.saver_result)
        cpb = QPushButton("复制报告"); cpb.setObjectName("ghost"); cpb.clicked.connect(lambda: QApplication.clipboard().setText(self.saver_result.toPlainText()) or self._toast("已复制")); lay.addWidget(cpb)
        return w
    def _do_saver(self):
        if not self.accounts: self._toast("暂无账号数据"); return
        lines = []
        for a in self.accounts:
            if a.get("monthly_cost"): lines.append(f"- {a['name']}（{a.get('category','')}，{a.get('platform','')}）: ¥{a['monthly_cost']}/月")
        if not lines: self._toast("暂无付费账号"); return
        total = sum(a.get("monthly_cost",0) or 0 for a in self.accounts)
        self._run([{"role":"system","content":"你是订阅省钱顾问。根据用户的订阅列表，分析：1.哪些服务功能重叠可以合并 2.哪些有更便宜的替代品 3.哪些可能不常用建议取消 4.给出具体省钱方案和预计每月节省金额。中文回答，实用具体。"},
            {"role":"user","content":f"我的订阅列表（月总支出¥{total}）：\n"+"\n".join(lines)}], lambda r: self.saver_result.setPlainText(r))

    def _tab_autofill(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("输入服务名称，AI 自动补全平台、分类、网址、参考价格:"))
        ir = QHBoxLayout()
        self.fill_input = QLineEdit(); self.fill_input.setPlaceholderText("如: ChatGPT、Notion、微信..."); self.fill_input.returnPressed.connect(self._do_fill); ir.addWidget(self.fill_input)
        fb = QPushButton("查询"); fb.setObjectName("primary"); fb.setFixedWidth(70); fb.clicked.connect(self._do_fill); ir.addWidget(fb)
        lay.addLayout(ir)
        self.fill_result = QTextEdit(); self.fill_result.setReadOnly(True); self.fill_result.setPlaceholderText("查询结果..."); lay.addWidget(self.fill_result)
        self.fill_data = None
        ub = QPushButton("用此信息添加账号"); ub.setObjectName("primary"); ub.clicked.connect(self._use_fill); lay.addWidget(ub)
        return w
    def _do_fill(self):
        name = self.fill_input.text().strip()
        if not name: self._toast("请输入服务名称"); return
        self._run([{"role":"system","content":"你是账号信息助手。用户输入一个服务/产品名称，返回JSON对象（不要markdown代码块），字段：name(标准名称),platform(所属公司),category(从AI对话/AI开发/AI绘图/办公AI/社交通讯/游戏娱乐/购物电商/金融支付/其他中选),url(官网),monthly_cost_cny(月费人民币,免费填0)。只返回JSON。"},
            {"role":"user","content":name}], self._on_fill, 0.3)
    def _on_fill(self, result):
        try:
            s = result.find('{'); e = result.rfind('}')+1
            if s >= 0 and e > s:
                self.fill_data = json.loads(result[s:e])
                d = self.fill_data
                self.fill_result.setPlainText(f"名称: {d.get('name','')}\n平台: {d.get('platform','')}\n分类: {d.get('category','')}\n网址: {d.get('url','')}\n参考月费: ¥{d.get('monthly_cost_cny',0)}")
                self._toast("查询成功，点击下方按钮可添加")
            else: self.fill_result.setPlainText(result); self._toast("格式异常")
        except Exception as ex: self.fill_result.setPlainText(result); self._toast(f"解析失败: {ex}")
    def _use_fill(self):
        if not self.fill_data: self._toast("请先查询"); return
        d = self.fill_data
        try:
            db.create_account({"workspace":self.cur_ws,"category":d.get("category","其他"),"name":d.get("name",""),
                "platform":d.get("platform",""),"username":"","password":"","api_key":"",
                "url":d.get("url",""),"monthly_cost":float(d.get("monthly_cost_cny",0) or 0),
                "sell_price":0,"total_income":0,"expire_date":"","account_status":"inventory",
                "customer_name":"","customer_contact":"","notes":"","starred":False,"auto_renew":False,"tags":[]}, self.enc_key)
            self._toast(f"已添加「{d.get('name','')}」"); self.import_ready.emit(self.accounts); self.fill_data = None
        except Exception as ex: self._toast(f"添加失败: {ex}")

    def _tab_report(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20,12,20,12); lay.setSpacing(12)
        lay.addWidget(QLabel("生成账号管理月度报告:"))
        ab = QPushButton("生成月度报告"); ab.setObjectName("primary"); ab.clicked.connect(self._do_report); lay.addWidget(ab)
        self.report_result = QTextEdit(); self.report_result.setReadOnly(True); self.report_result.setPlaceholderText("月度报告..."); lay.addWidget(self.report_result)
        cpb = QPushButton("复制报告"); cpb.setObjectName("ghost"); cpb.clicked.connect(lambda: QApplication.clipboard().setText(self.report_result.toPlainText()) or self._toast("已复制")); lay.addWidget(cpb)
        return w
    def _do_report(self):
        if not self.accounts: self._toast("暂无账号数据"); return
        try: sec = db.security_analysis(self.enc_key, self.cur_ws)
        except: sec = {"summary":{"avg_health":0,"weak":0,"duplicate":0,"empty":0}}
        sm = sec["summary"]; cats = {}; total_cost = 0; expiring = 0; expired = 0
        for a in self.accounts:
            cats[a["category"]] = cats.get(a["category"], 0) + 1
            total_cost += a.get("monthly_cost", 0) or 0
            if a.get("status") == "expiring": expiring += 1
            elif a.get("status") == "expired": expired += 1
        cat_str = ", ".join(f"{k}:{v}个" for k, v in sorted(cats.items(), key=lambda x:-x[1]))
        self._run([{"role":"system","content":"你是账号管理顾问。根据用户数据生成一份月度报告，包含：1.总览 2.费用分析 3.安全评分与建议 4.到期提醒 5.优化建议。格式清晰、中文、实用。"},
            {"role":"user","content":f"空间:「{self.cur_ws}」\n总账号:{len(self.accounts)}\n分类分布:{cat_str}\n月总支出:¥{total_cost}\n年支出:¥{total_cost*12}\n即将到期:{expiring}个\n已过期:{expired}个\n安全评分:{sm['avg_health']}\n弱密码:{sm['weak']}\n重复密码:{sm['duplicate']}\n空密码:{sm['empty']}"}],
            lambda r: self.report_result.setPlainText(r))

# ═══════════════════ Batch Import Dialog ═══════════════════

class BatchImportDialog(QDialog):
    def __init__(self, parent, key, workspaces, cur_ws, ws_type):
        super().__init__(parent)
        t = _current_theme; self.key = key; self.cur_ws = cur_ws; self._parsed = []
        self.setWindowTitle("批量添加账号"); self.setMinimumSize(700, 640)
        self.setStyleSheet(build_qss(t))
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        header = QWidget(); hl = QHBoxLayout(header); hl.setContentsMargins(32,20,32,12)
        title = QLabel("批量添加账号"); title.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};")
        hl.addWidget(title); hl.addStretch(); root.addWidget(header)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        sw = QWidget(); lay = QVBoxLayout(sw); lay.setContentsMargins(32,8,32,20); lay.setSpacing(14)

        # ── 导入目标 ──
        tgt = QFrame(); tgt.setStyleSheet(f"QFrame{{background:{t['card']};border:1px solid {t['border']};border-radius:10px;}}")
        tl = QHBoxLayout(tgt); tl.setContentsMargins(16,10,16,10); tl.setSpacing(14)
        dl = QLabel("导入到"); dl.setStyleSheet(f"font-size:13px;font-weight:600;color:{t['text2']};"); tl.addWidget(dl)
        self.ws_combo = QComboBox()
        for w in workspaces: self.ws_combo.addItem(f"{w['icon']} {w['name']}", w['name'])
        idx = self.ws_combo.findData(cur_ws)
        if idx >= 0: self.ws_combo.setCurrentIndex(idx)
        tl.addWidget(self.ws_combo)
        sep = QFrame(); sep.setFixedWidth(1); sep.setStyleSheet(f"background:{t['border']};"); tl.addWidget(sep)
        cl = QLabel("默认分类"); cl.setStyleSheet(f"font-size:13px;font-weight:600;color:{t['text2']};"); tl.addWidget(cl)
        self.cat_combo = QComboBox(); self.cat_combo.addItems(db.CATS); tl.addWidget(self.cat_combo)
        tl.addStretch()
        lay.addWidget(tgt)

        self.tabs = QTabWidget()

        # ── Tab 1: 快速粘贴 ──
        t1 = QWidget(); t1l = QVBoxLayout(t1); t1l.setContentsMargins(16,14,16,14); t1l.setSpacing(10)
        help1 = QFrame(); help1.setStyleSheet(f"QFrame{{background:{t['card']};border:1px solid {t['border']};border-radius:10px;}}")
        h1l = QVBoxLayout(help1); h1l.setContentsMargins(18,14,18,14); h1l.setSpacing(8)
        ht = QLabel("📋 格式说明"); ht.setStyleSheet(f"font-size:14px;font-weight:700;color:{t['text']};"); h1l.addWidget(ht)
        h1l.addWidget(self._help_line(t, "每行一个账号，字段用 英文逗号 或 Tab 分隔"))
        fmts = QFrame(); fmts.setStyleSheet(f"QFrame{{background:{t['input_bg']};border-radius:8px;border:none;}}")
        fml = QVBoxLayout(fmts); fml.setContentsMargins(14,10,14,10); fml.setSpacing(6)
        for label, fmt in [("基础","名称, 用户名, 密码"), ("含平台","名称, 用户名, 密码, 平台"), ("完整","名称, 用户名, 密码, 平台, 网址, 月成本")]:
            fml.addWidget(self._fmt_line(t, label, fmt))
        h1l.addWidget(fmts)
        tip = QLabel("💡 从 Excel 复制多行直接粘贴即可（Tab分隔自动识别）")
        tip.setStyleSheet(f"font-size:12px;color:{t['accent']};font-weight:500;"); h1l.addWidget(tip)
        ex = QLabel("示例：\nChatGPT, user@mail.com, myPassword123\nClaude Pro, test@gmail.com, pwd456, Anthropic\nCursor, dev@mail.com, pass789, Cursor, https://cursor.sh, 140")
        ex.setWordWrap(True); ex.setStyleSheet(f"font-size:12px;color:{t['text2']};background:{t['input_bg']};padding:10px;border-radius:8px;font-family:'Cascadia Code','Consolas',monospace;border:none;")
        h1l.addWidget(ex); t1l.addWidget(help1)
        self.text_input = QTextEdit(); self.text_input.setPlaceholderText("在此粘贴账号数据，每行一个..."); self.text_input.setMinimumHeight(140); t1l.addWidget(self.text_input)
        self.tabs.addTab(t1, "  快速粘贴  ")

        # ── Tab 2: CSV 导入 ──
        t2 = QWidget(); t2l = QVBoxLayout(t2); t2l.setContentsMargins(16,14,16,14); t2l.setSpacing(10)
        help2 = QFrame(); help2.setStyleSheet(f"QFrame{{background:{t['card']};border:1px solid {t['border']};border-radius:10px;}}")
        h2l = QVBoxLayout(help2); h2l.setContentsMargins(18,14,18,14); h2l.setSpacing(8)
        ct = QLabel("📋 CSV 格式说明"); ct.setStyleSheet(f"font-size:14px;font-weight:700;color:{t['text']};"); h2l.addWidget(ct)
        h2l.addWidget(self._help_line(t, "第一行必须是英文表头，数据从第二行开始"))
        fields = QFrame(); fields.setStyleSheet(f"QFrame{{background:{t['input_bg']};border-radius:8px;border:none;}}")
        fl = QVBoxLayout(fields); fl.setContentsMargins(14,10,14,10); fl.setSpacing(4)
        for fn, fd, req in [
            ("name","名称","必填"), ("username","用户名/邮箱/手机",""), ("password","密码",""),
            ("category","分类 (AI对话/AI开发/AI绘图/办公AI/社交通讯/游戏娱乐/购物电商/金融支付/其他)",""),
            ("platform","平台",""), ("url","网址",""), ("monthly_cost","月成本(数字)",""),
            ("sell_price","售价(数字)",""), ("expire_date","到期日期 (yyyy-MM-dd)",""),
            ("customer_name","客户名称",""), ("notes","备注",""), ("tags","标签 (用|分隔多个)",""),
        ]:
            r = QHBoxLayout(); r.setSpacing(6)
            nm = QLabel(fn); nm.setFixedWidth(120); nm.setStyleSheet(f"font-size:12px;font-weight:600;color:{t['accent']};font-family:'Cascadia Code','Consolas',monospace;"); r.addWidget(nm)
            ds = QLabel(fd); ds.setStyleSheet(f"font-size:12px;color:{t['text2']};"); r.addWidget(ds)
            if req:
                rq = QLabel(req); rq.setStyleSheet(f"font-size:10px;color:{t['red']};font-weight:600;background:{_rgba(t['red'],0.1)};padding:1px 6px;border-radius:3px;"); r.addWidget(rq)
            r.addStretch(); fl.addLayout(r)
        h2l.addWidget(fields)
        ex2 = QLabel("示例：\nname,username,password,category,platform,monthly_cost\nChatGPT,user@mail.com,pwd123,AI对话,OpenAI,140\nClaude,test@mail.com,pwd456,AI对话,Anthropic,140")
        ex2.setWordWrap(True); ex2.setStyleSheet(f"font-size:12px;color:{t['text2']};background:{t['input_bg']};padding:10px;border-radius:8px;font-family:'Cascadia Code','Consolas',monospace;border:none;")
        h2l.addWidget(ex2); t2l.addWidget(help2)
        self.csv_input = QTextEdit(); self.csv_input.setPlaceholderText("在此粘贴CSV数据（含表头）..."); self.csv_input.setMinimumHeight(140); t2l.addWidget(self.csv_input)
        self.tabs.addTab(t2, "  CSV 导入  ")
        lay.addWidget(self.tabs)

        pb = QPushButton("解析预览"); pb.setObjectName("primary"); pb.clicked.connect(self._parse); lay.addWidget(pb)

        self.preview_label = QLabel(""); lay.addWidget(self.preview_label)
        self.preview_area = QScrollArea(); self.preview_area.setWidgetResizable(True); self.preview_area.setMaximumHeight(200)
        self.preview_area.setStyleSheet(f"QScrollArea{{border:1px solid {t['border']};border-radius:8px;background:{t['input_bg']};}}")
        self.preview_widget = QWidget(); self.preview_layout = QVBoxLayout(self.preview_widget)
        self.preview_layout.setContentsMargins(12,8,12,8); self.preview_layout.setSpacing(2)
        self.preview_area.setWidget(self.preview_widget); self.preview_area.setVisible(False); lay.addWidget(self.preview_area)

        scroll.setWidget(sw); root.addWidget(scroll, 1)

        footer = QFrame(); footer.setStyleSheet(f"QFrame{{background:{t['bg2']};border-top:1px solid {t['border']};}}")
        btns = QHBoxLayout(footer); btns.setContentsMargins(32,12,32,16); btns.addStretch()
        cancel = QPushButton("取消"); cancel.setObjectName("ghost"); cancel.clicked.connect(self.reject); btns.addWidget(cancel)
        self.import_btn = QPushButton("确认导入"); self.import_btn.setObjectName("primary"); self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._do_import); btns.addWidget(self.import_btn); root.addWidget(footer)

    def _help_line(self, t, text):
        l = QLabel(text); l.setWordWrap(True); l.setStyleSheet(f"font-size:12px;color:{t['text2']};"); return l

    def _fmt_line(self, t, label, fmt):
        w = QWidget(); r = QHBoxLayout(w); r.setContentsMargins(0,0,0,0); r.setSpacing(8)
        lb = QLabel(label); lb.setFixedWidth(50); lb.setStyleSheet(f"font-size:12px;font-weight:700;color:{t['accent']};"); r.addWidget(lb)
        fv = QLabel(fmt); fv.setStyleSheet(f"font-size:12px;color:{t['text']};font-family:'Cascadia Code','Consolas',monospace;"); r.addWidget(fv); r.addStretch()
        return w

    def _parse(self):
        t = _current_theme; self._parsed = []
        ws = self.ws_combo.currentData() or self.cur_ws; default_cat = self.cat_combo.currentText()
        tab_idx = self.tabs.currentIndex()

        if tab_idx == 0:
            text = self.text_input.toPlainText().strip()
            if not text: self._show_status("⚠ 请粘贴数据", t['orange']); return
            for line in text.splitlines():
                line = line.strip()
                if not line: continue
                parts = [p.strip() for p in line.split('\t')] if '\t' in line else [p.strip() for p in line.split(',')]
                if not parts or not parts[0]: continue
                cost = 0
                if len(parts) > 5:
                    try: cost = float(parts[5])
                    except: pass
                self._parsed.append({"name": parts[0], "username": parts[1] if len(parts) > 1 else "",
                    "password": parts[2] if len(parts) > 2 else "", "platform": parts[3] if len(parts) > 3 else "",
                    "url": parts[4] if len(parts) > 4 else "", "monthly_cost": cost,
                    "category": default_cat, "workspace": ws, "account_status": "inventory",
                    "sell_price": 0, "total_income": 0, "expire_date": "", "customer_name": "",
                    "customer_contact": "", "notes": "", "starred": False, "auto_renew": False, "tags": []})
        else:
            text = self.csv_input.toPlainText().strip()
            if not text: self._show_status("⚠ 请粘贴CSV数据", t['orange']); return
            try:
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    name = row.get("name", "").strip()
                    if not name: continue
                    cost = 0; sell = 0
                    try: cost = float(row.get("monthly_cost", 0) or 0)
                    except: pass
                    try: sell = float(row.get("sell_price", 0) or 0)
                    except: pass
                    tags = [x.strip() for x in row.get("tags", "").split("|") if x.strip()]
                    self._parsed.append({"name": name, "username": row.get("username", "").strip(),
                        "password": row.get("password", "").strip(), "platform": row.get("platform", "").strip(),
                        "url": row.get("url", "").strip(), "monthly_cost": cost, "sell_price": sell,
                        "category": row.get("category", "").strip() or default_cat,
                        "expire_date": row.get("expire_date", "").strip(),
                        "customer_name": row.get("customer_name", "").strip(),
                        "customer_contact": "", "notes": row.get("notes", "").strip(),
                        "account_status": "inventory", "total_income": 0,
                        "starred": False, "auto_renew": False, "tags": tags, "workspace": ws})
            except Exception as e:
                self._show_status(f"❌ CSV 解析失败: {e}", t['red']); return

        if not self._parsed:
            self._show_status("⚠ 未解析到有效数据，请检查格式", t['orange']); return

        self.preview_label.setText(f"✅ 解析到 {len(self._parsed)} 个账号：")
        self.preview_label.setStyleSheet(f"font-size:14px;font-weight:600;color:{t['green']};")
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0); w = item.widget()
            if w: w.setParent(None); w.deleteLater()
        for i, acc in enumerate(self._parsed):
            pwd_txt = "••••" if acc.get("password") else "(无密码)"
            plat = f"  ·  {acc['platform']}" if acc.get("platform") else ""
            cost_txt = f"  ·  ¥{acc['monthly_cost']}" if acc.get("monthly_cost") else ""
            row = QLabel(f"  {i+1}.  {acc['name']}  ·  {acc.get('username','')}  ·  {pwd_txt}{plat}{cost_txt}")
            row.setStyleSheet(f"font-size:12px;color:{t['text']};padding:3px 0;"); self.preview_layout.addWidget(row)
        self.preview_layout.addStretch()
        self.preview_area.setVisible(True)
        self.import_btn.setEnabled(True); self.import_btn.setText(f"确认导入 ({len(self._parsed)})")

    def _show_status(self, msg, color):
        t = _current_theme
        self.preview_label.setText(msg); self.preview_label.setStyleSheet(f"font-size:14px;font-weight:600;color:{color};")
        self.preview_area.setVisible(False); self.import_btn.setEnabled(False); self.import_btn.setText("确认导入")

    def _do_import(self):
        if not self._parsed: return
        count = 0
        for acc in self._parsed:
            try: db.create_account(acc, self.key); count += 1
            except: pass
        self._parsed = []
        if count > 0:
            QMessageBox.information(self, "导入成功", f"已成功导入 {count} 个账号到「{self.ws_combo.currentText()}」")
            self.accept()
        else:
            QMessageBox.warning(self, "失败", "导入失败，请检查数据格式")

# ═══════════════════ Data Migration Dialog ═══════════════════

class MigrateDialog(QDialog):
    def __init__(self, parent, key, workspaces):
        super().__init__(parent)
        self.key = key; self.workspaces = workspaces; self.result = None
        t = _current_theme
        self.setWindowTitle("数据迁移"); self.setFixedWidth(500)
        self.setStyleSheet(build_qss(t))
        lay = QVBoxLayout(self); lay.setContentsMargins(32, 24, 32, 24); lay.setSpacing(14)

        tl = QLabel("📦 数据迁移"); tl.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};"); lay.addWidget(tl)
        desc = QLabel("从旧版本导入全部数据（账号、密码、工作空间、密码历史）。\n请在旧版本安装目录中找到 accounts.db 和 .salt 两个文件。")
        desc.setWordWrap(True); desc.setStyleSheet(f"font-size:12px;color:{t['text2']};line-height:1.5;"); lay.addWidget(desc)

        def file_row(label_text, placeholder, browse_filter):
            h = QHBoxLayout(); h.setSpacing(8)
            e = QLineEdit(); e.setPlaceholderText(placeholder); e.setFixedHeight(36)
            b = QPushButton("浏览"); b.setObjectName("ghost"); b.setFixedHeight(36); b.setCursor(Qt.CursorShape.PointingHandCursor)
            def pick():
                p, _ = QFileDialog.getOpenFileName(self, label_text, "", browse_filter)
                if p: e.setText(p)
            b.clicked.connect(pick)
            lbl = QLabel(label_text); lbl.setStyleSheet(f"font-size:12px;color:{t['text2']};font-weight:600;")
            lay.addWidget(lbl); h.addWidget(e, 1); h.addWidget(b); lay.addLayout(h)
            return e

        self.db_edit = file_row("旧版 accounts.db 文件", "选择旧版数据库文件...", "数据库 (*.db);;所有文件 (*)")
        self.salt_edit = file_row("旧版 .salt 密钥文件", "选择旧版 .salt 文件...", "所有文件 (*)")

        lbl_pwd = QLabel("旧版主密码"); lbl_pwd.setStyleSheet(f"font-size:12px;color:{t['text2']};font-weight:600;"); lay.addWidget(lbl_pwd)
        self.pwd_edit = QLineEdit(); self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText("输入旧版本的主密码"); self.pwd_edit.setFixedHeight(36); lay.addWidget(self.pwd_edit)

        ws_row = QHBoxLayout(); ws_row.setSpacing(8)
        lbl_ws = QLabel("导入到工作空间"); lbl_ws.setStyleSheet(f"font-size:12px;color:{t['text2']};font-weight:600;"); lay.addWidget(lbl_ws)
        self.ws_combo = QComboBox(); self.ws_combo.setFixedHeight(36)
        self.ws_combo.addItem("保留原空间分配", "")
        for w in workspaces:
            self.ws_combo.addItem(f"{w['icon']} {w['name']}", w['name'])
        lay.addWidget(self.ws_combo)

        self.skip_cb = QCheckBox("跳过重复账号（名称+用户名+平台相同）")
        self.skip_cb.setChecked(True); self.skip_cb.setStyleSheet(f"color:{t['text']};font-size:13px;"); lay.addWidget(self.skip_cb)

        self.result_label = QLabel(); self.result_label.setWordWrap(True); self.result_label.hide(); lay.addWidget(self.result_label)

        btns = QHBoxLayout(); btns.addStretch()
        cb = QPushButton("取消"); cb.setObjectName("ghost"); cb.clicked.connect(self.reject); btns.addWidget(cb)
        self.do_btn = QPushButton("开始迁移"); self.do_btn.setObjectName("primary"); self.do_btn.clicked.connect(self._do_migrate); btns.addWidget(self.do_btn)
        lay.addLayout(btns)

    def _do_migrate(self):
        db_path = self.db_edit.text().strip()
        salt_path = self.salt_edit.text().strip()
        old_pwd = self.pwd_edit.text()
        t = _current_theme

        if not db_path:
            QMessageBox.warning(self, "提示", "请选择旧版 accounts.db 文件"); return
        if not salt_path:
            QMessageBox.warning(self, "提示", "请选择旧版 .salt 文件"); return
        if not old_pwd:
            QMessageBox.warning(self, "提示", "请输入旧版主密码"); return
        if not os.path.isfile(db_path):
            QMessageBox.warning(self, "提示", "accounts.db 文件不存在"); return
        if not os.path.isfile(salt_path):
            QMessageBox.warning(self, "提示", ".salt 文件不存在"); return

        self.do_btn.setEnabled(False); self.do_btn.setText("迁移中...")
        QApplication.processEvents()

        try:
            r = db.migrate_from_old_db(
                db_path, salt_path, old_pwd, self.key,
                target_workspace=self.ws_combo.currentData() or "",
                skip_duplicates=self.skip_cb.isChecked()
            )
            self.result = r
            lines = [f"✅ 成功导入 {r['migrated']} 个账号"]
            if r['skipped']: lines.append(f"跳过重复 {r['skipped']} 个")
            if r['workspaces']: lines.append(f"新建工作空间 {r['workspaces']} 个")
            if r['password_history']: lines.append(f"密码历史 {r['password_history']} 条")
            if r['errors']: lines.append(f"⚠️ {len(r['errors'])} 个错误")
            self.result_label.setText("\n".join(lines))
            self.result_label.setStyleSheet(f"font-size:13px;color:{t['green']};padding:12px;background:rgba(48,209,88,0.08);border-radius:8px;")
            self.result_label.show()
            self.do_btn.setText("完成"); self.do_btn.setEnabled(True)
            self.do_btn.clicked.disconnect(); self.do_btn.clicked.connect(self.accept)
        except Exception as e:
            self.result_label.setText(f"❌ 迁移失败\n{str(e)}")
            self.result_label.setStyleSheet(f"font-size:13px;color:{t['red']};padding:12px;background:rgba(255,69,58,0.08);border-radius:8px;")
            self.result_label.show()
            self.do_btn.setEnabled(True); self.do_btn.setText("重试")


# ═══════════════════ Navigation ═══════════════════

PERSONAL_NAV = [("仪表盘","dashboard"),("全部账号","all"),("安全检测","security"),("回收站","recycle"),("操作日志","logs")]
MERCHANT_NAV = [("经营概览","dashboard"),("账号库存","all"),("客户管理","customers"),("财务分析","finance"),("安全检测","security"),("回收站","recycle"),("操作日志","logs")]
ALL_PAGES = ["dashboard","all","customers","finance","security","recycle","logs"]

# ═══════════════════ Main Window ═══════════════════

class MainWindow(QMainWindow):
    def __init__(self, key):
        super().__init__()
        self.key=key; self.cur_ws=""; self.workspaces=[]; self.accounts=[]; self.stats={}
        self._rendering=False; self._nav_type=None; self._fcat="全部"; self._sort="name"; self._batch=False; self._bsel=set()
        self._last_clip = ""; self._copy_history = []; self._last_focus_acc = None
        self.setWindowTitle(APP_NAME); self.resize(1200,780); self.setMinimumSize(900,560)
        c = QWidget(); self.setCentralWidget(c)
        ml = QHBoxLayout(c); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)
        self._build_sidebar(ml); self._build_content(ml)
        QShortcut(QKeySequence("Ctrl+K"), self, self._spotlight)
        QShortcut(QKeySequence("Ctrl+N"), self, lambda: self._open_form())
        QShortcut(QKeySequence("Ctrl+D"), self, self._dup_account)
        self._lock_timer = QTimer(self); self._lock_timer.setInterval(AUTO_LOCK_MINUTES*60*1000); self._lock_timer.setSingleShot(True)
        self._lock_timer.timeout.connect(self._auto_lock); self._lock_timer.start(); self.installEventFilter(self)
        self._load_ws(); self._load_data(); self._rebuild_nav(); self._update_status()
        QTimer.singleShot(600, self._check_expiry)

    def _build_sidebar(self, parent):
        t = _current_theme
        self.sidebar = QWidget(); self.sidebar.setObjectName("sidebar"); self.sidebar.setFixedWidth(230)
        sb = QVBoxLayout(self.sidebar); sb.setContentsMargins(16,20,16,12); sb.setSpacing(0)
        logo_row = QHBoxLayout(); logo_row.setSpacing(10)
        self.logo_icon = QLabel("🔑"); self.logo_icon.setFixedSize(36, 36)
        logo_row.addWidget(self.logo_icon)
        logo_col = QVBoxLayout(); logo_col.setSpacing(0)
        self.logo_main = QLabel(APP_NAME_SHORT); self.logo_sub = QLabel("AegisVault")
        logo_col.addWidget(self.logo_main); logo_col.addWidget(self.logo_sub)
        logo_row.addLayout(logo_col); logo_row.addStretch(); sb.addLayout(logo_row)
        sb.addSpacing(16)
        self.ws_btn = QPushButton(); self.ws_btn.setCursor(Qt.CursorShape.PointingHandCursor); self.ws_btn.clicked.connect(self._ws_menu)
        sb.addWidget(self.ws_btn); sb.addSpacing(6)
        wa = QHBoxLayout(); wa.setSpacing(4)
        for txt, handler in [("+ 新建", self._new_ws), ("管理", self._manage_ws)]:
            b = QPushButton(txt); b.setObjectName("ghost"); b.setFixedHeight(28); b.setCursor(Qt.CursorShape.PointingHandCursor); b.clicked.connect(handler); wa.addWidget(b)
        wa.addStretch(); sb.addLayout(wa); sb.addSpacing(14)
        self.sep1 = QFrame(); self.sep1.setFixedHeight(1); sb.addWidget(self.sep1); sb.addSpacing(10)
        self.nav_w = QWidget(); self.nav_l = QVBoxLayout(self.nav_w); self.nav_l.setContentsMargins(0,0,0,0); self.nav_l.setSpacing(2)
        self.nav_g = QButtonGroup(self); self.nav_g.setExclusive(True); sb.addWidget(self.nav_w); sb.addStretch()
        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet(f"background:{t['sb_border']};"); sb.addWidget(sep2); sb.addSpacing(8)
        theme_row = QHBoxLayout(); theme_row.setContentsMargins(0,0,0,0); theme_row.setSpacing(6)
        self.theme_btn = QPushButton("🌙" if not t["is_dark"] else "☀️")
        self.theme_btn.setFixedSize(36, 32); self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("切换主题"); self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setStyleSheet(f"border:1px solid {t['border']};border-radius:10px;background:{t['card']};font-size:14px;padding:0;")
        theme_row.addWidget(self.theme_btn)
        self.ver = QLabel("v3.0"); theme_row.addWidget(self.ver); theme_row.addStretch()
        sb.addLayout(theme_row); sb.addSpacing(4)
        for icon, text, handler in [("📋","最近复制",self._show_copy_history),("📦","数据迁移",self._migrate),("🔐","修改密码",self._change_pwd),("🔒","锁定",self._lock)]:
            b = QPushButton(f"  {icon}  {text}"); b.setObjectName("nav"); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(handler); sb.addWidget(b)
        self._style_sidebar(); parent.addWidget(self.sidebar)

    def _build_content(self, parent):
        content = QWidget(); content.setObjectName("content")
        cl = QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)
        self.topbar = QWidget(); self.topbar.setObjectName("topbar"); self.topbar.setFixedHeight(56)
        tb = QHBoxLayout(self.topbar); tb.setContentsMargins(32,0,32,0); tb.setSpacing(12)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("搜索...  Ctrl+K"); self.search_edit.setMaximumWidth(320); self.search_edit.setFixedHeight(36)
        self.search_edit.textChanged.connect(self._on_search); tb.addWidget(self.search_edit); tb.addStretch()
        for txt, handler in [("导出", self._export), ("导入", self._import)]:
            b = QPushButton(txt); b.setObjectName("ghost"); b.setCursor(Qt.CursorShape.PointingHandCursor); b.clicked.connect(handler); tb.addWidget(b)
        t = _current_theme; a2 = t.get('accent2', t['accent_hover'])
        ai = QPushButton("🤖 AI 助手"); ai.setCursor(Qt.CursorShape.PointingHandCursor)
        ai.setStyleSheet(f"padding:8px 18px;border-radius:12px;background:{t['accent_bg']};color:{t['accent']};border:none;font-weight:600;font-size:12px;")
        ai.clicked.connect(self._open_ai); tb.addWidget(ai)
        bi = QPushButton("📥 批量添加"); bi.setCursor(Qt.CursorShape.PointingHandCursor)
        bi.setStyleSheet(f"padding:8px 18px;border-radius:12px;background:transparent;color:{t['text2']};border:1px solid {t['border']};font-weight:500;font-size:12px;")
        bi.clicked.connect(self._batch_import); tb.addWidget(bi)
        ab = QPushButton("+ 添加"); ab.setObjectName("primary"); ab.setCursor(Qt.CursorShape.PointingHandCursor); ab.clicked.connect(lambda: self._open_form()); tb.addWidget(ab)
        self._style_topbar(); cl.addWidget(self.topbar)
        self.stack = QStackedWidget(); cl.addWidget(self.stack); parent.addWidget(content, 1)
        self.pages = {}
        for name in ALL_PAGES:
            sc = QScrollArea(); sc.setWidgetResizable(True); sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            pw = QWidget(); pl = QVBoxLayout(pw); pl.setContentsMargins(32,24,32,24); pl.setSpacing(20)
            sc.setWidget(pw); self.stack.addWidget(sc); self.pages[name] = pl

    def _style_sidebar(self):
        t = _current_theme; a2 = t.get('accent2', t['accent_hover'])
        self.logo_icon.setStyleSheet(f"font-size:22px;background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {t['accent']},stop:1 {a2});border-radius:10px;color:#fff;")
        self.logo_main.setStyleSheet(f"font-size:18px;font-weight:800;color:{t['text']};")
        self.logo_sub.setStyleSheet(f"font-size:9px;color:{t['muted']};letter-spacing:3px;font-weight:600;")
        self.sep1.setStyleSheet(f"background:{t['sb_border']};")
        self.ver.setStyleSheet(f"font-size:10px;color:{t['muted']};"); self._update_ws_btn()

    def _style_topbar(self):
        t = _current_theme; self.topbar.setStyleSheet(f"QWidget#topbar{{background:{t['topbar']};border-bottom:1px solid {t['sb_border']};}}")

    def _update_ws_btn(self):
        t = _current_theme
        ws = next((w for w in self.workspaces if w["name"] == self.cur_ws), None)
        if not ws: self.ws_btn.setText("选择空间"); return
        wt = "个人" if ws.get("ws_type","personal") == "personal" else "经营"
        cnt = len(self.accounts) if hasattr(self, 'accounts') else 0
        self.ws_btn.setText(f"  {ws.get('icon','📁')}  {ws['name']}\n  {wt} · {cnt}个账号")
        self.ws_btn.setStyleSheet(f"QPushButton{{background:{t['card']};border:1px solid {t['border']};border-radius:8px;padding:10px 14px;color:{t['text']};font-size:13px;font-weight:600;text-align:left;}}QPushButton:hover{{background:{t['card_hover']};}}")

    def _ws_menu(self):
        m = QMenu(self)
        for w in self.workspaces:
            tp = "个人" if w.get("ws_type","personal") == "personal" else "经营"
            act = m.addAction(f"{w['icon']} {w['name']}  ({tp})")
            act.setCheckable(True); act.setChecked(w["name"] == self.cur_ws)
            act.triggered.connect(lambda _, n=w["name"]: self._switch_ws(n))
        m.addSeparator(); m.addAction("新建空间", self._new_ws); m.addAction("管理空间", self._manage_ws)
        m.exec(self.ws_btn.mapToGlobal(self.ws_btn.rect().bottomLeft()))

    def _switch_ws(self, name):
        if name != self.cur_ws:
            ot = self._ws_type(); self.cur_ws = name; self._load_data()
            if ot != self._ws_type(): self._rebuild_nav()
            else: self._style_sidebar(); self._refresh()

    def _load_ws(self):
        self.workspaces = db.list_workspaces()
        if not self.cur_ws and self.workspaces: self.cur_ws = self.workspaces[0]["name"]
        self._update_ws_btn()

    def _rebuild_nav(self):
        for b in list(self.nav_g.buttons()): self.nav_g.removeButton(b); b.setParent(None); b.deleteLater()
        while self.nav_l.count():
            item = self.nav_l.takeAt(0); w = item.widget()
            if w: w.setParent(None); w.deleteLater()
        nav = MERCHANT_NAV if self._ws_type() == "merchant" else PERSONAL_NAV
        cp = ALL_PAGES[self.stack.currentIndex()] if self.stack.currentIndex() < len(ALL_PAGES) else None
        vp = [p for _, p in nav]; target = cp if cp in vp else "dashboard"
        cnt_map = {}
        if hasattr(self, 'accounts'):
            cnt_map["all"] = len(self.accounts)
            for a in self.accounts: cnt_map[a["category"]] = cnt_map.get(a["category"], 0) + 1
            cnt_map["recycle"] = self.stats.get("recycle_count", 0)
        for text, page in nav:
            cnt = cnt_map.get(page, cnt_map.get("all", 0) if page == "all" else 0)
            icon = NAV_ICONS.get(page, "")
            label = f"  {icon}  {text}  ({cnt})" if page in ("all","recycle") and cnt else f"  {icon}  {text}"
            btn = QPushButton(label); btn.setObjectName("nav"); btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.setProperty("page", page)
            btn.clicked.connect(lambda _, p=page: self._go(p))
            self.nav_g.addButton(btn); self.nav_l.addWidget(btn)
            if page == target: btn.setChecked(True)
        self._style_sidebar(); self._go(target)

    def _ws_type(self):
        for w in self.workspaces:
            if w["name"] == self.cur_ws: return w.get("ws_type","personal")
        return "personal"

    def _load_data(self):
        self.accounts = db.list_accounts(self.key, self.cur_ws); self.stats = db.get_stats(self.key, self.cur_ws); self._update_status()

    def _go(self, page):
        if page in ALL_PAGES: self.stack.setCurrentIndex(ALL_PAGES.index(page))
        for b in self.nav_g.buttons(): b.setChecked(b.property("page") == page)
        self._refresh(page)

    def _refresh(self, page=None):
        if self._rendering: return
        self._rendering = True
        try:
            if page is None: page = ALL_PAGES[self.stack.currentIndex()] if self.stack.currentIndex() < len(ALL_PAGES) else "dashboard"
            r = {"dashboard":self._pg_dash,"all":self._pg_accs,"customers":self._pg_cust,"finance":self._pg_fin,"security":self._pg_sec,"recycle":self._pg_rec,"logs":self._pg_log}
            if page in r: r[page]()
        finally: self._rendering = False

    def _clr(self, layout):
        while layout.count():
            item = layout.takeAt(0); w = item.widget()
            if w: w.setParent(None); w.deleteLater()
            sub = item.layout()
            if sub: self._clr(sub)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress, QEvent.Type.Wheel): self._lock_timer.start()
        return super().eventFilter(obj, event)

    def _auto_lock(self): QMessageBox.information(self, APP_NAME_SHORT, f"超过{AUTO_LOCK_MINUTES}分钟无操作"); self._lock()
    def _update_status(self):
        wt = "个人" if self._ws_type() == "personal" else "经营"
        self.statusBar().showMessage(f"  {APP_NAME}  |  {wt} {self.cur_ws}  |  {len(self.accounts)} 个账号  |  自动锁定 {AUTO_LOCK_MINUTES}分钟")

    def showEvent(self, e):
        super().showEvent(e); self._apply_titlebar()
    def _apply_titlebar(self):
        t = _current_theme; set_titlebar_color(int(self.winId()), "#0E0E16" if t["is_dark"] else "#F8F8FE", t["is_dark"])

    # ─── Dashboard ───
    def _pg_dash(self):
        lay = self.pages["dashboard"]; self._clr(lay); t = _current_theme; s = self.stats; wt = self._ws_type()
        hour = datetime.now().hour
        greeting = "夜深了" if hour < 6 else "早上好" if hour < 12 else "下午好" if hour < 18 else "晚上好"
        total = s.get("total", 0)
        a2 = t.get('accent2', t['accent_hover'])
        gt = QLabel(f"{greeting} 👋"); gt.setStyleSheet(f"font-size:26px;font-weight:800;color:{t['text']};"); lay.addWidget(gt)
        ws_desc = "经营空间" if wt == "merchant" else "个人空间"
        sl = QLabel(f"{self.cur_ws} · {ws_desc} · {total} 个账号"); sl.setStyleSheet(f"font-size:13px;color:{t['muted']};"); lay.addWidget(sl)
        deco = QFrame(); deco.setFixedHeight(3)
        deco.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {t['accent']},stop:0.5 {a2},stop:1 transparent);border:none;border-radius:1px;")
        lay.addWidget(deco)

        grid = QHBoxLayout(); grid.setSpacing(10)
        cost = s.get("total_monthly_cost", 0)
        total_invested = round(sum((a.get("monthly_cost",0) or 0) for a in self.accounts) * 12, 2)
        if wt == "merchant":
            inv = len([a for a in self.accounts if a.get("account_status")=="inventory"])
            rnt = len([a for a in self.accounts if a.get("account_status")=="rented"])
            sld = len([a for a in self.accounts if a.get("account_status")=="sold"])
            for l, v, c in [("总账号",total,t['accent']),("库存",inv,t['text2']),("出租中",rnt,t['accent']),("已售出",sld,t['green']),("月收入",f"¥{cost}",t['orange'])]:
                grid.addWidget(StatCard(l, v, c))
        else:
            for l, v, c in [("总账号",total,t['accent']),("正常",s.get("active",0),t['green']),("即将到期",s.get("expiring_soon",0),t['orange']),("已过期",s.get("expired",0),t['red']),("月支出",f"¥{cost}","#5E5CE6"),("年投入",f"¥{total_invested}","#BF5AF2")]:
                grid.addWidget(StatCard(l, v, c))
        lay.addLayout(grid)

        cols = QHBoxLayout(); cols.setSpacing(20); left = QVBoxLayout(); left.setSpacing(12); right = QVBoxLayout(); right.setSpacing(12)

        cat_counts = {}
        for a in self.accounts: cat_counts[a["category"]] = cat_counts.get(a["category"], 0) + 1
        if cat_counts:
            cc = Card(); cl = QVBoxLayout(cc); cl.setContentsMargins(20,16,20,16); cl.setSpacing(8)
            cl.addWidget(self._htitle("分类分布"))
            for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
                cr = QHBoxLayout(); cr.setSpacing(8)
                color = CAT_COLORS.get(cat, "#98989D"); pct = cnt/total*100 if total > 0 else 0
                cn = QLabel(cat); cn.setStyleSheet(f"font-size:14px;color:{t['text']};min-width:50px;"); cr.addWidget(cn)
                bg = QFrame(); bg.setFixedHeight(8); bg.setMinimumWidth(60); bg.setStyleSheet(f"background:{t['input_bg']};border-radius:4px;border:none;")
                fill = QFrame(bg); fill.setGeometry(0,0,max(4,int(pct/100*80)),8); fill.setStyleSheet(f"background:{color};border-radius:4px;border:none;")
                cr.addWidget(bg, 1)
                pv = QLabel(f"{cnt}"); pv.setStyleSheet(f"font-size:14px;font-weight:600;color:{t['text2']};min-width:24px;"); pv.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter); cr.addWidget(pv)
                cl.addLayout(cr)
            left.addWidget(cc)

        try:
            sec = db.security_analysis(self.key, self.cur_ws); avg = sec["summary"]["avg_health"]; sm = sec["summary"]
            sc = t['green'] if avg >= 80 else t['orange'] if avg >= 50 else t['red']
            scard = Card(); scl = QVBoxLayout(scard); scl.setContentsMargins(20,16,20,16); scl.setSpacing(8)
            scl.addWidget(self._htitle("安全评分"))
            sr = QHBoxLayout(); sr.setSpacing(12)
            sv = QLabel(str(avg)); sv.setStyleSheet(f"font-size:34px;font-weight:800;color:{sc};letter-spacing:-1px;"); sr.addWidget(sv)
            ri = QVBoxLayout(); ri.setSpacing(4)
            bar = QFrame(); bar.setFixedHeight(8); bar.setStyleSheet(f"background:{t['input_bg']};border-radius:4px;border:none;"); bar.setMinimumWidth(120)
            bf = QFrame(bar); bf.setGeometry(0,0,int(avg/100*120),8); bf.setStyleSheet(f"background:{sc};border-radius:4px;border:none;"); ri.addWidget(bar)
            info = QHBoxLayout()
            for v, l in [(sm["weak"],"弱密码"),(sm["duplicate"],"重复"),(sm["empty"],"空密码")]:
                il = QLabel(f"{l} {v}"); il.setStyleSheet(f"font-size:12px;color:{t['red'] if v > 0 else t['muted']};font-weight:{'600' if v > 0 else '400'};"); info.addWidget(il)
            info.addStretch(); ri.addLayout(info); sr.addLayout(ri, 1); scl.addLayout(sr)
            left.addWidget(scard)
        except: pass
        left.addStretch(); cols.addLayout(left, 1)

        starred = [a for a in self.accounts if a.get("starred")]
        if starred:
            sc = Card(); scl = QVBoxLayout(sc); scl.setContentsMargins(20,16,20,16); scl.setSpacing(8)
            scl.addWidget(self._htitle(f"星标 ({len(starred)})"))
            for a in starred[:5]:
                sr = QHBoxLayout(); sr.setSpacing(8)
                sn = QLabel(a["name"]); sn.setStyleSheet(f"font-size:14px;font-weight:600;color:{t['text']};"); sr.addWidget(sn)
                sp = QLabel(a.get("platform","") or a["category"]); sp.setStyleSheet(f"font-size:12px;color:{t['muted']};"); sr.addWidget(sp)
                sr.addStretch()
                cp = QPushButton("复制"); cp.setObjectName("ghost"); cp.setFixedHeight(24); cp.setCursor(Qt.CursorShape.PointingHandCursor)
                cp.clicked.connect(lambda _, acc=a: self._copy(acc.get("password",""))); sr.addWidget(cp)
                scl.addLayout(sr)
            right.addWidget(sc)

        exp = [a for a in self.accounts if a.get("days_left") is not None and a["days_left"] <= 30]
        exp.sort(key=lambda a: a.get("days_left", 999))
        if exp:
            ec = Card(); ecl = QVBoxLayout(ec); ecl.setContentsMargins(20,16,20,16); ecl.setSpacing(8)
            ecl.addWidget(self._htitle(f"到期预警 ({len(exp)})"))
            for a in exp[:5]:
                dl = a["days_left"]; clr = t["red"] if dl < 0 else t["orange"] if dl <= 7 else t["green"]
                txt = f"过期{abs(dl)}天" if dl < 0 else "今天到期" if dl == 0 else f"{dl}天后"
                er = QHBoxLayout(); er.setSpacing(8)
                en = QLabel(a["name"]); en.setStyleSheet(f"font-size:14px;font-weight:500;color:{t['text']};"); er.addWidget(en)
                er.addStretch()
                ed = QLabel(txt); ed.setStyleSheet(f"font-size:12px;font-weight:600;color:{clr};background:{_rgba(clr,0.1)};padding:2px 8px;border-radius:4px;"); er.addWidget(ed)
                ecl.addLayout(er)
            right.addWidget(ec)

        stale = []
        for a in self.accounts:
            upd = a.get("updated_at") or a.get("created_at") or ""
            if upd:
                try:
                    days = (datetime.now() - datetime.strptime(upd[:10], "%Y-%m-%d")).days
                    if days >= 90: stale.append((a, days))
                except: pass
        if stale:
            stale.sort(key=lambda x: -x[1])
            rc = Card(); rcl = QVBoxLayout(rc); rcl.setContentsMargins(20,16,20,16); rcl.setSpacing(6)
            rcl.addWidget(self._htitle(f"密码轮换 ({len(stale)})"))
            for a, days in stale[:4]:
                rr = QHBoxLayout()
                rn = QLabel(a["name"]); rn.setStyleSheet(f"font-size:14px;color:{t['text']};"); rr.addWidget(rn); rr.addStretch()
                clr = t["red"] if days >= 180 else t["orange"]
                rd = QLabel(f"{days}天未改"); rd.setStyleSheet(f"font-size:12px;font-weight:600;color:{clr};background:{_rgba(clr,0.1)};padding:2px 8px;border-radius:4px;"); rr.addWidget(rd)
                rcl.addLayout(rr)
            right.addWidget(rc)

        try:
            logs = db.get_logs(4)
            if logs:
                lc = Card(); lcl = QVBoxLayout(lc); lcl.setContentsMargins(20,16,20,16); lcl.setSpacing(6)
                lcl.addWidget(self._htitle("最近操作"))
                for l in logs:
                    lr = QHBoxLayout()
                    la = QLabel(l["action"]); la.setStyleSheet(f"font-size:12px;font-weight:600;color:{t['accent']};min-width:50px;"); lr.addWidget(la)
                    ld = QLabel(l.get("detail","")); ld.setStyleSheet(f"font-size:12px;color:{t['text2']};"); lr.addWidget(ld, 1)
                    lt = QLabel(l["ts"][-8:]); lt.setStyleSheet(f"font-size:12px;color:{t['muted']};"); lr.addWidget(lt)
                    lcl.addLayout(lr)
                right.addWidget(lc)
        except: pass
        right.addStretch(); cols.addLayout(right, 1); lay.addLayout(cols); lay.addStretch()

    def _htitle(self, text):
        t = _current_theme; l = QLabel(text); l.setStyleSheet(f"font-size:15px;font-weight:700;color:{t['text']};"); return l

    # ─── Accounts ───
    def _pg_accs(self):
        lay = self.pages["all"]; self._clr(lay); t = _current_theme; wt = self._ws_type()
        lay.addWidget(self._htitle("账号库存" if wt == "merchant" else "全部账号"))
        fr = QHBoxLayout(); fr.setSpacing(8)
        cats = ["全部"] + sorted(set(a["category"] for a in self.accounts))
        for cat in cats:
            ch = QPushButton(cat); ch.setCheckable(True); ch.setChecked(cat == self._fcat); ch.setCursor(Qt.CursorShape.PointingHandCursor)
            ch.setStyleSheet(f"font-size:12px;padding:4px 12px;border-radius:8px;background:{t['accent'] if cat==self._fcat else t['input_bg']};color:{'#fff' if cat==self._fcat else t['text2']};border:none;font-weight:{'600' if cat==self._fcat else '400'};")
            ch.clicked.connect(lambda _, c=cat: (setattr(self, '_fcat', c), self._pg_accs())); fr.addWidget(ch)
        fr.addStretch()
        sl = QLabel("排序"); sl.setStyleSheet(f"font-size:12px;color:{t['muted']};"); fr.addWidget(sl)
        sc = QComboBox(); sc.setFixedWidth(100)
        for l, v in [("名称","name"),("最新","date"),("成本","cost"),("到期","expire")]: sc.addItem(l, v)
        idx = sc.findData(self._sort)
        if idx >= 0: sc.setCurrentIndex(idx)
        sc.activated.connect(lambda i: (setattr(self, '_sort', sc.itemData(i)), self._pg_accs())); fr.addWidget(sc)
        bb = QPushButton("取消" if self._batch else "批量"); bb.setCursor(Qt.CursorShape.PointingHandCursor)
        bb.setStyleSheet(f"font-size:12px;padding:4px 12px;border-radius:8px;background:{_rgba(t['red'],0.1) if self._batch else t['input_bg']};color:{t['red'] if self._batch else t['text2']};border:none;")
        bb.clicked.connect(lambda: (setattr(self, '_batch', not self._batch), self._bsel.clear() if not self._batch else None, self._pg_accs())); fr.addWidget(bb)
        lay.addLayout(fr)
        if self._batch and self._bsel:
            br = QHBoxLayout(); br.addWidget(QLabel(f"已选 {len(self._bsel)} 项"))
            db_ = QPushButton(f"批量删除"); db_.setObjectName("danger"); db_.clicked.connect(self._batch_del); br.addWidget(db_); br.addStretch(); lay.addLayout(br)
        filtered = self.accounts; q = self.search_edit.text().lower()
        if q: filtered = [a for a in filtered if q in a["name"].lower() or q in a["platform"].lower() or q in a["username"].lower() or q in a.get("customer_name","").lower()]
        if self._fcat != "全部": filtered = [a for a in filtered if a["category"] == self._fcat]
        if self._sort == "name": filtered.sort(key=lambda a: a["name"].lower())
        elif self._sort == "date": filtered.sort(key=lambda a: a.get("created_at",""), reverse=True)
        elif self._sort == "cost": filtered.sort(key=lambda a: a.get("monthly_cost",0) or 0, reverse=True)
        elif self._sort == "expire": filtered.sort(key=lambda a: a.get("days_left",9999) if a.get("days_left") is not None else 9999)
        cl = QLabel(f"{len(filtered)} 个账号"); cl.setStyleSheet(f"font-size:12px;color:{t['muted']};"); lay.addWidget(cl)
        if not filtered: self._empty(lay, "暂无账号", "点击添加开始管理"); lay.addStretch(); return
        if not hasattr(self, '_collapsed_cats'): self._collapsed_cats = set()
        groups = {}
        for a in filtered:
            cat = a["category"] or "其他"
            if cat not in groups: groups[cat] = []
            groups[cat].append(a)
        for cat in sorted(groups.keys()):
            accs = groups[cat]; cc = CAT_COLORS.get(cat, "#98989D"); collapsed = cat in self._collapsed_cats
            arrow = '▶' if collapsed else '▼'
            hdr = QPushButton(f"  {arrow}  ●  {cat}  ({len(accs)})"); hdr.setCursor(Qt.CursorShape.PointingHandCursor)
            hdr.setStyleSheet(f"text-align:left;font-size:13px;font-weight:600;color:{cc};background:transparent;border:none;padding:10px 6px;")
            container = QWidget()
            container_lay = QVBoxLayout(container); container_lay.setContentsMargins(0,0,0,0); container_lay.setSpacing(8)
            container.setVisible(not collapsed)
            hdr.clicked.connect(lambda _, c=cat, w=container, b=hdr: self._toggle_group(c, w, b))
            lay.addWidget(hdr)
            for a in accs:
                if self._batch:
                    rw = QWidget(); rl = QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0); rl.setSpacing(8)
                    cb = QCheckBox(); cb.setChecked(a["id"] in self._bsel)
                    cb.stateChanged.connect(lambda s, aid=a["id"]: self._bsel.add(aid) if s else self._bsel.discard(aid)); rl.addWidget(cb)
                    card = AccountCard(a, wt); card.edit_clicked.connect(lambda aid: self._open_form(aid)); card.delete_clicked.connect(self._del_acc)
                    card.star_clicked.connect(self._toggle_star); card.copy_clicked.connect(self._copy); card.focused.connect(self._on_card_focus); rl.addWidget(card, 1); container_lay.addWidget(rw)
                else:
                    card = AccountCard(a, wt); card.edit_clicked.connect(lambda aid: self._open_form(aid)); card.delete_clicked.connect(self._del_acc)
                    card.star_clicked.connect(self._toggle_star); card.copy_clicked.connect(self._copy); card.focused.connect(self._on_card_focus); container_lay.addWidget(card)
            lay.addWidget(container)
        lay.addStretch()

    def _toggle_group(self, cat, container, btn):
        if cat in self._collapsed_cats: self._collapsed_cats.discard(cat); container.setVisible(True); btn.setText(btn.text().replace("▶","▼"))
        else: self._collapsed_cats.add(cat); container.setVisible(False); btn.setText(btn.text().replace("▼","▶"))

    def _batch_del(self):
        if not self._bsel: return
        if QMessageBox.question(self, "批量删除", f"删除 {len(self._bsel)} 个账号？") == QMessageBox.StandardButton.Yes:
            for aid in self._bsel: db.soft_delete(aid)
            self._bsel.clear(); self._batch = False; self._load_data(); self._refresh()

    # ─── Customers ───
    def _pg_cust(self):
        lay = self.pages["customers"]; self._clr(lay); t = _current_theme
        lay.addWidget(self._htitle("客户管理"))
        customers = {}
        for a in self.accounts:
            cn = (a.get("customer_name") or "").strip() or "未分配"
            if cn not in customers: customers[cn] = {"name":cn,"contact":"","accounts":[],"revenue":0,"cost":0}
            customers[cn]["accounts"].append(a); customers[cn]["revenue"] += (a.get("sell_price") or 0); customers[cn]["cost"] += (a.get("monthly_cost") or 0)
            if not customers[cn]["contact"] and a.get("customer_contact"): customers[cn]["contact"] = a["customer_contact"]
        real = {k:v for k,v in customers.items() if k != "未分配"}
        grid = QHBoxLayout(); grid.setSpacing(12)
        tr = sum(c["revenue"] for c in real.values()); tc = sum(c["cost"] for c in real.values()); profit = tr - tc
        for l, v, c in [("客户",len(real),"#5E5CE6"),("月收入",f"¥{tr}",t['green']),("月利润",f"¥{profit}",t['accent']),("账号",len(self.accounts),t['orange'])]:
            grid.addWidget(StatCard(l, v, c))
        lay.addLayout(grid)
        for cn, data in sorted(customers.items(), key=lambda x: (-x[1]["revenue"], x[0])):
            cc = Card(); cl = QVBoxLayout(cc); cl.setContentsMargins(20,14,20,14); cl.setSpacing(6)
            top = QHBoxLayout()
            nl = QLabel(data['name']); nl.setStyleSheet(f"font-size:16px;font-weight:600;color:{t['text']};"); top.addWidget(nl); top.addStretch()
            cnt = QLabel(f"{len(data['accounts'])} 个账号"); cnt.setStyleSheet(f"font-size:12px;color:{t['muted']};background:{t['input_bg']};padding:2px 8px;border-radius:4px;"); top.addWidget(cnt)
            if data["revenue"] > 0:
                rv = QLabel(f"¥{data['revenue']}/月"); rv.setStyleSheet(f"font-size:14px;font-weight:600;color:{t['green']};"); top.addWidget(rv)
            cl.addLayout(top)
            if data["contact"]:
                ct = QLabel(data['contact']); ct.setStyleSheet(f"font-size:12px;color:{t['text2']};"); cl.addWidget(ct)
            names = ", ".join(a["name"] for a in data["accounts"][:6])
            if len(data["accounts"]) > 6: names += f" ...共{len(data['accounts'])}个"
            al = QLabel(names); al.setStyleSheet(f"font-size:12px;color:{t['muted']};"); al.setWordWrap(True); cl.addWidget(al)
            lay.addWidget(cc)
        if not real: self._empty(lay, "暂无客户", "在账号中填写客户信息即可归类")
        lay.addStretch()

    # ─── Security ───
    def _pg_sec(self):
        lay = self.pages["security"]; self._clr(lay); t = _current_theme
        lay.addWidget(self._htitle("安全检测"))
        try:
            data = db.security_analysis(self.key, self.cur_ws); s = data["summary"]
            grid = QHBoxLayout(); grid.setSpacing(12)
            for l, v, c in [("健康",f"{s['avg_health']}",t['green']),("弱密码",s["weak"],t['red']),("重复",s["duplicate"],t['orange']),("空密码",s["empty"],"#5E5CE6")]:
                grid.addWidget(StatCard(l, v, c))
            lay.addLayout(grid)
            for a in data["accounts"]:
                hc = t['green'] if a["health"] >= 80 else t['orange'] if a["health"] >= 50 else t['red']
                issues = [x for x in [("弱密码" if a["weak"] else ""),("重复" if a["duplicate"] else ""),("空密码" if a["empty"] else "")] if x]
                cc = Card(); cl = QHBoxLayout(cc); cl.setContentsMargins(20,12,20,12); cl.setSpacing(12)
                cl.addWidget(QLabel(a["name"])); cl.addWidget(QLabel(a.get("platform",""))); cl.addStretch()
                il = QLabel(" · ".join(issues) if issues else "安全"); il.setStyleSheet(f"font-size:12px;color:{t['red'] if issues else t['green']};font-weight:500;"); cl.addWidget(il)
                sc = QLabel(str(a["health"])); sc.setStyleSheet(f"color:{hc};font-weight:700;font-size:16px;min-width:30px;"); sc.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter); cl.addWidget(sc)
                lay.addWidget(cc)
        except Exception as e: lay.addWidget(QLabel(f"错误: {e}"))
        lay.addStretch()

    # ─── Finance ───
    def _pg_fin(self):
        lay = self.pages["finance"]; self._clr(lay); t = _current_theme
        lay.addWidget(self._htitle("财务分析"))
        try:
            d = db.finance_analysis(self.key, self.cur_ws)
            grid = QHBoxLayout(); grid.setSpacing(12)
            for l, v, c in [("月成本",f"¥{d['monthly_cost']}",t['red']),("月收入",f"¥{d['monthly_sell']}",t['green']),("月利润",f"¥{d['monthly_profit']}",t['accent']),("利润率",f"{d['profit_rate']}%","#5E5CE6"),("年成本",f"¥{d['yearly_cost']}",t['orange'])]:
                grid.addWidget(StatCard(l, v, c))
            lay.addLayout(grid)
            if d["category_costs"]:
                lay.addWidget(self._htitle("分类明细"))
                for cat, cost in sorted(d["category_costs"].items(), key=lambda x: -x[1]):
                    cc = Card(); cl = QHBoxLayout(cc); cl.setContentsMargins(20,12,20,12)
                    color = CAT_COLORS.get(cat, "#98989D"); dot = QLabel("●"); dot.setStyleSheet(f"color:{color};font-size:10px;"); dot.setFixedWidth(14); cl.addWidget(dot)
                    cl.addWidget(QLabel(cat)); cl.addStretch(); cl.addWidget(QLabel(f"¥{cost}/月")); lay.addWidget(cc)
        except Exception as e: lay.addWidget(QLabel(f"错误: {e}"))
        lay.addStretch()

    # ─── Recycle ───
    def _pg_rec(self):
        lay = self.pages["recycle"]; self._clr(lay); t = _current_theme
        lay.addWidget(self._htitle("回收站"))
        items = db.list_recycle(self.key)
        if items:
            eb = QPushButton("清空回收站"); eb.setObjectName("danger"); eb.clicked.connect(self._empty_rec); lay.addWidget(eb)
        for a in items:
            cc = Card(); cl = QHBoxLayout(cc); cl.setContentsMargins(20,12,20,12); cl.setSpacing(12)
            cl.addWidget(QLabel(a["name"])); cl.addWidget(QLabel(a.get("category",""))); cl.addStretch()
            rb = QPushButton("恢复"); rb.setObjectName("ghost"); rb.clicked.connect(lambda _, aid=a["id"]: self._restore(aid)); cl.addWidget(rb)
            db_ = QPushButton("彻底删除"); db_.setObjectName("danger"); db_.clicked.connect(lambda _, aid=a["id"]: self._perm_del(aid)); cl.addWidget(db_)
            lay.addWidget(cc)
        if not items: self._empty(lay, "回收站为空", "")
        lay.addStretch()

    # ─── Logs ───
    def _pg_log(self):
        lay = self.pages["logs"]; self._clr(lay); t = _current_theme
        lay.addWidget(self._htitle("操作日志"))
        logs = db.get_logs(50)
        for l in logs:
            cc = Card(); cl = QHBoxLayout(cc); cl.setContentsMargins(16,10,16,10); cl.setSpacing(12)
            tl = QLabel(l["ts"]); tl.setStyleSheet(f"font-size:12px;color:{t['muted']};min-width:130px;font-family:'Cascadia Code','Consolas',monospace;"); cl.addWidget(tl)
            al = QLabel(l["action"]); al.setStyleSheet(f"font-size:12px;font-weight:600;color:{t['accent']};"); al.setFixedWidth(80); cl.addWidget(al)
            dl = QLabel(l.get("detail","")); dl.setStyleSheet(f"font-size:14px;color:{t['text2']};"); cl.addWidget(dl, 1)
            lay.addWidget(cc)
        if not logs: self._empty(lay, "暂无日志", "")
        lay.addStretch()

    def _empty(self, lay, msg, sub):
        t = _current_theme
        w = QWidget(); el = QVBoxLayout(w); el.setAlignment(Qt.AlignmentFlag.AlignCenter); el.setSpacing(8)
        ml = QLabel(msg); ml.setAlignment(Qt.AlignmentFlag.AlignCenter); ml.setStyleSheet(f"font-size:16px;color:{t['text2']};font-weight:600;"); el.addWidget(ml)
        if sub:
            sl = QLabel(sub); sl.setAlignment(Qt.AlignmentFlag.AlignCenter); sl.setStyleSheet(f"font-size:14px;color:{t['muted']};"); el.addWidget(sl)
        w.setMinimumHeight(200); lay.addWidget(w)

    # ─── Actions ───
    def _batch_import(self):
        dlg = BatchImportDialog(self, self.key, self.workspaces, self.cur_ws, self._ws_type())
        if dlg.exec() == QDialog.DialogCode.Accepted: self._load_data(); self._refresh()
    def _open_ai(self):
        dlg = AIAssistantDialog(self, self.key, self.accounts, self.cur_ws, self._ws_type())
        dlg.import_ready.connect(lambda _: (self._load_data(), self._refresh())); dlg.exec(); self._load_data(); self._refresh()
    def _spotlight(self):
        dlg = SpotlightDialog(self, self.key); dlg.account_selected.connect(self._spot_jump)
        center = self.geometry().center(); dlg.move(center.x()-260, center.y()-250); dlg.exec()
    def _spot_jump(self, ws, aid):
        if ws != self.cur_ws:
            ot = self._ws_type(); self.cur_ws = ws; self._load_ws(); self._load_data()
            if self._ws_type() != ot: self._rebuild_nav()
        self._go("all"); self._open_form(aid)
    def _open_form(self, aid=None):
        acc = next((a for a in self.accounts if a["id"] == aid), None) if aid else None
        dlg = AccountDialog(self, self.key, self.workspaces, self.cur_ws, self._ws_type(), acc)
        if dlg.exec() == QDialog.DialogCode.Accepted: self._load_data(); self._refresh()
    def _del_acc(self, aid):
        acc = next((a for a in self.accounts if a["id"] == aid), None)
        if QMessageBox.question(self,"删除",f"删除「{acc['name'] if acc else aid}」？\n可在回收站恢复",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            db.soft_delete(aid); self._load_data(); self._refresh()
    def _on_card_focus(self, aid): self._last_focus_acc = aid
    def _toggle_star(self, aid): db.toggle_star(aid); self._load_data(); self._refresh()
    def _copy(self, text):
        QApplication.clipboard().setText(text); self._last_clip = text
        if text not in self._copy_history: self._copy_history.insert(0, text)
        if len(self._copy_history) > 5: self._copy_history = self._copy_history[:5]
        self.statusBar().showMessage("已复制 (30秒后自动清除)", 3000)
        QTimer.singleShot(30000, lambda: self._clear_clip(text))
    def _clear_clip(self, expected):
        cb = QApplication.clipboard()
        if cb.text() == expected: cb.clear(); self.statusBar().showMessage("剪贴板已清除", 2000)
    def _check_expiry(self):
        urgent = [a for a in self.accounts if a.get("days_left") is not None and a["days_left"] <= 7]
        if not urgent: return
        urgent.sort(key=lambda a: a.get("days_left", 999))
        t = _current_theme; dlg = QDialog(self); dlg.setWindowTitle("到期提醒"); dlg.setMinimumWidth(440)
        dlg.setStyleSheet(build_qss(t)); lay = QVBoxLayout(dlg); lay.setContentsMargins(32,20,32,20); lay.setSpacing(12)
        tl = QLabel(f"⚠ 有 {len(urgent)} 个账号即将到期或已过期"); tl.setStyleSheet(f"font-size:18px;font-weight:700;color:{t['text']};"); lay.addWidget(tl)
        for a in urgent[:10]:
            dl = a["days_left"]; clr = t["red"] if dl < 0 else t["orange"] if dl <= 3 else t["text2"]
            txt = f"过期{abs(dl)}天" if dl < 0 else "今天到期" if dl == 0 else f"{dl}天后到期"
            row = QHBoxLayout()
            nm = QLabel(a["name"]); nm.setStyleSheet(f"font-size:14px;font-weight:600;color:{t['text']};"); row.addWidget(nm)
            pl = QLabel(a.get("platform","") or a["category"]); pl.setStyleSheet(f"font-size:12px;color:{t['muted']};"); row.addWidget(pl)
            row.addStretch()
            dl_lbl = QLabel(txt); dl_lbl.setStyleSheet(f"font-size:12px;font-weight:600;color:{clr};background:{_rgba(clr,0.1)};padding:2px 10px;border-radius:4px;"); row.addWidget(dl_lbl)
            lay.addLayout(row)
        if len(urgent) > 10: lay.addWidget(QLabel(f"...还有 {len(urgent)-10} 个"))
        cb = QPushButton("知道了"); cb.setObjectName("primary"); cb.clicked.connect(dlg.accept); lay.addWidget(cb)
        dlg.exec()
    def _dup_account(self):
        if not self._last_focus_acc: self.statusBar().showMessage("请先点击一个账号卡片", 2000); return
        src = next((a for a in self.accounts if a["id"] == self._last_focus_acc), None)
        if not src: return
        dup = {k: v for k, v in src.items() if k not in ("id", "created_at", "updated_at", "days_left")}
        dup["name"] = f"{src['name']} (副本)"
        dlg = AccountDialog(self, self.key, self.workspaces, self.cur_ws, self._ws_type(), None)
        dlg.cat_combo.setCurrentText(dup.get("category","AI对话")); dlg.name_edit.setText(dup["name"])
        dlg.plat_edit.setText(dup.get("platform","")); dlg.user_edit.setText(dup.get("username",""))
        dlg.pwd_edit.setText(dup.get("password","")); dlg.key_edit.setText(dup.get("api_key",""))
        dlg.url_edit.setText(dup.get("url","")); dlg.cost_edit.setValue(dup.get("monthly_cost",0) or 0)
        dlg.notes_edit.setPlainText(dup.get("notes",""))
        tags = dup.get("tags",[])
        if isinstance(tags, list): dlg.tags_edit.setText(", ".join(tags))
        if dlg.exec() == QDialog.DialogCode.Accepted: self._load_data(); self._refresh()
    def _show_copy_history(self):
        if not self._copy_history: self.statusBar().showMessage("暂无复制记录", 2000); return
        m = QMenu(self)
        for i, txt in enumerate(self._copy_history):
            display = txt[:40] + "..." if len(txt) > 40 else txt
            display = display.replace("\n", " ")
            m.addAction(f"{i+1}. {display}", lambda _, t=txt: self._copy(t))
        m.exec(QCursor.pos())
    def _on_search(self):
        p = ALL_PAGES[self.stack.currentIndex()] if self.stack.currentIndex() < len(ALL_PAGES) else "all"
        if p == "all": self._pg_accs()
    def _new_ws(self):
        dlg = WorkspaceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.result_data
            try: db.create_workspace(d["name"],d["icon"],d["ws_type"]); self.cur_ws = d["name"]; self._load_ws(); self._load_data(); self._rebuild_nav()
            except Exception as e: QMessageBox.warning(self,"错误",str(e))
    def _manage_ws(self):
        t = _current_theme; dlg = QDialog(self); dlg.setWindowTitle("管理空间"); dlg.setMinimumWidth(440)
        dlg.setStyleSheet(build_qss(t))
        lay = QVBoxLayout(dlg); lay.setContentsMargins(32,20,32,20); lay.setSpacing(12)
        tl = QLabel("管理空间"); tl.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};"); lay.addWidget(tl)
        for w in self.workspaces:
            row = QHBoxLayout(); tp = "个人" if w.get("ws_type","personal") == "personal" else "经营"
            row.addWidget(QLabel(f"{w['icon']} {w['name']}")); tl2 = QLabel(tp); tl2.setStyleSheet(f"font-size:12px;color:{t['muted']};background:{t['input_bg']};padding:2px 8px;border-radius:4px;"); row.addWidget(tl2)
            row.addStretch()
            eb = QPushButton("编辑"); eb.setObjectName("ghost"); eb.clicked.connect(lambda _, ws=w: self._edit_ws(ws, dlg)); row.addWidget(eb)
            db_ = QPushButton("删除"); db_.setObjectName("danger"); db_.clicked.connect(lambda _, ws=w: self._del_ws(ws, dlg)); row.addWidget(db_)
            lay.addLayout(row)
        cb = QPushButton("关闭"); cb.setObjectName("ghost"); cb.clicked.connect(dlg.accept); lay.addWidget(cb); dlg.exec()
    def _edit_ws(self, ws, pdlg):
        dlg = WorkspaceDialog(self, ws)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.result_data; db.update_workspace(ws["id"],d["name"],d["icon"],d["ws_type"])
            if self.cur_ws == ws["name"]: self.cur_ws = d["name"]
            self._load_ws(); self._load_data(); self._rebuild_nav(); pdlg.accept()
    def _del_ws(self, ws, pdlg):
        if QMessageBox.question(self,"删除",f"删除「{ws['name']}」？") == QMessageBox.StandardButton.Yes:
            try:
                moved = db.delete_workspace(ws["id"])
                if self.cur_ws == ws["name"]: self.cur_ws = moved
                self._load_ws(); self._load_data(); self._rebuild_nav(); pdlg.accept()
            except Exception as e: QMessageBox.warning(self,"错误",str(e))
    def _change_pwd(self):
        t = _current_theme; dlg = QDialog(self); dlg.setWindowTitle("修改密码"); dlg.setFixedWidth(400)
        dlg.setStyleSheet(build_qss(t))
        lay = QVBoxLayout(dlg); lay.setContentsMargins(32,20,32,20); lay.setSpacing(12)
        tl = QLabel("修改密码"); tl.setStyleSheet(f"font-size:22px;font-weight:700;color:{t['text']};"); lay.addWidget(tl)
        oe = QLineEdit(); oe.setEchoMode(QLineEdit.EchoMode.Password); oe.setPlaceholderText("当前密码"); lay.addWidget(oe)
        ne = QLineEdit(); ne.setEchoMode(QLineEdit.EchoMode.Password); ne.setPlaceholderText("新密码"); lay.addWidget(ne)
        n2 = QLineEdit(); n2.setEchoMode(QLineEdit.EchoMode.Password); n2.setPlaceholderText("确认新密码"); lay.addWidget(n2)
        btns = QHBoxLayout(); btns.addStretch()
        c = QPushButton("取消"); c.setObjectName("ghost"); c.clicked.connect(dlg.reject); btns.addWidget(c)
        s = QPushButton("确认"); s.setObjectName("primary")
        def do():
            if ne.text() != n2.text(): QMessageBox.warning(dlg,"提示","两次不一致"); return
            nk = db.change_master_password(oe.text(), ne.text(), self.key)
            if nk: self.key = nk; QMessageBox.information(dlg,"成功","已修改"); dlg.accept()
            else: QMessageBox.warning(dlg,"错误","原密码错误")
        s.clicked.connect(do); btns.addWidget(s); lay.addLayout(btns); dlg.exec()
    def _toggle_theme(self):
        global _current_theme
        _current_theme = LIGHT_THEME if _current_theme["is_dark"] else DARK_THEME
        t = _current_theme
        self.theme_btn.setText("☀️" if t["is_dark"] else "🌙")
        self.theme_btn.setStyleSheet(f"border:1px solid {t['border']};border-radius:10px;background:{t['card']};font-size:14px;padding:0;")
        QApplication.instance().setStyleSheet(build_qss(_current_theme))
        self._style_sidebar(); self._style_topbar(); self._apply_titlebar(); self._load_ws()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, _current_theme["is_dark"])
        self._load_data(); self._refresh()
    def _lock(self): self._lock_timer.stop(); self.close()
    def _restore(self, aid): db.restore_account(aid); self._load_data(); self._pg_rec()
    def _perm_del(self, aid):
        if QMessageBox.question(self,"彻底删除","不可恢复，确认？") == QMessageBox.StandardButton.Yes: db.permanent_delete(aid); self._pg_rec()
    def _empty_rec(self):
        if QMessageBox.question(self,"清空","清空回收站？") == QMessageBox.StandardButton.Yes: db.empty_recycle(); self._load_data(); self._pg_rec()
    def _export(self):
        try:
            content, fn = db.export_data(self.key)
            path, _ = QFileDialog.getSaveFileName(self,"导出",fn,"JSON (*.json)")
            if path:
                with open(path,"w",encoding="utf-8") as f: f.write(content)
                QMessageBox.information(self,"成功",f"已导出到 {path}")
        except Exception as e: QMessageBox.critical(self,"失败",str(e))
    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self,"导入","","JSON (*.json);;CSV (*.csv)")
        if not path: return
        try:
            with open(path,"r",encoding="utf-8") as f: text = f.read()
            if path.lower().endswith(".csv"): count = db.import_csv_text(text, self.key, self.cur_ws)
            else:
                items = json.loads(text)
                if not isinstance(items, list): QMessageBox.warning(self,"格式错误","JSON应为数组"); return
                count = db.import_json(items, self.key)
            QMessageBox.information(self,"成功",f"已导入 {count} 条"); self._load_data(); self._refresh()
        except Exception as e: QMessageBox.critical(self,"失败",str(e))
    def _migrate(self):
        dlg = MigrateDialog(self, self.key, self.workspaces)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result:
            self._load_ws(); self._load_data(); self._rebuild_nav(); self._refresh()

def main():
    app = QApplication(sys.argv)
    global _current_theme
    hour = datetime.now().hour
    _current_theme = DARK_THEME if (hour >= 19 or hour < 7) else LIGHT_THEME
    app.setStyleSheet(build_qss(_current_theme))
    db.init_db()
    db.auto_backup()
    is_init = not db.is_initialized()
    login = LoginDialog(is_init)
    if login.exec() != QDialog.DialogCode.Accepted: sys.exit(0)
    win = MainWindow(login.key); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
