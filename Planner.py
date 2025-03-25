# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import Calendar
from datetime import datetime, timedelta
import json
import os
import shutil
import csv

class Task:
    def __init__(self, title, due_date, category="Без категории", comment="", time_spent=0):
        self.title = title
        self.due_date = due_date
        self.category = category
        self.completed = False
        self.comment = comment
        self.time_spent = time_spent  # Время в секундах

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
        self.root.grid_columnconfigure(3, weight=1)  # Добавляем растяжение для третьего столбца

        # Поиск
        tk.Label(root, text="Поиск:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.search_entry = tk.Entry(root)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(root, text="Найти", command=self.search).grid(row=0, column=2, padx=5, pady=5)
        tk.Button(root, text="Показать всё", command=self.reset_search).grid(row=0, column=3, padx=5, pady=5)

        # Поля ввода для задач
        tk.Label(root, text="Название задачи:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.title_entry = tk.Entry(root)
        self.title_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        tk.Button(root, text="Сегодня", command=self.set_today).grid(row=2, column=0, padx=5, pady=5)
        tk.Button(root, text="Выбрать дату", command=self.open_calendar).grid(row=2, column=1, padx=5, pady=5)

        self.due_date_var = tk.StringVar(value="Дата не выбрана")
        tk.Label(root, textvariable=self.due_date_var).grid(row=3, column=0, columnspan=2, pady=5)

        tk.Label(root, text="Категория:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.category_var = tk.StringVar(value="Без категории")
        self.category_menu = tk.OptionMenu(root, self.category_var, *self.categories)
        self.category_menu.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(root, text="Добавить категорию", command=self.add_category).grid(row=4, column=2, padx=5, pady=5)

        tk.Button(root, text="Добавить задачу", command=self.add_task).grid(row=5, column=0, columnspan=2, pady=5)

        tk.Button(root, text="Отметить выполненной", command=self.complete_task).grid(row=6, column=0, padx=5, pady=5)
        tk.Button(root, text="Удалить задачу", command=self.delete_task).grid(row=6, column=1, padx=5, pady=5)
        tk.Button(root, text="Комментарий", command=self.edit_task_comment).grid(row=6, column=2, padx=5, pady=5)

        self.task_tree = ttk.Treeview(root, columns=("Title", "Due Date", "Category", "Status", "Comment", "Time"),
                                      show="headings", height=10)
        self.task_tree.heading("Title", text="Задача")
        self.task_tree.heading("Due Date", text="Срок")
        self.task_tree.heading("Category", text="Категория")
        self.task_tree.heading("Status", text="Статус")
        self.task_tree.heading("Comment", text="Комментарий")
        self.task_tree.heading("Time", text="Время")
        self.task_tree.column("Title", width=300, stretch=True)  # Уменьшаем, чтобы уместить новую колонку
        self.task_tree.column("Due Date", width=200, stretch=True)
        self.task_tree.column("Category", width=150, stretch=True)
        self.task_tree.column("Status", width=80, stretch=True)
        self.task_tree.column("Comment", width=50, stretch=True)
        self.task_tree.column("Time", width=100, stretch=True)  # Новая колонка
        self.task_tree.grid(row=7, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.task_tree.tag_configure("overdue", foreground="red")
        self.task_tree.bind("<Double-1>", self.on_task_double_click)
        self.update_task_table()

        # Таймер Помидоро
        tk.Button(root, text="Запустить таймер", command=self.start_pomodoro).grid(row=8, column=0, padx=5, pady=5)
        tk.Button(root, text="Статистика таймера", command=self.show_pomodoro_stats).grid(row=8, column=1, padx=5,
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
        self.work_time_spent = 0  # Добавляем атрибут класса
        self.total_work_time = 0  # Добавляем для накопления общего времени

        # Настройка напоминаний
        tk.Label(root, text="Напоминание за:").grid(row=8, column=2, padx=5, pady=5, sticky="e")
        self.reminder_var = tk.StringVar(value="10")
        tk.OptionMenu(root, self.reminder_var, "5", "10", "30", "60").grid(row=8, column=3, padx=5, pady=5, sticky="w")

        tk.Button(root, text="Добавить заметку", command=self.open_note_window).grid(row=11, column=0, padx=5, pady=5)
        tk.Button(root, text="Редактировать заметку", command=self.edit_note).grid(row=11, column=1, padx=5, pady=5)
        tk.Button(root, text="Удалить заметку", command=self.delete_note).grid(row=12, column=0, padx=5, pady=5)
        tk.Button(root, text="Восстановить из резерва", command=self.restore_from_backup).grid(row=12, column=1, padx=5, pady=5)
        tk.Button(root, text="Экспорт в CSV", command=self.export_to_csv).grid(row=12, column=2, padx=5, pady=5)

        self.note_tree = ttk.Treeview(root, columns=("Title", "Date", "Category"), show="headings", height=5)
        self.note_tree.heading("Title", text="Заголовок заметки")
        self.note_tree.heading("Date", text="Дата")
        self.note_tree.heading("Category", text="Категория")
        self.note_tree.column("Title", width=450, stretch=True)  # Увеличиваем ширину
        self.note_tree.column("Date", width=150, stretch=True)
        self.note_tree.column("Category", width=150, stretch=True)
        self.note_tree.grid(row=13, column=0, columnspan=4, padx=5, pady=5, sticky="ew")  # Расширяем на 4 столбца
        self.note_tree.bind("<Double-1>", self.on_note_double_click)
        self.update_note_table()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
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

    def add_task(self):
        title = self.title_entry.get()
        due_date = self.due_date_var.get()
        category = self.category_var.get()
        if due_date == "Дата не выбрана":
            messagebox.showwarning("Ошибка", "Выберите дату!")
            return
        if not title:
            messagebox.showwarning("Ошибка", "Введите название задачи!")
            return
        try:
            datetime.strptime(due_date, "%Y-%m-%d %H:%M")
            task = Task(title, due_date, category)
            self.tasks.append(task)
            self.update_task_table()
            self.title_entry.delete(0, tk.END)
            self.due_date_var.set("Дата не выбрана")
            self.category_var.set("Без категории")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат даты!")

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
            top.geometry("600x500")

            tk.Label(top, text="Название задачи:").pack(pady=5)
            title_entry = tk.Entry(top, width=40)
            title_entry.insert(0, current_task.title)
            title_entry.pack(pady=5)

            tk.Label(top, text="Срок выполнения:").pack(pady=5)
            due_date_entry = tk.Entry(top, width=40)
            due_date_entry.insert(0, current_task.due_date)
            due_date_entry.pack(pady=5)

            tk.Label(top, text="Категория:").pack(pady=5)
            category_var = tk.StringVar(value=current_task.category)
            tk.OptionMenu(top, category_var, *self.categories).pack(pady=5)

            tk.Label(top, text="Комментарий:").pack(pady=5)
            comment_text = tk.Text(top, wrap="word", height=10)
            comment_text.insert("1.0", current_task.comment)
            comment_text.pack(pady=5, padx=10, expand=True, fill="both")

            def save_edited_task():
                new_title = title_entry.get().strip()
                new_due_date = due_date_entry.get().strip()
                new_category = category_var.get()
                new_comment = comment_text.get("1.0", tk.END).strip()
                if not new_title:
                    messagebox.showwarning("Ошибка", "Введите название задачи!")
                    return
                try:
                    datetime.strptime(new_due_date, "%Y-%m-%d %H:%M")
                    current_task.title = new_title
                    current_task.due_date = new_due_date
                    current_task.category = new_category
                    current_task.comment = new_comment
                    self.update_task_table()
                    top.destroy()
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверный формат даты! Используйте YYYY-MM-DD HH:MM")

            tk.Button(top, text="Сохранить", command=save_edited_task).pack(pady=10)
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
        self.task_tree.delete(*self.task_tree.get_children())
        now = datetime.now()
        for task in self.tasks:
            status = "✓" if task.completed else "✗"
            comment_status = "✓" if task.comment.strip() else ""
            time_spent = f"{task.time_spent // 60}м {task.time_spent % 60}с" if task.time_spent > 0 else ""
            due = datetime.strptime(task.due_date, "%Y-%m-%d %H:%M")
            if not task.completed and due < now:
                self.task_tree.insert("", "end", values=(
                task.title, task.due_date, task.category, status, comment_status, time_spent), tags=("overdue",))
            else:
                self.task_tree.insert("", "end", values=(
                task.title, task.due_date, task.category, status, comment_status, time_spent))

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
            "tasks": [{"title": t.title, "due_date": t.due_date, "category": t.category, "completed": t.completed,
                       "comment": t.comment, "time_spent": t.time_spent} for t in self.tasks],
            "notes": [{"text": n.text, "date": n.date, "category": n.category} for n in self.notes],
            "categories": self.categories,
            "free_time_entries": self.free_time_entries  # Добавляем свободные записи
        }
        if data["tasks"] or data["notes"] or data["categories"]:
            if os.path.exists("tasks.json"):
                shutil.copy("tasks.json", "tasks_backup.json")
            try:
                with open("tasks.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить данные: {e}")
                if os.path.exists("tasks_backup.json"):
                    shutil.copy("tasks_backup.json", "tasks.json")

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
                    if isinstance(data, list):  # Старый формат
                        self.tasks = [Task(t["title"], t["due_date"]) for t in data]
                        for i, task in enumerate(self.tasks):
                            task.completed = data[i]["completed"]
                        self.notes = []
                        self.categories = ["Без категории", "Работа", "Личное", "Срочное"]
                        self.free_time_entries = []
                    elif isinstance(data, dict):  # Новый формат
                        self.tasks = [
                            Task(t["title"], t["due_date"], t.get("category", "Без категории"), t.get("comment", ""),
                                 t.get("time_spent", 0)) for t in data.get("tasks", [])]
                        for i, task in enumerate(self.tasks):
                            task.completed = data["tasks"][i]["completed"]
                        self.notes = [Note(n["text"], n["date"], n.get("category", "Без категории")) for n in
                                      data.get("notes", [])]
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
            if os.path.exists("tasks_backup.json"):
                messagebox.showwarning("Внимание", "Основной файл повреждён, загружаю резервную копию.")
                try:
                    with open("tasks_backup.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self.tasks = [Task(t["title"], t["due_date"], t.get("category", "Без категории"),
                                               t.get("comment", ""), t.get("time_spent", 0)) for t in
                                          data.get("tasks", [])]
                            for i, task in enumerate(self.tasks):
                                task.completed = data["tasks"][i]["completed"]
                            self.notes = [Note(n["text"], n["date"], n.get("category", "Без категории")) for n in
                                          data.get("notes", [])]
                            self.categories = data.get("categories", ["Без категории", "Работа", "Личное", "Срочное"])
                            self.free_time_entries = data.get("free_time_entries", [])
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось загрузить резервную копию: {e}")

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

# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = PlannerApp(root)
    root.mainloop()