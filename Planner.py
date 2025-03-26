# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import Calendar
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import json
import os
import shutil
import csv

class Task:
    def __init__(self, title, due_date, category="Без категории", comment="", time_spent=0, importance=False, urgency=False):
        self.title = title
        self.due_date = due_date
        self.category = category
        self.completed = False
        self.comment = comment
        self.time_spent = time_spent  # Время в секундах
        self.importance = importance  # True = Важно, False = Не важно
        self.urgency = urgency  # True = Срочно, False = Не срочно

    def __str__(self):
        status = "✓" if self.completed else "✗"
        return f"{self.title} | {self.due_date} | {self.category} | {status}"

class Note:
    def __init__(self, text, date, category="Без категории"):
        self.text = text
        self.date = date
        self.category = category

    @property
    def title(self):
        return self.text.split("\n")[0].strip() if self.text else ""

    def __str__(self):
        return f"{self.title} | {self.date} | {self.category}"

class PlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Планировщик дел")
        self.root.minsize(700, 600)
        self.tasks = []
        self.notes = []
        self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
        self.free_time_entries = []
        self.current_task = None
        self.load_data()

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)

        # Поиск
        tk.Label(root, text="Поиск:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.search_entry = tk.Entry(root)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(root, text="Найти", command=self.search).grid(row=0, column=2, padx=5, pady=5)
        tk.Button(root, text="Показать всё", command=self.reset_search).grid(row=0, column=3, padx=5, pady=5)

        # Таблица задач
        self.task_tree = ttk.Treeview(root, columns=(
        "Title", "Due Date", "Category", "Status", "Comment", "Time", "Priority"),
                                      show="headings", height=10)
        self.task_tree.heading("Title", text="Задача")
        self.task_tree.heading("Due Date", text="Срок")
        self.task_tree.heading("Category", text="Категория")
        self.task_tree.heading("Status", text="Статус")
        self.task_tree.heading("Comment", text="Комментарий")
        self.task_tree.heading("Time", text="Время")
        self.task_tree.heading("Priority", text="Приоритет")  # Новая колонка
        self.task_tree.column("Title", width=250, stretch=True)
        self.task_tree.column("Due Date", width=150, stretch=True)
        self.task_tree.column("Category", width=120, stretch=True)
        self.task_tree.column("Status", width=80, stretch=True)
        self.task_tree.column("Comment", width=50, stretch=True)
        self.task_tree.column("Time", width=100, stretch=True)
        self.task_tree.column("Priority", width=80, anchor="center")  # Новая колонка
        self.task_tree.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.task_tree.tag_configure("overdue", foreground="red")
        self.task_tree.bind("<Double-1>", self.on_task_double_click)

        # Кнопки для задач
        tk.Button(root, text="Добавить задачу", command=self.add_task_window).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(root, text="Отметить выполненной", command=self.complete_task).grid(row=2, column=1, padx=5, pady=5)
        tk.Button(root, text="Удалить задачу", command=self.delete_task).grid(row=2, column=2, padx=5, pady=5)
        tk.Button(root, text="Комментарий", command=self.edit_task_comment).grid(row=2, column=3, padx=5, pady=5)

        # Таймер Помидоро
        tk.Button(root, text="Запустить таймер", command=self.start_pomodoro).grid(row=3, column=0, padx=5, pady=5)
        tk.Button(root, text="Статистика таймера", command=self.show_pomodoro_stats).grid(row=3, column=1, padx=5,
                                                                                          pady=5)

        self.timer_running = False
        self.timer_paused = False
        self.pomodoro_cycles = 0
        self.work_seconds = 0
        self.rest_seconds = 0
        self.long_break_seconds = 15 * 60
        self.original_work_seconds = 25 * 60
        self.original_rest_seconds = 5 * 60
        self.is_work_phase = True
        self.work_time_spent = 0
        self.total_work_time = 0

        # Настройка напоминаний
        tk.Label(root, text="Напоминание за:").grid(row=3, column=2, padx=5, pady=5, sticky="e")
        self.reminder_var = tk.StringVar(value="10")
        tk.OptionMenu(root, self.reminder_var, "5", "10", "30", "60").grid(row=3, column=3, padx=5, pady=5, sticky="w")

        # Заметки
        tk.Button(root, text="Добавить заметку", command=self.open_note_window).grid(row=4, column=0, padx=5, pady=5)
        tk.Button(root, text="Редактировать заметку", command=self.edit_note).grid(row=4, column=1, padx=5, pady=5)
        tk.Button(root, text="Удалить заметку", command=self.delete_note).grid(row=4, column=2, padx=5, pady=5)
        tk.Button(root, text="Восстановить из резерва", command=self.restore_from_backup).grid(row=5, column=0, padx=5,
                                                                                               pady=5)
        tk.Button(root, text="Экспорт в CSV", command=self.export_to_csv).grid(row=5, column=1, padx=5, pady=5)

        self.note_tree = ttk.Treeview(root, columns=("Title", "Date", "Category"), show="headings", height=5)
        self.note_tree.heading("Title", text="Заголовок заметки")
        self.note_tree.heading("Date", text="Дата")
        self.note_tree.heading("Category", text="Категория")
        self.note_tree.column("Title", width=450, stretch=True)
        self.note_tree.column("Date", width=150, stretch=True)
        self.note_tree.column("Category", width=150, stretch=True)
        self.note_tree.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.note_tree.bind("<Double-1>", self.on_note_double_click)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_task_table()
        self.update_note_table()
        self.check_reminders()

    def set_today(self):
        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.due_date_var.set(today)

    def open_calendar(self):
        top = tk.Toplevel(self.root)
        top.title("Выберите дату")
        cal = Calendar(top, selectmode="day", date_pattern="yyyy-mm-dd")
        cal.pack(padx=10, pady=10)

        def set_date():
            selected_date = cal.get_date() + " 00:00"
            self.due_date_var.set(selected_date)
            top.destroy()

        tk.Button(top, text="Подтвердить", command=set_date).pack(pady=5)

    def complete_task(self):
        try:
            selected_item = self.task_tree.selection()[0]
            index = self.task_tree.index(selected_item)
            self.tasks[index].completed = True
            self.update_task_table()
        except IndexError:
            messagebox.showwarning("Ошибка", "Выберите задачу!")

    def delete_task(self):
        try:
            selected_item = self.task_tree.selection()[0]
            index = self.task_tree.index(selected_item)
            self.tasks.pop(index)
            self.update_task_table()
        except IndexError:
            messagebox.showwarning("Ошибка", "Выберите задачу!")

    def edit_task(self):
        try:
            selected_item = self.task_tree.selection()[0]
            index = self.task_tree.index(selected_item)
            current_task = self.tasks[index]

            top = tk.Toplevel(self.root)
            top.title("Редактировать задачу")
            top.geometry("500x350")  # Оптимизированный размер окна

            # Основной фрейм с минимальными отступами
            main_frame = tk.Frame(top, padx=10, pady=10)
            main_frame.pack(expand=True, fill="both")

            # Название задачи
            tk.Label(main_frame, text="Название задачи:").grid(row=0, column=0, sticky="w", pady=5)
            title_entry = tk.Entry(main_frame, width=50)
            title_entry.insert(0, current_task.title)
            title_entry.grid(row=0, column=1, pady=5, sticky="w")

            # Срок выполнения
            tk.Label(main_frame, text="Срок выполнения:").grid(row=1, column=0, sticky="w", pady=5)
            due_date_entry = tk.Entry(main_frame, width=50)
            due_date_entry.insert(0, current_task.due_date)
            due_date_entry.grid(row=1, column=1, pady=5, sticky="w")

            # Категория и чекбоксы в одной строке
            tk.Label(main_frame, text="Категория:").grid(row=2, column=0, sticky="w", pady=5)
            category_frame = tk.Frame(main_frame)
            category_frame.grid(row=2, column=1, pady=5, sticky="w")

            category_var = tk.StringVar(value=current_task.category)
            category_menu = tk.OptionMenu(category_frame, category_var, *self.categories)
            category_menu.pack(side="left", padx=(0, 10))

            importance_var = tk.BooleanVar(
                value=current_task.importance if hasattr(current_task, 'importance') else False)
            urgency_var = tk.BooleanVar(value=current_task.urgency if hasattr(current_task, 'urgency') else False)
            tk.Checkbutton(category_frame, text="Важно", variable=importance_var).pack(side="left", padx=5)
            tk.Checkbutton(category_frame, text="Срочно", variable=urgency_var).pack(side="left", padx=5)

            # Поле комментариев без метки, с подсказкой
            comment_text = tk.Text(main_frame, wrap="word", height=8, width=60)
            if current_task.comment:
                comment_text.insert("1.0", current_task.comment)
            else:
                comment_text.insert("1.0", "комментарий")
                comment_text.config(fg="grey")  # Серый цвет для подсказки

                def clear_placeholder(event):
                    if comment_text.get("1.0", tk.END).strip() == "комментарий":
                        comment_text.delete("1.0", tk.END)
                        comment_text.config(fg="black")

                def restore_placeholder(event):
                    if not comment_text.get("1.0", tk.END).strip():
                        comment_text.insert("1.0", "комментарий")
                        comment_text.config(fg="grey")

                comment_text.bind("<FocusIn>", clear_placeholder)
                comment_text.bind("<FocusOut>", restore_placeholder)
            comment_text.grid(row=3, column=0, columnspan=2, pady=10, sticky="we")

            def save_edited_task():
                new_title = title_entry.get().strip()
                new_due_date = due_date_entry.get().strip()
                new_category = category_var.get()
                new_comment = comment_text.get("1.0", tk.END).strip()
                new_importance = importance_var.get()
                new_urgency = urgency_var.get()

                if not new_title:
                    messagebox.showwarning("Ошибка", "Введите название задачи!")
                    return
                try:
                    datetime.strptime(new_due_date, "%Y-%m-%d %H:%M")
                    current_task.title = new_title
                    current_task.due_date = new_due_date
                    current_task.category = new_category
                    current_task.comment = new_comment if new_comment != "комментарий" else ""  # Убираем подсказку
                    if hasattr(current_task, 'importance'):
                        current_task.importance = new_importance
                    if hasattr(current_task, 'urgency'):
                        current_task.urgency = new_urgency
                    self.update_task_table()
                    self.save_data()  # Сохранение данных
                    top.destroy()
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверный формат даты! Используйте YYYY-MM-DD HH:MM")

            # Кнопка сохранения
            tk.Button(main_frame, text="Сохранить", command=save_edited_task).grid(row=4, column=0, columnspan=2,
                                                                                   pady=10)

        except IndexError:
            messagebox.showwarning("Ошибка", "Выберите задачу!")

    def on_task_double_click(self, event):
        self.edit_task()

    def open_note_window(self):
        top = tk.Toplevel(self.root)
        top.title("Новая заметка")
        top.geometry("600x450")

        tk.Label(top, text="Текст заметки (первая строка — заголовок):").pack(pady=5)
        note_text = tk.Text(top, wrap="word", height=10)
        note_text.pack(pady=5, padx=10, expand=True, fill="both")

        tk.Label(top, text="Категория:").pack(pady=5)
        category_var = tk.StringVar(value="Без категории")
        tk.OptionMenu(top, category_var, *self.categories).pack(pady=5)

        def save_note():
            text = note_text.get("1.0", tk.END).strip()
            category = category_var.get()
            if not text:
                messagebox.showwarning("Ошибка", "Введите текст заметки!")
                return
            date = datetime.now().strftime("%Y-%m-%d %H:%M")
            note = Note(text, date, category)
            self.notes.append(note)
            self.update_note_table()
            top.destroy()

        tk.Button(top, text="Сохранить", command=save_note).pack(pady=5)

    def edit_note(self):
        try:
            selected_item = self.note_tree.selection()[0]
            index = self.note_tree.index(selected_item)
            current_note = self.notes[index]

            top = tk.Toplevel(self.root)
            top.title("Редактировать заметку")
            top.geometry("600x450")

            tk.Label(top, text="Текст заметки (первая строка — заголовок):").pack(pady=5)
            note_text = tk.Text(top, wrap="word", height=10)
            note_text.insert("1.0", current_note.text)
            note_text.pack(pady=5, padx=10, expand=True, fill="both")

            tk.Label(top, text="Категория:").pack(pady=5)
            category_var = tk.StringVar(value=current_note.category)
            tk.OptionMenu(top, category_var, *self.categories).pack(pady=5)

            def save_edited_note():
                text = note_text.get("1.0", tk.END).strip()
                category = category_var.get()
                if not text:
                    messagebox.showwarning("Ошибка", "Введите текст заметки!")
                    return
                current_note.text = text
                current_note.category = category
                self.update_note_table()
                top.destroy()

            tk.Button(top, text="Сохранить", command=save_edited_note).pack(pady=5)
        except IndexError:
            messagebox.showwarning("Ошибка", "Выберите заметку!")

    def on_note_double_click(self, event):
        self.edit_note()

    def delete_note(self):
        try:
            selected_item = self.note_tree.selection()[0]
            index = self.note_tree.index(selected_item)
            self.notes.pop(index)
            self.update_note_table()
        except IndexError:
            messagebox.showwarning("Ошибка", "Выберите заметку!")

    def update_task_table(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        for task in self.tasks:
            status = "✓" if task.completed else "✗"
            time_str = f"{task.time_spent // 60} мин {task.time_spent % 60} сек" if task.time_spent else ""
            comment_symbol = "✎" if task.comment else ""
            if task.importance and task.urgency:
                priority = "1"  # Важно и Срочно
                tag = "urgent_important"
            elif task.importance and not task.urgency:
                priority = "2"  # Важно, Не срочно
                tag = "important"
            elif not task.importance and task.urgency:
                priority = "3"  # Не важно, Срочно
                tag = "urgent"
            else:
                priority = "4"  # Не важно, Не срочно
                tag = "not_important"

            values = (task.title, task.due_date, task.category, status, comment_symbol, time_str, priority)
            item = self.task_tree.insert("", "end", values=values, tags=(tag,))
            if not task.completed and datetime.strptime(task.due_date, "%Y-%m-%d %H:%M") < datetime.now():
                self.task_tree.item(item, tags=(tag, "overdue"))

        # Мягкие цвета
        self.task_tree.tag_configure("urgent_important", background="#ffcccc")  # Квадрант 1: Мягкий красный
        self.task_tree.tag_configure("important", background="#ccffcc")  # Квадрант 2: Мягкий зелёный
        self.task_tree.tag_configure("urgent", background="#ffcc99")  # Квадрант 3: Мягкий оранжевый
        self.task_tree.tag_configure("not_important", background="#cce5ff")  # Квадрант 4: Мягкий голубой
        self.task_tree.tag_configure("overdue", foreground="red")

    def update_note_table(self):
        self.note_tree.delete(*self.note_tree.get_children())
        for note in self.notes:
            self.note_tree.insert("", "end", values=(note.title, note.date, note.category))

    def search(self):
        query = self.search_entry.get().lower()
        self.task_tree.delete(*self.task_tree.get_children())
        self.note_tree.delete(*self.note_tree.get_children())
        for task in self.tasks:
            if query in task.title.lower() or query in task.category.lower():
                status = "✓" if task.completed else "✗"
                self.task_tree.insert("", "end", values=(task.title, task.due_date, task.category, status))
        for note in self.notes:
            if query in note.title.lower() or query in note.text.lower() or query in note.category.lower():
                self.note_tree.insert("", "end", values=(note.title, note.date, note.category))

    def reset_search(self):
        self.search_entry.delete(0, tk.END)
        self.update_task_table()
        self.update_note_table()

    def check_reminders(self):
        now = datetime.now()
        reminder_minutes = int(self.reminder_var.get())
        for task in self.tasks:
            if not task.completed:
                due = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
                if now <= due <= now + timedelta(minutes=reminder_minutes):
                    messagebox.showinfo("Напоминание", f"Срок задачи '{task.title}' через {reminder_minutes} минут!")
        self.root.after(60000, self.check_reminders)

    def start_pomodoro(self):
        try:
            selected_item = self.task_tree.selection()[0]
            index = self.task_tree.index(selected_item)
            self.current_task = self.tasks[index]
            task_name = self.current_task.title
        except IndexError:
            self.current_task = None
            task_name = "Без задачи"

        settings_win = tk.Toplevel(self.root)
        settings_win.title(f"Таймер Помидоро для '{task_name}'")
        settings_win.geometry("300x300")

        tk.Label(settings_win, text="Время работы (мин):").pack(pady=5)
        work_entry = tk.Entry(settings_win)
        work_entry.insert(0, "25")
        work_entry.pack(pady=5)

        tk.Label(settings_win, text="Время отдыха (мин):").pack(pady=5)
        rest_entry = tk.Entry(settings_win)
        rest_entry.insert(0, "5")
        rest_entry.pack(pady=5)

        tk.Label(settings_win, text="Длинный перерыв (мин):").pack(pady=5)
        long_break_entry = tk.Entry(settings_win)
        long_break_entry.insert(0, "15")
        long_break_entry.pack(pady=5)

        def run_timer():
            try:
                work_minutes = int(work_entry.get())
                rest_minutes = int(rest_entry.get())
                long_break_minutes = int(long_break_entry.get())
                if work_minutes <= 0 or rest_minutes <= 0 or long_break_minutes <= 0:
                    raise ValueError
                self.work_seconds = work_minutes * 60
                self.rest_seconds = rest_minutes * 60
                self.long_break_seconds = long_break_minutes * 60
                self.original_work_seconds = work_minutes * 60
                self.original_rest_seconds = rest_minutes * 60
                self.is_work_phase = True
                self.timer_running = True
                self.timer_paused = False
                self.pomodoro_cycles = 0
                self.work_time_spent = 0
                self.total_work_time = 0  # Сбрасываем общее время
                settings_win.destroy()

                timer_win = tk.Toplevel(self.root)
                timer_win.title(f"Таймер Помидоро: {task_name}")
                timer_win.geometry("400x200")
                timer_win.protocol("WM_DELETE_WINDOW", self.stop_timer)

                timer_label = tk.Label(timer_win, text="Таймер: Настраивается...")
                timer_label.pack(pady=10)

                progress_bar = ttk.Progressbar(timer_win, length=300, mode="determinate")
                progress_bar.pack(pady=10)

                pause_btn = tk.Button(timer_win, text="Пауза", command=self.toggle_pause)
                pause_btn.pack(side=tk.LEFT, padx=5, pady=5)

                stop_btn = tk.Button(timer_win, text="Стоп", command=lambda: self.stop_timer(timer_win))
                stop_btn.pack(side=tk.LEFT, padx=5, pady=5)

                end_btn = tk.Button(timer_win, text="Окончить работу", command=lambda: self.end_work(timer_win))
                end_btn.pack(side=tk.LEFT, padx=5, pady=5)

                self.run_pomodoro_timer(timer_win, timer_label, progress_bar)
            except ValueError:
                messagebox.showerror("Ошибка", "Введите положительные числа!")

        tk.Button(settings_win, text="Старт", command=run_timer).pack(pady=10)
        tk.Button(settings_win, text="Отмена", command=settings_win.destroy).pack(pady=5)

    def run_pomodoro_timer(self, timer_win, timer_label, progress_bar):
        pause_btn = timer_win.children["!button"]  # Кнопка "Пауза"

        def update_timer():
            if not self.timer_running:
                if timer_win.winfo_exists():
                    progress_bar["value"] = 0
                    timer_win.destroy()
                return
            if self.timer_paused:
                timer_label.config(text=f"Пауза: {'Работа' if self.is_work_phase else 'Отдых'}")
                pause_btn.config(text="Продолжить")
                self.root.after(1000, update_timer)
                return
            else:
                pause_btn.config(text="Пауза")

            task_name = self.current_task.title if self.current_task else "Без задачи"
            if self.is_work_phase and self.work_seconds > 0:
                timer_label.config(
                    text=f"Работа над '{task_name}': {self.work_seconds // 60}:{self.work_seconds % 60:02d} (Цикл {self.pomodoro_cycles + 1})")
                progress = (self.original_work_seconds - self.work_seconds) / self.original_work_seconds * 100
                progress_bar["value"] = progress
                self.work_seconds -= 1
                self.work_time_spent += 1
                self.total_work_time += 1  # Накапливаем общее время
                self.root.after(1000, update_timer)
            elif self.is_work_phase and self.work_seconds <= 0:
                if self.current_task:
                    self.current_task.time_spent += self.work_time_spent
                    self.update_task_table()
                self.work_time_spent = 0
                self.is_work_phase = False
                self.pomodoro_cycles += 1
                self.rest_seconds = self.original_rest_seconds if self.pomodoro_cycles < 4 else self.long_break_seconds
                self.root.after(1000, update_timer)
            elif not self.is_work_phase and self.rest_seconds > 0:
                timer_label.config(
                    text=f"Отдых: {self.rest_seconds // 60}:{self.rest_seconds % 60:02d} (Цикл {self.pomodoro_cycles})")
                progress = (
                                       self.original_rest_seconds - self.rest_seconds) / self.original_rest_seconds * 100 if self.pomodoro_cycles < 4 else (
                                                                                                                                                                       self.long_break_seconds - self.rest_seconds) / self.long_break_seconds * 100
                progress_bar["value"] = progress
                self.rest_seconds -= 1
                self.root.after(1000, update_timer)
            else:
                self.work_seconds = self.original_work_seconds
                self.is_work_phase = True
                self.pomodoro_cycles = 0 if self.pomodoro_cycles >= 4 else self.pomodoro_cycles
                self.root.after(1000, update_timer)

        update_timer()

    def log_free_time(self, time_spent):
        top = tk.Toplevel(self.root)
        top.title("Лог времени")
        top.geometry("400x200")

        tk.Label(top, text=f"Потрачено {time_spent // 60} мин {time_spent % 60} сек").pack(pady=5)
        tk.Label(top, text="На что было потрачено время?").pack(pady=5)
        desc_entry = tk.Entry(top, width=40)
        desc_entry.pack(pady=5)

        def save_log():
            desc = desc_entry.get().strip()
            if not desc:
                messagebox.showwarning("Ошибка", "Введите описание!")
                return
            entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "description": desc,
                "time_spent": time_spent
            }
            self.free_time_entries.append(entry)
            top.destroy()

        tk.Button(top, text="Сохранить", command=save_log).pack(pady=10)

    def end_work(self, timer_win):
        if self.current_task:
            self.current_task.time_spent += self.work_time_spent
            self.update_task_table()
        else:
            if self.total_work_time > 0:  # Учитываем всё время работы
                self.log_free_time(self.total_work_time)
        self.timer_running = False
        timer_win.destroy()

    def show_pomodoro_stats(self):
        top = tk.Toplevel(self.root)
        top.title("Статистика таймера")
        top.geometry("600x400")

        stats_text = tk.Text(top, wrap="word", height=20)
        stats_text.pack(pady=5, padx=10, expand=True, fill="both")

        stats_text.insert("end", "Время по задачам:\n")
        for task in self.tasks:
            if task.time_spent > 0:
                minutes = task.time_spent // 60
                seconds = task.time_spent % 60
                stats_text.insert("end", f"- {task.title}: {minutes} мин {seconds} сек\n")

        stats_text.insert("end", "\nРабота вне плана:\n")
        for entry in self.free_time_entries:
            minutes = entry["time_spent"] // 60
            seconds = entry["time_spent"] % 60
            stats_text.insert("end", f"- {entry['date']} | {entry['description']}: {minutes} мин {seconds} сек\n")

        stats_text.config(state="disabled")  # Только чтение

    def toggle_pause(self):
        if self.timer_running:
            self.timer_paused = not self.timer_paused

    def stop_timer(self, timer_win=None):
        self.timer_running = False
        if timer_win:
            timer_win.destroy()

    def save_data(self):
        data = {
            "tasks": [{"title": task.title, "due_date": task.due_date, "category": task.category,
                       "comment": task.comment, "time_spent": task.time_spent, "completed": task.completed,
                       "importance": task.importance, "urgency": task.urgency} for task in self.tasks],
            "notes": [{"text": note.text, "date": note.date, "category": note.category} for note in self.notes],
            "categories": self.categories,
            "free_time_entries": self.free_time_entries
        }
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        if not os.path.exists("tasks_backup.json") or os.path.getmtime("tasks.json") > os.path.getmtime(
                "tasks_backup.json"):
            with open("tasks_backup.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    def load_data(self):
        try:
            with open("tasks.json", "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self.tasks = []
                    self.notes = []
                    self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
                    self.free_time_entries = []
                else:
                    data = json.loads(content)
                    self.tasks = [Task(t["title"], t["due_date"], t.get("category", "Без категории"),
                                       t.get("comment", ""), t.get("time_spent", 0),
                                       t.get("importance", False), t.get("urgency", False))
                                  for t in data.get("tasks", [])]
                    for i, task in enumerate(self.tasks):
                        task.completed = data["tasks"][i]["completed"]
                    self.notes = [Note(n["text"], n["date"], n.get("category", "Без категории"))
                                  for n in data.get("notes", [])]
                    self.categories = data.get("categories", ["Без категории", "Работа", "Личное", "Срочное"])
                    self.free_time_entries = data.get("free_time_entries", [])
        except FileNotFoundError:
            self.tasks = []
            self.notes = []
            self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
            self.free_time_entries = []
        except json.JSONDecodeError:
            self.tasks = []
            self.notes = []
            self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
            self.free_time_entries = []

    def save_data(self):
        data = {
            "tasks": [{"title": task.title, "due_date": task.due_date, "category": task.category,
                       "comment": task.comment, "time_spent": task.time_spent, "completed": task.completed,
                       "importance": task.importance, "urgency": task.urgency} for task in self.tasks],
            "notes": [{"text": note.text, "date": note.date, "category": note.category} for note in self.notes],
            "categories": self.categories,
            "free_time_entries": self.free_time_entries
        }
        with open("tasks.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        if not os.path.exists("tasks_backup.json") or os.path.getmtime("tasks.json") > os.path.getmtime(
                "tasks_backup.json"):
            with open("tasks_backup.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    def load_data(self):
        try:
            with open("tasks.json", "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    self.tasks = []
                    self.notes = []
                    self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
                    self.free_time_entries = []
                else:
                    data = json.loads(content)
                    self.tasks = [Task(t["title"], t["due_date"], t.get("category", "Без категории"),
                                       t.get("comment", ""), t.get("time_spent", 0),
                                       t.get("importance", False), t.get("urgency", False))
                                  for t in data.get("tasks", [])]
                    for i, task in enumerate(self.tasks):
                        task.completed = data["tasks"][i]["completed"]
                    self.notes = [Note(n["text"], n["date"], n.get("category", "Без категории"))
                                  for n in data.get("notes", [])]
                    self.categories = data.get("categories", ["Без категории", "Работа", "Личное", "Срочное"])
                    self.free_time_entries = data.get("free_time_entries", [])
        except FileNotFoundError:
            self.tasks = []
            self.notes = []
            self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
            self.free_time_entries = []
        except json.JSONDecodeError:
            self.tasks = []
            self.notes = []
            self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
            self.free_time_entries = []

    def restore_from_backup(self):
        if os.path.exists("tasks_backup.json"):
            try:
                with open("tasks_backup.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.tasks = [Task(t["title"], t["due_date"], t.get("category", "Без категории")) for t in data.get("tasks", [])]
                        for i, task in enumerate(self.tasks):
                            task.completed = data["tasks"][i]["completed"]
                        self.notes = [Note(n["text"], n["date"], n.get("category", "Без категории")) for n in data.get("notes", [])]
                        self.update_task_table()
                        self.update_note_table()
                        messagebox.showinfo("Успех", "Данные восстановлены из резервной копии.")
                        self.save_data()
                    else:
                        messagebox.showerror("Ошибка", "Резервная копия имеет неверный формат.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось восстановить данные: {e}")
        else:
            messagebox.showwarning("Внимание", "Резервная копия не найдена.")

    def export_to_csv(self):
        try:
            with open("planner_export.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Заголовки для задач
                writer.writerow(["Тип", "Название", "Срок/Дата", "Категория", "Статус"])
                # Экспорт задач
                for task in self.tasks:
                    status = "Выполнено" if task.completed else "Не выполнено"
                    writer.writerow(["Задача", task.title, task.due_date, task.category, status])
                # Экспорт заметок
                for note in self.notes:
                    writer.writerow(["Заметка", note.title, note.date, note.category, ""])
            messagebox.showinfo("Успех", "Данные экспортированы в planner_export.csv")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {e}")

    def on_closing(self):
        self.save_data()
        self.root.destroy()

    def edit_task_comment(self):
        try:
            selected_item = self.task_tree.selection()[0]
            index = self.task_tree.index(selected_item)
            current_task = self.tasks[index]

            top = tk.Toplevel(self.root)
            top.title(f"Комментарий к задаче '{current_task.title}'")
            top.geometry("600x450")

            tk.Label(top, text="Комментарий к задаче:").pack(pady=5)
            comment_text = tk.Text(top, wrap="word", height=10)
            comment_text.insert("1.0", current_task.comment)
            comment_text.pack(pady=5, padx=10, expand=True, fill="both")

            def save_comment():
                comment = comment_text.get("1.0", tk.END).strip()
                current_task.comment = comment
                top.destroy()

            tk.Button(top, text="Сохранить", command=save_comment).pack(pady=5)
        except IndexError:
            messagebox.showwarning("Ошибка", "Выберите задачу!")

    def add_category(self):
        top = tk.Toplevel(self.root)
        top.title("Новая категория")
        top.geometry("300x150")

        tk.Label(top, text="Введите название категории:").pack(pady=5)
        category_entry = tk.Entry(top, width=30)
        category_entry.pack(pady=5)

        def save_category():
            new_category = category_entry.get().strip()
            if not new_category:
                messagebox.showwarning("Ошибка", "Введите название категории!")
                return
            if new_category in self.categories:
                messagebox.showwarning("Ошибка", "Такая категория уже существует!")
                return
            self.categories.append(new_category)
            self.category_menu["menu"].delete(0, "end")  # Обновляем меню
            for category in self.categories:
                self.category_menu["menu"].add_command(label=category,
                                                       command=lambda c=category: self.category_var.set(c))
            self.category_var.set(new_category)
            top.destroy()

        tk.Button(top, text="Сохранить", command=save_category).pack(pady=10)

    def add_task_window(self):
        top = tk.Toplevel(self.root)
        top.title("Добавить задачу")
        top.geometry("420x320")  # Оптимизируем размер окна

        # Используем grid для аккуратного размещения элементов
        tk.Label(top, text="Название задачи:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        title_entry = tk.Entry(top, width=40)
        title_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(top, text="Дата выполнения:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        due_date_entry = DateEntry(top, width=20, date_pattern="yyyy-mm-dd")
        due_date_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(top, text="Категория:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        category_var = tk.StringVar(value="Без категории")
        category_menu = tk.OptionMenu(top, category_var, *self.categories)
        category_menu.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        tk.Label(top, text="Комментарий:").grid(row=3, column=0, sticky="nw", padx=10, pady=5)
        comment_text = tk.Text(top, height=4, width=30)
        comment_text.grid(row=3, column=1, padx=10, pady=5)

        # Чекбоксы размещаем в одной строке
        importance_var = tk.BooleanVar(value=False)
        urgency_var = tk.BooleanVar(value=False)
        checkbox_frame = tk.Frame(top)
        checkbox_frame.grid(row=4, column=1, pady=10, sticky="w")

        tk.Checkbutton(checkbox_frame, text="Важно", variable=importance_var).pack(side="left", padx=5)
        tk.Checkbutton(checkbox_frame, text="Срочно", variable=urgency_var).pack(side="left", padx=5)

        def save_task():
            title = title_entry.get().strip()
            due_date = due_date_entry.get()
            category = category_var.get()
            comment = comment_text.get("1.0", "end-1c").strip()
            importance = importance_var.get()
            urgency = urgency_var.get()

            if not title or not due_date:
                messagebox.showwarning("Ошибка", "Заполните название и дату!")
                return

            try:
                date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                due_date_formatted = date_obj.replace(hour=23, minute=59).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showwarning("Ошибка", "Неверный формат даты! Используйте ГГГГ-ММ-ДД")
                return

            new_task = Task(title, due_date_formatted, category, comment, 0, importance, urgency)
            self.tasks.append(new_task)
            self.update_task_table()
            self.save_data()
            top.destroy()

        # Кнопка сохранения
        tk.Button(top, text="Сохранить", command=save_task).grid(row=5, column=0, columnspan=2, pady=10)


# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = PlannerApp(root)
    root.mainloop()