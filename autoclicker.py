import threading
import time
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui
import keyboard

CONFIG_FILE = "config.json"


class AutoClicker:
    def __init__(self):
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # 기본 설정
        self.cps = 10.0
        self.button = "left"

        # 설정 파일 로드
        self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cps = float(data.get("cps", self.cps))
            self.button = data.get("button", self.button)
        except Exception:
            # 설정 파일이 깨져도 프로그램은 계속 동작하게
            pass

    def save_config(self, cps, button):
        self.cps = cps
        self.button = button
        data = {"cps": self.cps, "button": self.button}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def start(self):
        with self.lock:
            if self.running:
                return
            self.running = True
            self.thread = threading.Thread(target=self._click_loop, daemon=True)
            self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False

    def _click_loop(self):
        while True:
            with self.lock:
                if not self.running:
                    break
                cps = self.cps
                button = self.button

            # cps 가 0 또는 음수가 되지 않도록 보호
            if cps <= 0:
                time.sleep(0.1)
                continue

            interval = 1.0 / cps
            pyautogui.click(button=button)
            time.sleep(interval)


class AutoClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python 오토클릭")

        # pyautogui failsafe 비활성화(마우스를 구석으로 보내도 예외 안나게)
        pyautogui.FAILSAFE = False

        self.clicker = AutoClicker()

        # UI 구성
        self.create_widgets()
        self.bind_hotkeys()

        # 초기 값 반영
        self.cps_var.set(str(self.clicker.cps))
        self.button_var.set("좌클릭" if self.clicker.button == "left" else "우클릭")
        self.update_status_label()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # CPS 입력
        ttk.Label(main_frame, text="초당 클릭 횟수 (CPS):").grid(
            row=0, column=0, sticky="w"
        )
        self.cps_var = tk.StringVar()
        cps_entry = ttk.Entry(main_frame, textvariable=self.cps_var, width=10)
        cps_entry.grid(row=0, column=1, sticky="w", padx=(5, 0))

        # 버튼 선택 (좌/우클릭)
        ttk.Label(main_frame, text="마우스 버튼:").grid(
            row=1, column=0, sticky="w", pady=(5, 0)
        )
        self.button_var = tk.StringVar()
        button_combo = ttk.Combobox(
            main_frame,
            textvariable=self.button_var,
            values=["좌클릭", "우클릭"],
            state="readonly",
            width=8,
        )
        button_combo.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(5, 0))

        # 설정 저장 버튼
        save_button = ttk.Button(main_frame, text="설정 저장", command=self.on_save)
        save_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # 상태 라벨
        self.status_label = ttk.Label(main_frame, text="", foreground="blue")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # 단축키 안내
        hotkey_info = (
            "단축키:\n"
            " - F4: 오토클릭 시작\n"
            " - F5: 오토클릭 정지"
        )
        ttk.Label(main_frame, text=hotkey_info, justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

    def bind_hotkeys(self):
        # keyboard 라이브러리로 전역 핫키 등록
        keyboard.add_hotkey("f4", self.on_hotkey_start)
        keyboard.add_hotkey("f5", self.on_hotkey_stop)

        # 창이 닫힐 때 핫키 해제
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_hotkey_start(self):
        self.clicker.start()
        # tkinter UI 업데이트는 메인 스레드에서
        self.root.after(0, self.update_status_label)

    def on_hotkey_stop(self):
        self.clicker.stop()
        self.root.after(0, self.update_status_label)

    def on_save(self):
        try:
            cps_str = self.cps_var.get().strip().replace(",", ".")
            cps = float(cps_str)
            if cps <= 0:
                raise ValueError

            button_text = self.button_var.get()
            if button_text == "좌클릭":
                button = "left"
            else:
                button = "right"

            self.clicker.save_config(cps, button)
            messagebox.showinfo("저장 완료", "설정을 저장했습니다.")
            self.update_status_label()
        except ValueError:
            messagebox.showerror("오류", "CPS에는 0보다 큰 숫자를 입력하세요.")

    def update_status_label(self):
        status = "실행 중" if self.clicker.running else "정지"
        button_text = "좌클릭" if self.clicker.button == "left" else "우클릭"
        text = (
            f"상태: {status} / CPS: {self.clicker.cps} / 버튼: {button_text}\n"
            "F4로 시작, F5로 정지할 수 있습니다."
        )
        self.status_label.config(text=text)

    def on_close(self):
        # 종료 시 오토클릭 중지 및 핫키 해제
        self.clicker.stop()
        keyboard.unhook_all_hotkeys()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AutoClickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
