import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
from collections import Counter
import random
import json
import os
import re
import threading
import time

class CipherTool:
    def __init__(self, root):
        self.root = root
        self.root.title("单表代换工具")
        self.root.geometry("1400x800")
        
        # 存储当前密钥和固定密钥对
        self.key = {chr(97 + i): chr(97 + i) for i in range(26)}
        self.fixed_pairs = {}  # 存储固定的密钥对
        self.current_page = None
        self.current_page_frame = None
        
        # 缓存文本内容
        self.cached_plaintext = ""
        self.cached_ciphertext = ""
        self.cached_decrypt_text = ""
        
        # 标记示例文本状态
        self.plaintext_has_example = True
        self.decrypt_text_has_example = True
        
        # 词典相关
        self.dictionary = set()  # 存储词典单词
        self.dictionary_path = "dictionary.txt"  # 默认词典路径
        self.load_dictionary()  # 尝试加载词典
        
        # 自动破译相关
        self.is_breaking = False  # 是否正在进行自动破译
        self.break_thread = None  # 自动破译线程
        self.best_key = None  # 最佳密钥
        self.best_match_count = 0  # 最佳匹配数
        self.iterations = 0  # 迭代次数
        self.max_iterations = 1000000  # 最大迭代次数
        self.last_updated_iterations = 0  # 上次更新界面的迭代次数
        self.update_interval = 1000  # 界面更新间隔
        
        # 设置主题样式
        self.style = ttk.Style()
        
        # 普通按钮样式
        self.style.configure('TButton', font=('宋体', 10), foreground='black')
        self.style.configure('Inactive.TButton', font=('宋体', 10), foreground='gray')
        self.style.configure('Active.TButton', font=('宋体', 10, 'bold'), foreground='gray', background='#e0e0e0')
        self.style.configure('Stop.TButton', font=('宋体', 10), foreground='white', background='red')
        
        self.style.configure('TLabel', font=('宋体', 10))
        self.style.configure('TFrame', background='white')
        
        # 创建顶部按钮框架
        self.create_top_buttons()
        
        # 默认显示解密页面
        self.current_page = 'decrypt'
        self.show_page('decrypt')
        
        # 模拟点击加密按钮
        self.show_page('encrypt')
        
        # 强制更新显示
        self.root.update_idletasks()
        self.update_key_display()

    def load_dictionary(self):
        """加载词典文件"""
        try:
            if os.path.exists(self.dictionary_path):
                with open(self.dictionary_path, 'r', encoding='utf-8') as file:
                    self.dictionary = {line.strip().lower() for line in file if line.strip()}
                print(f"成功加载词典，包含 {len(self.dictionary)} 个单词")
                return True
            else:
                print(f"词典文件 {self.dictionary_path} 不存在")
                return False
        except Exception as e:
            print(f"加载词典时出错: {str(e)}")
            return False

    def create_top_buttons(self):
        # 创建顶部按钮框架
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 加密按钮
        self.encrypt_btn = ttk.Button(
            self.button_frame, 
            text="加密", 
            command=lambda: self.show_page('encrypt')
        )
        self.encrypt_btn.pack(side=tk.LEFT, padx=5)
        
        # 解密按钮
        self.decrypt_btn = ttk.Button(
            self.button_frame, 
            text="解密", 
            command=lambda: self.show_page('decrypt')
        )
        self.decrypt_btn.pack(side=tk.LEFT, padx=5)
        
        # 初始按钮状态
        self.update_button_state()

    def show_page(self, page_name):
        if self.current_page == page_name:  # 如果已经在目标页面，不重复操作
            return
        
        # 保存当前页面的文本内容
        self.clear_frame()
        
        self.current_page = page_name
        
        if page_name == 'encrypt':
            self.create_encrypt_page()
        elif page_name == 'decrypt':
            self.create_decrypt_page()
            
        self.update_button_state()
        self.root.update_idletasks()  # 确保界面立即更新

    def update_button_state(self):
        # 更新按钮状态
        if hasattr(self, 'encrypt_btn') and hasattr(self, 'decrypt_btn'):
            self.encrypt_btn.config(style='Active.TButton' if self.current_page == 'encrypt' else 'TButton')
            self.decrypt_btn.config(style='Active.TButton' if self.current_page == 'decrypt' else 'TButton')

    def clear_frame(self):
        # 保存当前页面的文本内容
        if self.current_page == 'encrypt':
            if hasattr(self, 'plaintext_area') and self.plaintext_area.winfo_exists():
                self.cached_plaintext = self.plaintext_area.get("1.0", tk.END).strip()
        elif self.current_page == 'decrypt':
            if hasattr(self, 'decrypt_text_area') and self.decrypt_text_area.winfo_exists():
                self.cached_decrypt_text = self.decrypt_text_area.get("1.0", tk.END).strip()
        
        # 清除当前页面
        if self.current_page_frame and self.current_page_frame.winfo_exists():
            self.current_page_frame.destroy()
            self.current_page_frame = None

    def create_encrypt_page(self):
        self.current_page_frame = ttk.Frame(self.root, padding=10)
        self.current_page_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：加密模块
        left_frame = ttk.Frame(self.current_page_frame, width=480, padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(left_frame, text="明文输入", font=("黑体", 14, "bold")).pack(pady=10)
        
        self.plaintext_area = scrolledtext.ScrolledText(left_frame, height=15, wrap=tk.WORD, font=("宋体", 10))
        self.plaintext_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 设置示例文本或恢复缓存文本
        if not self.cached_plaintext:
            self.plaintext_area.insert(tk.END, "请在此输入明文...")
            self.plaintext_has_example = True
            self.plaintext_area.bind("<FocusIn>", self.on_plaintext_focus_in)
        else:
            self.plaintext_area.insert(tk.END, self.cached_plaintext)
            self.plaintext_has_example = False
        
        # 密钥显示与编辑
        key_frame = ttk.Frame(left_frame)
        key_frame.pack(pady=10, fill=tk.X)
        
        ttk.Label(key_frame, text="当前密钥：", font=("黑体", 10)).pack(side=tk.LEFT, padx=5)
        self.encrypt_key_display = ttk.Label(key_frame, text="a-a, b-b, ..., z-z", wraplength=350)
        self.encrypt_key_display.pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(btn_frame, text="编辑密钥", command=self.edit_key).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="加密", command=self.perform_encryption).pack(side=tk.RIGHT, padx=10)
        
        # 保存加密结果按钮
        ttk.Button(btn_frame, text="保存加密结果", command=self.save_encrypted_text).pack(side=tk.RIGHT, padx=10)
        
        # 新增保存密钥、读取密钥和清空文本按钮
        ttk.Button(btn_frame, text="保存密钥", command=self.save_key).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="读取密钥", command=self.load_key).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="清空文本", command=lambda: self.clear_text('encrypt')).pack(side=tk.LEFT, padx=10)
        
        # 新增读取文本按钮
        ttk.Button(btn_frame, text="读取文本", command=lambda: self.load_text('encrypt')).pack(side=tk.LEFT, padx=10)
        
        # 右侧：加密结果
        right_frame = ttk.Frame(self.current_page_frame, width=480, padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_frame, text="加密结果", font=("黑体", 14, "bold")).pack(pady=10)
        
        self.ciphertext_area = scrolledtext.ScrolledText(right_frame, height=15, wrap=tk.WORD, font=("宋体", 10))
        self.ciphertext_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.ciphertext_area.insert(tk.END, self.cached_ciphertext)
        
        # 更新密钥显示
        self.update_key_display()

    def create_decrypt_page(self):
        self.current_page_frame = ttk.Frame(self.root, padding=10)
        self.current_page_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：解密模块
        left_frame = ttk.Frame(self.current_page_frame, width=480, padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(left_frame, text="密文输入", font=("黑体", 14, "bold")).pack(pady=10)
        
        self.decrypt_text_area = scrolledtext.ScrolledText(left_frame, height=10, wrap=tk.WORD, font=("宋体", 10))
        self.decrypt_text_area.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 设置示例文本或恢复缓存文本
        if not self.cached_decrypt_text:
            self.decrypt_text_area.insert(tk.END, "请在此输入密文...")
            self.decrypt_text_has_example = True
            self.decrypt_text_area.bind("<FocusIn>", self.on_decrypt_text_focus_in)
        else:
            self.decrypt_text_area.insert(tk.END, self.cached_decrypt_text)
            self.decrypt_text_has_example = False
        
        # 密钥显示与编辑
        key_frame = ttk.Frame(left_frame)
        key_frame.pack(pady=10, fill=tk.X)
        
        ttk.Label(key_frame, text="当前密钥：", font=("黑体", 10)).pack(side=tk.LEFT, padx=5)
        self.decrypt_key_display = ttk.Label(key_frame, text="a-a, b-b, ..., z-z", wraplength=350)
        self.decrypt_key_display.pack(side=tk.LEFT, padx=5)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(btn_frame, text="编辑密钥", command=self.edit_key).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="解密", command=self.perform_decryption).pack(side=tk.RIGHT, padx=10)
        
        # 保存解密结果按钮
        ttk.Button(btn_frame, text="保存解密结果", command=self.save_decrypted_text).pack(side=tk.RIGHT, padx=10)
        
        # 新增保存密钥、读取密钥和清空文本按钮
        ttk.Button(btn_frame, text="保存密钥", command=self.save_key).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="读取密钥", command=self.load_key).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="清空文本", command=lambda: self.clear_text('decrypt')).pack(side=tk.LEFT, padx=10)
        
        # 新增读取文本按钮
        ttk.Button(btn_frame, text="读取文本", command=lambda: self.load_text('decrypt')).pack(side=tk.LEFT, padx=10)
        
        # 新增加载词典按钮
        ttk.Button(btn_frame, text="加载词典", command=self.load_dictionary_gui).pack(side=tk.LEFT, padx=10)
        
        # 新增自动破译按钮
        self.break_btn = ttk.Button(
            btn_frame, 
            text="重复破译", 
            command=self.start_breaking,
            style='TButton' if not self.is_breaking else 'Stop.TButton'
        )
        self.break_btn.pack(side=tk.LEFT, padx=10)
        
        # 右侧：破译辅助
        right_frame = ttk.Frame(self.current_page_frame, width=480, padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_frame, text="破译辅助", font=("黑体", 14, "bold")).pack(pady=10)
        
        # 频率统计
        freq_frame = ttk.LabelFrame(right_frame, text="频率统计", padding=10)
        freq_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.freq_high_display = scrolledtext.ScrolledText(freq_frame, height=5, wrap=tk.WORD, font=("宋体", 10))
        self.freq_high_display.pack(pady=5, fill=tk.BOTH, expand=True)
        self.freq_high_display.insert(tk.END, "最高频率字母将显示在这里...")
        
        self.freq_low_display = scrolledtext.ScrolledText(freq_frame, height=5, wrap=tk.WORD, font=("宋体", 10))
        self.freq_low_display.pack(pady=5, fill=tk.BOTH, expand=True)
        self.freq_low_display.insert(tk.END, "最低频率字母将显示在这里...")
        
        # 词典匹配结果
        dict_frame = ttk.LabelFrame(right_frame, text="词典匹配结果", padding=10)
        dict_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.dict_match_display = scrolledtext.ScrolledText(dict_frame, height=5, wrap=tk.WORD, font=("宋体", 10))
        self.dict_match_display.pack(pady=5, fill=tk.BOTH, expand=True)
        self.dict_match_display.insert(tk.END, "词典匹配结果将显示在这里...")
        
        # 词典匹配统计
        self.dict_stats = ttk.Label(dict_frame, text="匹配单词数: 0", font=("宋体", 10))
        self.dict_stats.pack(pady=5, fill=tk.X)
        
        # 自动破译进度
        break_frame = ttk.LabelFrame(right_frame, text="自动破译进度", padding=10)
        break_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.break_progress = ttk.Label(break_frame, text="迭代次数: 0", font=("宋体", 10))
        self.break_progress.pack(pady=5, fill=tk.X)
        
        self.best_match = ttk.Label(break_frame, text="最佳匹配: 0", font=("宋体", 10))
        self.best_match.pack(pady=5, fill=tk.X)
        
        # 破译意见
        advice_frame = ttk.LabelFrame(right_frame, text="破译意见", padding=10)
        advice_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.advice_display = scrolledtext.ScrolledText(advice_frame, height=5, wrap=tk.WORD, font=("宋体", 10))
        self.advice_display.pack(pady=5, fill=tk.BOTH, expand=True)
        self.advice_display.insert(tk.END, "破译建议将显示在这里...")
        
        # 更新密钥显示
        self.update_key_display()
        
        # 如果有密文且不是示例文本，更新解密结果
        if self.cached_decrypt_text and self.cached_decrypt_text != "请在此输入密文...":
            self.update_decrypt_results()

    def load_dictionary_gui(self):
        """通过GUI界面加载词典文件"""
        file_path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if file_path:
            self.dictionary_path = file_path
            if self.load_dictionary():
                messagebox.showinfo("成功", f"词典加载成功，包含 {len(self.dictionary)} 个单词")
                # 如果当前在解密页面且有密文，更新匹配结果
                if self.current_page == 'decrypt' and self.cached_decrypt_text and self.cached_decrypt_text != "请在此输入密文...":
                    self.update_decrypt_results()
            else:
                messagebox.showerror("错误", "词典加载失败")

    def on_plaintext_focus_in(self, event):
        if self.plaintext_has_example:
            self.plaintext_area.delete("1.0", tk.END)
            self.plaintext_has_example = False

    def on_decrypt_text_focus_in(self, event):
        if self.decrypt_text_has_example:
            self.decrypt_text_area.delete("1.0", tk.END)
            self.decrypt_text_has_example = False

    def edit_key(self):
        # 创建密钥编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑密钥")
        edit_window.geometry("800x600")
        
        # 主框架
        main_frame = ttk.Frame(edit_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 密钥文本区域
        ttk.Label(main_frame, text="编辑代换规则（格式：a-a, b-b, ...）：", font=("黑体", 12)).pack(pady=10)
        key_text = scrolledtext.ScrolledText(main_frame, height=10, wrap=tk.WORD, font=("宋体", 10))
        key_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 显示当前密钥
        current_key_text = ", ".join([f"{k}-{v}" for k, v in sorted(self.key.items())])
        key_text.insert(tk.END, current_key_text)
        
        # 固定密钥对区域
        fixed_frame = ttk.LabelFrame(main_frame, text="固定的密钥对（不会被随机生成改变）", padding=10)
        fixed_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        fixed_text = scrolledtext.ScrolledText(fixed_frame, height=5, wrap=tk.WORD, font=("宋体", 10))
        fixed_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 显示当前固定的密钥对
        if self.fixed_pairs:
            fixed_pairs_text = ", ".join([f"{k}-{v}" for k, v in sorted(self.fixed_pairs.items())])
            fixed_text.insert(tk.END, fixed_pairs_text)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10, fill=tk.X)
        
        # 随机生成按钮
        def generate_random_key():
            # 获取固定的密钥对
            fixed_pairs_str = fixed_text.get("1.0", tk.END).strip()
            new_fixed_pairs = {}
            
            for pair in fixed_pairs_str.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                parts = pair.split("-")
                if len(parts) != 2:
                    continue
                ciph, plain = parts
                ciph = ciph.lower()
                plain = plain.lower()
                if len(ciph) == 1 and len(plain) == 1 and ciph.isalpha() and plain.isalpha():
                    new_fixed_pairs[ciph] = plain
            
            # 验证固定的密钥对是否有效
            if len(set(new_fixed_pairs.values())) != len(new_fixed_pairs):
                messagebox.showerror("错误", "固定的密钥对中存在重复的映射目标")
                return
            
            # 更新固定的密钥对
            self.fixed_pairs = new_fixed_pairs
            
            # 生成随机密钥，保留固定的映射
            letters = list('abcdefghijklmnopqrstuvwxyz')
            available_letters = [l for l in letters if l not in self.fixed_pairs.values()]
            random.shuffle(available_letters)
            
            random_key = {}
            available_index = 0
            
            for letter in letters:
                if letter in self.fixed_pairs:
                    random_key[letter] = self.fixed_pairs[letter]
                else:
                    if available_index < len(available_letters):
                        random_key[letter] = available_letters[available_index]
                        available_index += 1
            
            # 确保所有字母都有映射
            if len(random_key) < 26:
                remaining = [l for l in letters if l not in random_key.values()]
                for letter in letters:
                    if letter not in random_key:
                        if remaining:
                            random_key[letter] = remaining.pop()
            
            # 更新密钥文本区域
            key_text.delete("1.0", tk.END)
            key_text.insert(tk.END, ", ".join([f"{k}-{v}" for k, v in sorted(random_key.items())]))
        
        ttk.Button(btn_frame, text="随机生成", command=generate_random_key).pack(side=tk.LEFT, padx=10)
        
        # 反变换按钮
        def reverse_mapping():
            current_text = key_text.get("1.0", tk.END).strip()
            try:
                pairs = [pair.strip() for pair in current_text.split(",") if pair.strip()]
                reversed_pairs = []
                for pair in pairs:
                    if '-' in pair:
                        src, dst = pair.split('-', 1)
                        if len(src) == 1 and len(dst) == 1 and src.isalpha() and dst.isalpha():
                            reversed_pairs.append(f"{dst}-{src}")
                key_text.delete("1.0", tk.END)
                key_text.insert(tk.END, ", ".join(sorted(reversed_pairs)))
            except:
                messagebox.showerror("格式错误", "无法解析当前代换规则")
        
        ttk.Button(btn_frame, text="反向", command=reverse_mapping).pack(side=tk.LEFT, padx=10)
        
        # 设置选中的密钥对为固定
        def set_selected_as_fixed():
            try:
                selected_text = key_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if not selected_text:
                    messagebox.showwarning("警告", "请先选择要固定的密钥对")
                    return
                
                # 解析选中的文本
                pairs = [pair.strip() for pair in selected_text.split(",") if pair.strip()]
                valid_pairs = []
                
                for pair in pairs:
                    if '-' in pair:
                        src, dst = pair.split('-', 1)
                        if len(src) == 1 and len(dst) == 1 and src.isalpha() and dst.isalpha():
                            valid_pairs.append(pair)
                
                if not valid_pairs:
                    messagebox.showwarning("警告", "选择的内容中没有有效的密钥对")
                    return
                
                # 更新固定的密钥对文本区域
                current_fixed = fixed_text.get("1.0", tk.END).strip()
                if current_fixed:
                    current_pairs = [p.strip() for p in current_fixed.split(",") if p.strip()]
                else:
                    current_pairs = []
                
                # 合并并去重
                all_pairs = list(set(current_pairs + valid_pairs))
                
                fixed_text.delete("1.0", tk.END)
                fixed_text.insert(tk.END, ", ".join(sorted(all_pairs)))
                
            except tk.TclError:
                messagebox.showwarning("警告", "请先选择要固定的密钥对")
        
        ttk.Button(btn_frame, text="固定选中的密钥对", command=set_selected_as_fixed).pack(side=tk.LEFT, padx=10)
        
        # 清除所有固定的密钥对
        def clear_all_fixed():
            fixed_text.delete("1.0", tk.END)
        
        ttk.Button(btn_frame, text="清除所有固定", command=clear_all_fixed).pack(side=tk.LEFT, padx=10)
        
               # 确认修改按钮
        def confirm_edit():
            input_str = key_text.get("1.0", tk.END).strip()
            try:
                # 解析输入的密钥对
                new_key = {}
                for pair in input_str.split(","):
                    pair = pair.strip()
                    if not pair:
                        continue
                    parts = pair.split("-")
                    if len(parts) != 2:
                        raise ValueError(f"格式错误: {pair}")
                    ciph, plain = parts
                    ciph = ciph.lower()
                    plain = plain.lower()
                    if len(ciph) == 1 and len(plain) == 1 and ciph.isalpha() and plain.isalpha():
                        # 检查是否有重复的密文映射
                        if ciph in new_key:
                            messagebox.showerror("格式错误", f"密文字母 '{ciph}' 有重复的映射")
                            return
                        # 检查是否有重复的明文映射
                        if plain in new_key.values():
                            # 找出已经映射到这个明文的密文
                            conflicting_ciph = [k for k, v in new_key.items() if v == plain][0]
                            messagebox.showerror("格式错误", f"明文 '{plain}' 已被密文 '{conflicting_ciph}' 映射")
                            return
                        new_key[ciph] = plain
                    else:
                        raise ValueError(f"无效的字符: {pair}")
                
                # 检查是否覆盖所有字母
                if len(new_key) != 26:
                    missing = [chr(97+i) for i in range(26) if chr(97+i) not in new_key]
                    messagebox.showerror("格式错误", f"缺少字母映射: {', '.join(missing)}")
                    return
                
                # 检查固定的密钥对是否被修改
                fixed_pairs_str = fixed_text.get("1.0", tk.END).strip()
                new_fixed_pairs = {}
                
                if fixed_pairs_str:  # 检查输入是否为空
                    for pair in fixed_pairs_str.split(","):
                        pair = pair.strip()
                        if not pair:
                            continue
                        parts = pair.split("-")
                        if len(parts) != 2:
                            continue
                        ciph, plain = parts
                        ciph = ciph.lower()
                        plain = plain.lower()
                        if len(ciph) == 1 and len(plain) == 1 and ciph.isalpha() and plain.isalpha():
                            new_fixed_pairs[ciph] = plain                
                # 更新密钥
                self.key = new_key
                self.fixed_pairs = new_fixed_pairs
                
                self.update_key_display()
                if self.current_page == 'decrypt':
                    self.update_decrypt_results()
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("格式错误", str(e))
        
        ttk.Button(btn_frame, text="确认修改", command=confirm_edit).pack(side=tk.RIGHT, padx=10)
        
        # 取消按钮
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT, padx=10)
        
        ttk.Button(btn_frame, text="确认修改", command=confirm_edit).pack(side=tk.RIGHT, padx=10)
        
        # 取消按钮
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy).pack(side=tk.RIGHT, padx=10)

    def update_key_display(self):
        # 更新密钥显示
        key_text = ", ".join([f"{k}-{v}" for k, v in sorted(self.key.items())])
        if hasattr(self, 'encrypt_key_display') and self.encrypt_key_display.winfo_exists():
            self.encrypt_key_display.config(text=key_text)
        if hasattr(self, 'decrypt_key_display') and self.decrypt_key_display.winfo_exists():
            self.decrypt_key_display.config(text=key_text)

    def perform_encryption(self):
        # 检查是否为示例文本
        if self.plaintext_has_example:
            self.plaintext_area.delete("1.0", tk.END)
            self.plaintext_has_example = False
            return
            
        # 执行加密
        plaintext = self.plaintext_area.get("1.0", tk.END).strip()
        if not plaintext:
            messagebox.showwarning("警告", "请输入明文")
            return
        
        encrypted_text = []
        for c in plaintext:
            if c.isalpha():
                if c.isupper():
                    encrypted_text.append(self.key[c.lower()].upper())
                else:
                    encrypted_text.append(self.key[c])
            else:
                encrypted_text.append(c)
        
        self.ciphertext_area.delete("1.0", tk.END)
        self.ciphertext_area.insert(tk.END, "".join(encrypted_text))
        self.cached_ciphertext = "".join(encrypted_text)

    def perform_decryption(self):
        # 检查是否为示例文本
        if self.decrypt_text_has_example:
            self.decrypt_text_area.delete("1.0", tk.END)
            self.decrypt_text_has_example = False
            return
            
        # 执行解密
        ciphertext = self.decrypt_text_area.get("1.0", tk.END).strip()
        if not ciphertext:
            messagebox.showwarning("警告", "请输入密文")
            return
        
        # 更新解密结果
        self.update_decrypt_results()
        
        # 弹出解密结果窗口
        self.show_decryption_window()

    def show_decryption_window(self):
        """显示解密结果窗口"""
        # 创建解密结果窗口
        decrypt_window = tk.Toplevel(self.root)
        decrypt_window.title("解密结果")
        decrypt_window.geometry("900x900") 
        
        # 确保窗口在最前面
        decrypt_window.transient(self.root)
        decrypt_window.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(decrypt_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 密钥信息
        key_frame = ttk.LabelFrame(main_frame, text="当前使用的密钥", padding=10)
        key_frame.pack(pady=10, fill=tk.X)
        
        key_text = ", ".join([f"{k}-{v}" for k, v in sorted(self.key.items())])
        ttk.Label(key_frame, text=key_text, wraplength=800).pack(pady=5)
        
        # 解密结果
        result_frame = ttk.LabelFrame(main_frame, text="解密文本", padding=10)
        result_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        reverse_key = {v: k for k, v in self.key.items()}
        ciphertext = self.decrypt_text_area.get("1.0", tk.END).strip()
        decrypted_text = []
        
        for c in ciphertext:
            if c.isalpha():
                if c.isupper():
                    decrypted_text.append(reverse_key.get(c.lower(), '*').upper())
                else:
                    decrypted_text.append(reverse_key.get(c, '*'))
            else:
                decrypted_text.append(c)
        
        decrypted_text_str = "".join(decrypted_text)
        
        result_text = scrolledtext.ScrolledText(result_frame, height=15, wrap=tk.WORD, font=("宋体", 10))
        result_text.pack(pady=5, fill=tk.BOTH, expand=True)
        result_text.insert(tk.END, decrypted_text_str)
        
        # 频率分析 - 使用解密后的文本
        freq_frame = ttk.LabelFrame(main_frame, text="频率分析", padding=10)
        freq_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # 最高频率字母
        high_frame = ttk.Frame(freq_frame)
        high_frame.pack(pady=5, fill=tk.X)
        
        ttk.Label(high_frame, text="最高频率字母:", font=("宋体", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        # 使用解密后的文本计算频率
        freq = Counter(c.lower() for c in decrypted_text_str if c.isalpha())
        high_freq = freq.most_common(10)
        
        high_freq_text = ""
        for letter, count in high_freq:
            high_freq_text += f"{letter}: {count}次 ({count/len(decrypted_text_str)*100:.2f}%)  "
        
        ttk.Label(high_frame, text=high_freq_text, font=("宋体", 10)).pack(side=tk.LEFT, padx=5)
        
        # 最低频率字母
        low_frame = ttk.Frame(freq_frame)
        low_frame.pack(pady=5, fill=tk.X)
        
        ttk.Label(low_frame, text="最低频率字母:", font=("宋体", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        low_freq = sorted(freq.items(), key=lambda x: x[1])[:10]
        
        low_freq_text = ""
        for letter, count in low_freq:
            low_freq_text += f"{letter}: {count}次 ({count/len(decrypted_text_str)*100:.2f}%)  "
        
        ttk.Label(low_frame, text=low_freq_text, font=("宋体", 10)).pack(side=tk.LEFT, padx=5)
        
        # 双字母组合分析 - 使用解密后的文本
        bigram_frame = ttk.LabelFrame(main_frame, text="双字母组合分析", padding=10)
        bigram_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # 提取双字母组合 - 使用解密后的文本
        bigrams = []
        for i in range(len(decrypted_text_str)-1):
            if decrypted_text_str[i].isalpha() and decrypted_text_str[i+1].isalpha():
                bigrams.append(decrypted_text_str[i].lower() + decrypted_text_str[i+1].lower())
        
        if bigrams:
            bigram_freq = Counter(bigrams)
            common_bigrams = bigram_freq.most_common(10)
            
            bigram_text = "最常见的双字母组合:\n"
            for bigram, count in common_bigrams:
                bigram_text += f"{bigram}: {count}次\n"
            
            bigram_display = scrolledtext.ScrolledText(bigram_frame, height=5, wrap=tk.WORD, font=("宋体", 10))
            bigram_display.pack(pady=5, fill=tk.BOTH, expand=True)
            bigram_display.insert(tk.END, bigram_text)
        else:
            ttk.Label(bigram_frame, text="没有足够的文本进行双字母组合分析").pack(pady=5)
        
        # 词典匹配
        dict_frame = ttk.LabelFrame(main_frame, text="词典匹配结果", padding=10)
        dict_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        dict_text = scrolledtext.ScrolledText(dict_frame, height=10, wrap=tk.WORD, font=("宋体", 10))
        dict_text.pack(pady=5, fill=tk.BOTH, expand=True)
        
        if self.dictionary:
            words = re.findall(r'\b[a-zA-Z]+\b', decrypted_text_str.lower())
            if words:
                matched_words = []
                for word in words:
                    if word in self.dictionary:
                        matched_words.append(word)
                
                if matched_words:
                    word_freq = Counter(matched_words)
                    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                    
                    match_text = "匹配的单词:\n"
                    for word, count in sorted_words[:20]:  # 只显示前20个最常见的匹配单词
                        match_text += f"{word}: {count}次\n"
                    
                    match_text += f"\n总共匹配到 {len(matched_words)} 个单词，占总单词数的 {len(matched_words)/len(words)*100:.2f}%"
                    dict_text.insert(tk.END, match_text)
                else:
                    dict_text.insert(tk.END, "未找到匹配的单词")
            else:
                dict_text.insert(tk.END, "未找到单词")
        else:
            dict_text.insert(tk.END, "未加载词典")
        
        # 破译建议
        advice_frame = ttk.LabelFrame(main_frame, text="破译建议", padding=10)
        advice_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        advice_text = scrolledtext.ScrolledText(advice_frame, height=10, wrap=tk.WORD, font=("宋体", 10))
        advice_text.pack(pady=5, fill=tk.BOTH, expand=True)
        
        # 生成破译建议
        advice = self.generate_decryption_advice(ciphertext, decrypted_text_str)
        advice_text.insert(tk.END, advice)
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10, fill=tk.X)
        
        # 编辑密钥按钮
        def edit_key_from_result():
            self.edit_key()
            decrypt_window.destroy()
            self.update_decrypt_results()
        
        ttk.Button(btn_frame, text="编辑密钥", command=edit_key_from_result).pack(side=tk.LEFT, padx=10)
        
        # 保存解密结果按钮
        def save_result():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(f"解密结果:\n\n{decrypted_text_str}\n\n")
                        file.write(f"使用的密钥:\n{key_text}\n\n")
                        file.write(f"频率分析:\n")
                        file.write(f"最高频率字母: {high_freq_text}\n")
                        file.write(f"最低频率字母: {low_freq_text}\n\n")
                        
                        if self.dictionary and matched_words:
                            file.write(f"词典匹配结果:\n")
                            for word, count in sorted_words:
                                file.write(f"{word}: {count}次\n")
                            file.write(f"\n总共匹配到 {len(matched_words)} 个单词，占总单词数的 {len(matched_words)/len(words)*100:.2f}%\n")
                    
                    messagebox.showinfo("成功", f"解密结果已保存到 {file_path}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存文件时出错: {str(e)}")
        
        ttk.Button(btn_frame, text="保存解密结果", command=save_result).pack(side=tk.RIGHT, padx=10)
        
        # 关闭按钮
        ttk.Button(btn_frame, text="关闭", command=decrypt_window.destroy).pack(side=tk.RIGHT, padx=10)

    def update_decrypt_results(self):
        """更新解密结果和辅助信息"""
        ciphertext = self.decrypt_text_area.get("1.0", tk.END).strip()
        if not ciphertext:
            return
        
        reverse_key = {v: k for k, v in self.key.items()}
        decrypted_text = []
        
        for c in ciphertext:
            if c.isalpha():
                if c.isupper():
                    decrypted_text.append(reverse_key.get(c.lower(), '*').upper())
                else:
                    decrypted_text.append(reverse_key.get(c, '*'))
            else:
                decrypted_text.append(c)
        
        decrypted_text_str = "".join(decrypted_text)
        
        # 更新频率分析
        self.update_frequency_analysis(ciphertext)
        
        # 更新词典匹配
        if self.dictionary:
            words = re.findall(r'\b[a-zA-Z]+\b', decrypted_text_str.lower())
            if words:
                matched_words = []
                for word in words:
                    if word in self.dictionary:
                        matched_words.append(word)
                
                if matched_words:
                    word_freq = Counter(matched_words)
                    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                    
                    match_text = "匹配的单词:\n"
                    for word, count in sorted_words[:10]:  # 只显示前10个最常见的匹配单词
                        match_text += f"{word}: {count}次\n"
                    
                    self.dict_match_display.delete("1.0", tk.END)
                    self.dict_match_display.insert(tk.END, match_text)
                    self.dict_stats.config(text=f"匹配单词数: {len(matched_words)}，占总单词数的 {len(matched_words)/len(words)*100:.2f}%")
                else:
                    self.dict_match_display.delete("1.0", tk.END)
                    self.dict_match_display.insert(tk.END, "未找到匹配的单词")
                    self.dict_stats.config(text=f"匹配单词数: 0")
            else:
                self.dict_match_display.delete("1.0", tk.END)
                self.dict_match_display.insert(tk.END, "未找到单词")
                self.dict_stats.config(text=f"匹配单词数: 0")
        else:
            self.dict_match_display.delete("1.0", tk.END)
            self.dict_match_display.insert(tk.END, "未加载词典")
            self.dict_stats.config(text=f"匹配单词数: 0")
        
        # 生成破译建议
        advice = self.generate_decryption_advice(ciphertext, decrypted_text_str)
        self.advice_display.delete("1.0", tk.END)
        self.advice_display.insert(tk.END, advice)

    def update_frequency_analysis(self, text):
        """更新频率分析结果"""
        # 计算字母频率
        freq = Counter(c.lower() for c in text if c.isalpha())
        
        # 最高频率字母
        high_freq = freq.most_common(10)
        high_freq_text = "最高频率字母:\n"
        for letter, count in high_freq:
            high_freq_text += f"{letter}: {count}次 ({count/sum(freq.values())*100:.2f}%)\n"
        
        self.freq_high_display.delete("1.0", tk.END)
        self.freq_high_display.insert(tk.END, high_freq_text)
        
        # 最低频率字母
        low_freq = sorted(freq.items(), key=lambda x: x[1])[:10]
        low_freq_text = "最低频率字母:\n"
        for letter, count in low_freq:
            low_freq_text += f"{letter}: {count}次 ({count/sum(freq.values())*100:.2f}%)\n"
        
        self.freq_low_display.delete("1.0", tk.END)
        self.freq_low_display.insert(tk.END, low_freq_text)

    def generate_decryption_advice(self, ciphertext, decrypted_text):
        """生成破译建议"""
        advice = []
        
        # 英语字母频率
        english_freq = {'e': 12.70, 't': 9.06, 'a': 8.17, 'o': 7.51, 'i': 6.97, 'n': 6.75, 
                        's': 6.33, 'h': 6.09, 'r': 5.99, 'd': 4.25, 'l': 4.03, 'c': 2.78, 
                        'u': 2.76, 'm': 2.41, 'w': 2.36, 'f': 2.23, 'g': 2.02, 'y': 1.97, 
                        'p': 1.93, 'b': 1.29, 'v': 0.98, 'k': 0.77, 'j': 0.15, 'x': 0.15, 
                        'q': 0.10, 'z': 0.07}
        
        # 计算密文频率
        cipher_freq = Counter(c.lower() for c in ciphertext if c.isalpha())
        total_letters = sum(cipher_freq.values())
        cipher_freq_percent = {letter: count/total_letters*100 for letter, count in cipher_freq.items()}
        
        # 计算解密文本频率
        decrypted_freq = Counter(c.lower() for c in decrypted_text if c.isalpha())
        decrypted_total_letters = sum(decrypted_freq.values())
        decrypted_freq_percent = {letter: count/decrypted_total_letters*100 for letter, count in decrypted_freq.items()}
        
        # 频率匹配建议
        advice.append("=== 频率分析建议 ===")
        for letter, freq in sorted(decrypted_freq_percent.items(), key=lambda x: x[1], reverse=True)[:5]:
            # 找到最接近的英语频率字母
            closest_letter = min(english_freq, key=lambda k: abs(english_freq[k] - freq))
            advice.append(f"解密后字母 '{letter}' 频率为 {freq:.2f}%，可能对应英语中的 '{closest_letter}'")
        
        # 英语语言规则建议
        advice.append("\n=== 英语语言规则建议 ===")
        
        # Q-U规则
        if 'q' in decrypted_freq:
            q_mapping = self.key.get('q', '')
            if q_mapping:
                u_mapping = self.key.get('u', '')
                if u_mapping:
                    if u_mapping != 'u':
                        advice.append(f"注意：在英语中，字母 'q' 后面几乎总是跟着 'u'。当前 'q' 映射到 '{q_mapping}'，'u' 映射到 '{u_mapping}'，可能需要调整。")
                else:
                    advice.append(f"注意：在英语中，字母 'q' 后面几乎总是跟着 'u'。当前 'q' 映射到 '{q_mapping}'，但 'u' 的映射可能需要检查。")
        
        # X前字母规则
        x_count = decrypted_freq.get('x', 0)
        if x_count > 0:
            x_mapping = self.key.get('x', '')
            if x_mapping:
                # 查找X前的字母
                x_positions = [i for i, c in enumerate(decrypted_text.lower()) if c == 'x']
                preceding_letters = []
                for pos in x_positions:
                    if pos > 0 and decrypted_text[pos-1].isalpha():
                        preceding_letters.append(decrypted_text[pos-1].lower())
                
                if preceding_letters:
                    preceding_freq = Counter(preceding_letters)
                    most_common = preceding_freq.most_common(1)[0][0]
                    mapped_preceding = self.key.get(most_common, '')
                    
                    if mapped_preceding not in ['i', 'e']:
                        advice.append(f"注意：在英语中，字母 'x' 前面通常是 'i' 或 'e'。当前解密文本中 'x' 前面最常见的字母是 '{most_common}'，映射到 '{mapped_preceding}'，可能需要调整。")
        
        # EE之间R高频规则
        e_count = decrypted_freq.get('e', 0)
        if e_count > 0:
            e_mapping = self.key.get('e', '')
            if e_mapping:
                # 查找EE之间的字母
                e_positions = [i for i, c in enumerate(decrypted_text.lower()) if c == 'e']
                middle_letters = []
                for i in range(len(e_positions)-1):
                    if e_positions[i+1] - e_positions[i] == 2:
                        middle_letters.append(decrypted_text[e_positions[i]+1].lower())
                
                if middle_letters:
                    middle_freq = Counter(middle_letters)
                    most_common = middle_freq.most_common(1)[0][0]
                    mapped_middle = self.key.get(most_common, '')
                    
                    if mapped_middle != 'r':
                        advice.append(f"注意：在英语中，'ee' 组合之间经常出现字母 'r'（如 'tree'、'three'）。当前解密文本中 'e' 之间最常见的字母是 '{most_common}'，映射到 '{mapped_middle}'，可能需要调整。")
        
        # 双字母组合分析 - 使用解密后的文本
        bigrams = []
        for i in range(len(decrypted_text)-1):
            if decrypted_text[i].isalpha() and decrypted_text[i+1].isalpha():
                bigrams.append(decrypted_text[i].lower() + decrypted_text[i+1].lower())
        
        if bigrams:
            bigram_freq = Counter(bigrams)
            common_bigrams = bigram_freq.most_common(5)
            
            # 英语中常见的双字母组合
            english_common_bigrams = ['th', 'he', 'in', 'er', 'an']
            
            advice.append("\n=== 双字母组合分析 ===")
            for bigram, count in common_bigrams:
                if bigram in english_common_bigrams:
                    advice.append(f"解密后双字母组合 '{bigram}' 出现 {count} 次，与英语常见组合匹配！")
                else:
                    advice.append(f"解密后双字母组合 '{bigram}' 出现 {count} 次，可能需要调整以匹配英语常见组合（如 'th', 'he', 'in', 'er', 'an'）")
        
        # 单字母单词分析
        words = re.findall(r'\b[a-zA-Z]+\b', decrypted_text.lower())
        one_letter_words = [word for word in words if len(word) == 1]
        
        if one_letter_words:
            one_letter_freq = Counter(one_letter_words)
            most_common = one_letter_freq.most_common(1)[0][0]
            
            advice.append("\n=== 单字母单词分析 ===")
            if most_common not in ['a', 'i']:
                advice.append(f"注意：英语中最常见的单字母单词是 'a' 和 'i'。当前解密文本中最常见的单字母单词是 '{most_common}'，可能需要调整对应密钥。")
        
        # 常见前缀和后缀分析
        prefixes = ['un', 're', 'in', 'im', 'dis', 'pre', 'post', 'anti', 'pro']
        suffixes = ['ing', 'ed', 'es', 's', 'er', 'est', 'ly', 'tion', 'ation', 'ment']
        
        prefix_matches = []
        suffix_matches = []
        
        for word in words:
            for prefix in prefixes:
                if word.startswith(prefix):
                    prefix_matches.append(prefix)
            for suffix in suffixes:
                if word.endswith(suffix):
                    suffix_matches.append(suffix)
        
        if prefix_matches:
            prefix_freq = Counter(prefix_matches)
            most_common_prefix = prefix_freq.most_common(1)[0][0]
            advice.append(f"\n=== 前缀分析 ===")
            advice.append(f"最常见的前缀是 '{most_common_prefix}'，可能需要检查相关字母的映射")
        
        if suffix_matches:
            suffix_freq = Counter(suffix_matches)
            most_common_suffix = suffix_freq.most_common(1)[0][0]
            advice.append(f"\n=== 后缀分析 ===")
            advice.append(f"最常见的后缀是 '{most_common_suffix}'，可能需要检查相关字母的映射")
        
        # 自动破译建议
        if not self.is_breaking:
            advice.append("\n=== 自动破译建议 ===")
            advice.append("考虑使用自动破译功能来尝试找到更优的密钥。")
            advice.append("自动破译会使用模拟退火算法，结合频率分析和词典匹配来寻找可能的密钥。")
        
        return "\n".join(advice)

    def start_breaking(self):
        """开始或停止自动破译"""
        if self.is_breaking:
            # 停止破译
            self.is_breaking = False
            self.break_btn.config(text="重复破译", style='TButton')
            if self.break_thread and self.break_thread.is_alive():
                self.break_thread.join(timeout=1.0)  # 等待线程结束，最多1秒
                if self.break_thread.is_alive():
                    print("警告: 自动破译线程未能及时停止")
        else:
            # 开始破译
            ciphertext = self.decrypt_text_area.get("1.0", tk.END).strip()
            if not ciphertext:
                messagebox.showwarning("警告", "请输入密文")
                return
            
            # 获取用户设置的迭代次数
            iterations = simpledialog.askinteger(
                "设置迭代次数", 
                "请输入最大迭代次数:", 
                parent=self.root,
                minvalue=1000, 
                maxvalue=1000000,  
                initialvalue=self.max_iterations
            )
            
            if iterations is not None:
                self.max_iterations = iterations
                self.is_breaking = True
                self.break_btn.config(text="停止破译", style='Stop.TButton')
                self.iterations = 0
                self.best_key = None
                self.best_match_count = 0
                self.last_updated_iterations = 0
                
                # 重置进度显示
                self.break_progress.config(text=f"迭代次数: 0")
                self.best_match.config(text=f"最佳匹配: 0")
                
                # 启动自动破译线程
                self.break_thread = threading.Thread(target=self.break_cipher, args=(ciphertext,))
                self.break_thread.daemon = True
                self.break_thread.start()

    def break_cipher(self, ciphertext):
        """使用模拟退火算法自动破译密码"""
        # 初始化密钥
        current_key = self.generate_initial_key()
        current_score = self.evaluate_key_dictionary(current_key, ciphertext)
        
        # 最佳密钥
        self.best_key = current_key.copy()
        self.best_match_count = current_score
        
        # 模拟退火参数
        temperature = 100.0
        cooling_rate = 0.999  # 减慢降温速率，增加探索时间
        
        # 记录连续未改进的迭代次数
        stagnation_count = 0
        max_stagnation = 10000  # 连续10000次迭代没有改进则停止
        
        # 迭代
        while temperature > 0.1 and self.iterations < self.max_iterations and self.is_breaking:
            # 生成新密钥
            new_key = self.swap_mapping(current_key.copy())
            new_score = self.evaluate_key_dictionary(new_key, ciphertext)
            
            # 计算接受概率
            prob = self.acceptance_probability(current_score, new_score, temperature)
            
            # 决定是否接受新解
            improved = False
            if prob > random.random():
                current_key = new_key
                current_score = new_score
                
                # 更新最佳解
                if current_score > self.best_match_count:
                    self.best_key = current_key.copy()
                    self.best_match_count = current_score
                    improved = True
                    stagnation_count = 0
                else:
                    stagnation_count += 1
            else:
                stagnation_count += 1
            
            # 增加迭代次数
            self.iterations += 1
            
            # 每1000次迭代更新一次界面，减少界面更新频率提高性能
            if self.iterations % 1000 == 0:
                self.root.after(0, self.update_break_progress)
            
            # 检查是否停滞
            if stagnation_count >= max_stagnation:
                print(f"破译停滞: 在 {max_stagnation} 次迭代中没有改进")
                break
            
            # 降低温度
            temperature *= cooling_rate
            
            # 小睡一下，避免CPU占用过高，但时间更短
            if self.iterations % 100 == 0:
                time.sleep(0.001)  # 每100次迭代才休眠，减少休眠次数
        
        # 迭代完成
        if self.is_breaking:
            self.is_breaking = False
            self.root.after(0, self.update_break_complete)

    def generate_initial_key(self):
        """基于当前固定的密钥对生成初始密钥"""
        letters = list('abcdefghijklmnopqrstuvwxyz')
        available_letters = [l for l in letters if l not in self.fixed_pairs.values()]
        random.shuffle(available_letters)
        
        key = {}
        available_index = 0
        
        for letter in letters:
            if letter in self.fixed_pairs:
                key[letter] = self.fixed_pairs[letter]
            else:
                if available_index < len(available_letters):
                    key[letter] = available_letters[available_index]
                    available_index += 1
        
        # 确保所有字母都有映射
        if len(key) < 26:
            remaining = [l for l in letters if l not in key.values()]
            for letter in letters:
                if letter not in key:
                    if remaining:
                        key[letter] = remaining.pop()
        
        return key

    def swap_mapping(self, key):
        """随机交换两个非固定的映射"""
        # 获取所有非固定的字母
        non_fixed = [k for k in key if k not in self.fixed_pairs]
        
        if len(non_fixed) < 2:
            return key  # 没有足够的非固定字母进行交换
        
        # 随机选择两个非固定的字母
        a, b = random.sample(non_fixed, 2)
        
        # 交换它们的映射
        key[a], key[b] = key[b], key[a]
        
        return key

    def evaluate_key_dictionary(self, key, ciphertext):
        """使用词典匹配评估密钥的质量"""
        # 解密文本
        reverse_key = {v: k for k, v in key.items()}
        decrypted_text = []
        for c in ciphertext:
            if c.isalpha():
                if c.isupper():
                    decrypted_text.append(reverse_key.get(c.lower(), '*').upper())
                else:
                    decrypted_text.append(reverse_key.get(c, '*'))
            else:
                decrypted_text.append(c)
        
        decrypted_text_str = "".join(decrypted_text)
        
        # 执行词典匹配
        words = re.findall(r'\b[a-zA-Z]+\b', decrypted_text_str.lower())
        if not words:
            return 0
        
        matched_words = []
        for word in words:
            if word in self.dictionary:
                matched_words.append(word)
        
        return len(matched_words)

    def evaluate_key_frequency(self, key, ciphertext):
        """使用频率分析评估密钥的质量"""
        # 解密文本
        reverse_key = {v: k for k, v in key.items()}
        decrypted_text = []
        for c in ciphertext:
            if c.isalpha():
                if c.isupper():
                    decrypted_text.append(reverse_key.get(c.lower(), '*').upper())
                else:
                    decrypted_text.append(reverse_key.get(c, '*'))
            else:
                decrypted_text.append(c)
        
        decrypted_text_str = "".join(decrypted_text)
        
        # 计算解密文本的字母频率
        freq = Counter(c.lower() for c in decrypted_text_str if c.isalpha())
        
        # 英语字母频率顺序
        english_freq_order = 'etaoinsrhdlucmfywgpbvkxqjz'
        
        # 计算解密文本的字母频率顺序
        decrypted_freq_order = ''.join([letter for letter, _ in freq.most_common()])
        
        # 计算评分：频率顺序匹配程度
        score = 0
        for i, letter in enumerate(decrypted_freq_order):
            if letter in english_freq_order:
                pos = english_freq_order.index(letter)
                # 位置越接近，得分越高
                score += 10 - abs(i - pos) if i < 10 else 0
        
        return score

    def acceptance_probability(self, current_score, new_score, temperature):
        """计算接受新解的概率"""
        if new_score > current_score:
            return 1.0
        return 1.0 * (1 - (current_score - new_score) / temperature)

    def update_break_progress(self):
        """更新自动破译进度显示"""
        if hasattr(self, 'break_progress') and self.break_progress.winfo_exists():
            self.break_progress.config(text=f"迭代次数: {self.iterations}")
        if hasattr(self, 'best_match') and self.best_match.winfo_exists():
            self.best_match.config(text=f"最佳匹配: {self.best_match_count}")
        
        # 每10000次迭代才更新解密结果，减少计算负担
        if self.iterations - self.last_updated_iterations >= 10000 and self.best_key:
            self.last_updated_iterations = self.iterations
            # 如果当前密钥是最佳密钥，更新解密结果
            if self.key == self.best_key:
                self.update_decrypt_results()

    def update_break_complete(self):
        """更新自动破译完成后的界面"""
        self.break_btn.config(text="重复破译", style='TButton')
        
        if self.best_key:
            # 使用最佳密钥
            self.key = self.best_key
            self.update_key_display()
            self.update_decrypt_results()
            
            messagebox.showinfo("破译完成", f"自动破译完成！\n迭代次数: {self.iterations}\n最佳匹配: {self.best_match_count}")
        else:
            messagebox.showinfo("破译取消", "自动破译已取消")

    def save_key(self):
        """保存当前密钥到文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".key",
            filetypes=[("密钥文件", "*.key"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(self.key, file)
                messagebox.showinfo("成功", f"密钥已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存密钥时出错: {str(e)}")

    def load_key(self):
        """从文件加载密钥"""
        file_path = filedialog.askopenfilename(filetypes=[("密钥文件", "*.key"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    loaded_key = json.load(file)
                
                # 验证加载的密钥
                if len(loaded_key) != 26:
                    messagebox.showerror("错误", "加载的密钥不完整")
                    return
                
                if len(set(loaded_key.values())) != 26:
                    messagebox.showerror("错误", "加载的密钥包含重复的映射")
                    return
                
                self.key = loaded_key
                self.update_key_display()
                
                if self.current_page == 'decrypt':
                    self.update_decrypt_results()
                
                messagebox.showinfo("成功", f"密钥已从 {file_path} 加载")
            except Exception as e:
                messagebox.showerror("错误", f"加载密钥时出错: {str(e)}")

    def save_encrypted_text(self):
        """保存加密文本到文件"""
        encrypted_text = self.ciphertext_area.get("1.0", tk.END).strip()
        if not encrypted_text:
            messagebox.showwarning("警告", "没有加密文本可保存")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(encrypted_text)
                messagebox.showinfo("成功", f"加密文本已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

    def save_decrypted_text(self):
        """保存解密文本到文件"""
        ciphertext = self.decrypt_text_area.get("1.0", tk.END).strip()
        if not ciphertext:
            messagebox.showwarning("警告", "没有解密文本可保存")
            return
        
        reverse_key = {v: k for k, v in self.key.items()}
        decrypted_text = []
        
        for c in ciphertext:
            if c.isalpha():
                if c.isupper():
                    decrypted_text.append(reverse_key.get(c.lower(), '*').upper())
                else:
                    decrypted_text.append(reverse_key.get(c, '*'))
            else:
                decrypted_text.append(c)
        
        decrypted_text_str = "".join(decrypted_text)
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(decrypted_text_str)
                messagebox.showinfo("成功", f"解密文本已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

    def clear_text(self, page_type):
        """清空文本区域"""
        if page_type == 'encrypt' and hasattr(self, 'plaintext_area'):
            self.plaintext_area.delete("1.0", tk.END)
            self.cached_plaintext = ""
            self.plaintext_has_example = True
            self.plaintext_area.insert(tk.END, "请在此输入明文...")
            self.plaintext_area.bind("<FocusIn>", self.on_plaintext_focus_in)
        elif page_type == 'decrypt' and hasattr(self, 'decrypt_text_area'):
            self.decrypt_text_area.delete("1.0", tk.END)
            self.cached_decrypt_text = ""
            self.decrypt_text_has_example = True
            self.decrypt_text_area.insert(tk.END, "请在此输入密文...")
            self.decrypt_text_area.bind("<FocusIn>", self.on_decrypt_text_focus_in)

    def load_text(self, page_type):
        """从文件加载文本"""
        file_path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                
                if page_type == 'encrypt' and hasattr(self, 'plaintext_area'):
                    self.plaintext_area.delete("1.0", tk.END)
                    self.plaintext_area.insert(tk.END, text)
                    self.cached_plaintext = text
                    self.plaintext_has_example = False
                elif page_type == 'decrypt' and hasattr(self, 'decrypt_text_area'):
                    self.decrypt_text_area.delete("1.0", tk.END)
                    self.decrypt_text_area.insert(tk.END, text)
                    self.cached_decrypt_text = text
                    self.decrypt_text_has_example = False
                
                messagebox.showinfo("成功", f"文本已从 {file_path} 加载")
            except Exception as e:
                messagebox.showerror("错误", f"加载文件时出错: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CipherTool(root)
    root.mainloop()