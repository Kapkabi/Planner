# -*- coding: utf-8 -*-
import json
import os


def convert_old_to_new():
    input_file = "tasks_old.json"
    output_file = "tasks.json"

    # Проверяем наличие старого файла
    if not os.path.exists(input_file):
        print(f"Ошибка: Файл {input_file} не найден!")
        return

    try:
        # Читаем старый файл
        with open(input_file, "r", encoding="utf-8") as f:
            old_data = json.load(f)

        # Проверяем, что данные в формате словаря
        if not isinstance(old_data, dict) or "tasks" not in old_data:
            print(f"Ошибка: {input_file} не в ожидаемом формате (должен быть словарь с 'tasks')!")
            return

        # Преобразуем задачи, добавляя time_spent
        tasks = []
        for old_task in old_data.get("tasks", []):
            task = {
                "title": old_task["title"],
                "due_date": old_task["due_date"],
                "category": old_task.get("category", "Без категории"),
                "comment": old_task.get("comment", ""),
                "time_spent": 0,  # Добавляем недостающее поле
                "completed": old_task.get("completed", False)
            }
            tasks.append(task)

        # Заметки остаются без изменений
        notes = old_data.get("notes", [])

        # Категории берём из старого файла или используем дефолтные
        categories = old_data.get("categories", ["Без категории", "Работа", "Личное", "Срочное"])

        # Формируем новый словарь с free_time_entries
        new_data = {
            "tasks": tasks,
            "notes": notes,
            "categories": categories,
            "free_time_entries": []  # Добавляем пустой список
        }

        # Сохраняем в новый файл
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)

        print(f"Успешно преобразовано! Данные из {input_file} сохранены в {output_file}")

    except json.JSONDecodeError as e:
        print(f"Ошибка: Не удалось разобрать {input_file}: {e}")
    except KeyError as e:
        print(f"Ошибка: В {input_file} отсутствует обязательное поле {e}")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")


if __name__ == "__main__":
    convert_old_to_new()