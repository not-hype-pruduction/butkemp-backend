import random
import re
import os
from xml.etree import ElementTree as ET

# Система редкости с весами
RARITY_WEIGHTS = {
    "обычный": 60,  # 60%
    "необычный": 25,  # 25%
    "редкий": 10,  # 10%
    "эпический": 4,  # 4%
    "легендарный": 1  # 1%
}

# Расширенные цветовые палитры с редкостью
COLOR_PALETTES = {
    "body": {
        "обычный": ["#E39D3A", "#5C9EAD", "#8FB339"],
        "необычный": ["#7C73E6", "#FF6B6B", "#4FB286", "#D972FF"],
        "редкий": ["#FF4500", "#32CD32", "#9370DB", "#40E0D0"],
        "эпический": ["#00BFFF", "#FF69B4", "#FFD700", "#8A2BE2"],
        "легендарный": ["#FF00FF", "#1E90FF", "#00FF7F", "#FF1493"]
    },
    "stroke": {
        "обычный": ["#8A5C1E", "#2C5D73", "#5A7324"],
        "необычный": ["#4A3D9D", "#B54B4B", "#2A735A", "#8A3DAD"],
        "редкий": ["#B32D00", "#228B22", "#663399", "#20B2AA"],
        "эпический": ["#0080FF", "#C71585", "#DAA520", "#551A8B"],
        "легендарный": ["#8B008B", "#0000CD", "#006400", "#8B0000"]
    }
}

# Специфические цвета для типов шапок
HAT_COLORS = {
    "Классическая шапка": {
        "обычный": ["#FFFFFF", "#F5F5F5", "#EFEFEF"],
        "необычный": ["#FFD6D6", "#D6EEFF", "#EEFFD6"],
        "редкий": ["#FFB6C1", "#AFEEEE", "#FFDAB9"],
        "эпический": ["#FFC0CB", "#87CEFA", "#FFFACD"],
        "легендарный": ["#FFFF00", "#FF00FF", "#00FFFF"]
    },
    "Простая кепка": {
        "обычный": ["#E8E8E8", "#D1D1D1", "#C0C0C0"],
        "необычный": ["#AED6F1", "#F5CBA7", "#D2B4DE"],
        "редкий": ["#F9E79F", "#ABEBC6", "#F5B7B1"],
        "эпический": ["#BB8FCE", "#85C1E9", "#F8C471"],
        "легендарный": ["#F1948A", "#7FB3D5", "#73C6B6"]
    },
    "Шляпа с полями": {
        "обычный": ["#F5F5DC", "#E0E0E0", "#D0D0D0"],
        "необычный": ["#FAD7A0", "#82E0AA", "#D7BDE2"],
        "редкий": ["#A9CCE3", "#F5B041", "#A3E4D7"],
        "эпический": ["#85C1E9", "#F1948A", "#7DCEA0"],
        "легендарный": ["#F4D03F", "#EC7063", "#3498DB"]
    },
    "Шапка с помпоном": {
        "обычный": ["#FAF0E6", "#F0E68C", "#E6E6FA"],
        "необычный": ["#FADBD8", "#D6EAF8", "#D4EFDF"],
        "редкий": ["#F5CBA7", "#D2B4DE", "#A9DFBF"],
        "эпический": ["#F8C471", "#85C1E9", "#BB8FCE"],
        "легендарный": ["#F5B041", "#EC7063", "#3498DB"]
    },
    "Ковбойская шляпа": {
        "обычный": ["#D2B48C", "#BC8F8F", "#F5DEB3"],
        "необычный": ["#CD853F", "#DEB887", "#D2B48C"],
        "редкий": ["#B87333", "#8B4513", "#A0522D"],
        "эпический": ["#800000", "#8B0000", "#A52A2A"],
        "легендарный": ["#FFD700", "#DAA520", "#B8860B"]
    },
    "Цилиндр": {
        "обычный": ["#000000", "#1A1A1A", "#2C2C2C"],
        "необычный": ["#191970", "#00008B", "#0000CD"],
        "редкий": ["#4B0082", "#800080", "#8B008B"],
        "эпический": ["#483D8B", "#4169E1", "#0000FF"],
        "легендарный": ["#00FFFF", "#00CED1", "#5F9EA0"]
    },
    "Корона": {
        "обычный": ["#FFD700", "#FFC125", "#FFA500"],
        "необычный": ["#FFDF00", "#FFD700", "#FFCC00"],
        "редкий": ["#D4AF37", "#CFB53B", "#FFDF00"],
        "эпический": ["#FAFAD2", "#EEE8AA", "#F0E68C"],
        "легендарный": ["#E6BE8A", "#CD7F32", "#996515"]
    },
    "Шлем рыцаря": {
        "обычный": ["#708090", "#778899", "#A9A9A9"],
        "необычный": ["#B0C4DE", "#B0E0E6", "#ADD8E6"],
        "редкий": ["#4682B4", "#5F9EA0", "#7B68EE"],
        "эпический": ["#4169E1", "#0000CD", "#00008B"],
        "легендарный": ["#00BFFF", "#6A5ACD", "#483D8B"]
    },
    "Волшебная шляпа": {
        "обычный": ["#663399", "#9370DB", "#8A2BE2"],
        "необычный": ["#9932CC", "#BA55D3", "#DA70D6"],
        "редкий": ["#8B008B", "#9400D3", "#8A2BE2"],
        "эпический": ["#4B0082", "#800080", "#9932CC"],
        "легендарный": ["#6A0DAD", "#9400D3", "#9370DB"]
    },
    "Космический шлем": {
        "обычный": ["#B0C4DE", "#87CEFA", "#ADD8E6"],
        "необычный": ["#00BFFF", "#1E90FF", "#4682B4"],
        "редкий": ["#4169E1", "#0000FF", "#0000CD"],
        "эпический": ["#483D8B", "#6A5ACD", "#7B68EE"],
        "легендарный": ["#8A2BE2", "#9932CC", "#9400D3"]
    }
}

# Расширенные варианты шапочек с редкостью
HAT_VARIANTS = {
    "обычный": [
        # Оригинальная шапочка
        {
            "name": "Классическая шапка",
            "path1": "M113.5 84C90.8 84 79.45 102 79.45 114H147.55C147.55 102 136.2 84 113.5 84Z",
            "path2": "M141.875 108H85.125C81.9907 108 79.45 110.686 79.45 114C79.45 117.314 81.9907 120 85.125 120H141.875C145.009 120 147.55 117.314 147.55 114C147.55 110.686 145.009 108 141.875 108Z",
        },
        # Простая кепка
        {
            "name": "Простая кепка",
            "path1": "M113.5 84C90.8 84 79.45 102 79.45 114H147.55C147.55 102 136.2 84 113.5 84Z",
            "path2": "M147.55 102H79.45C79.45 108 85.125 114 85.125 114H141.875C141.875 114 147.55 108 147.55 102Z",
        },
    ],
    "необычный": [
        # Шляпа с полями
        {
            "name": "Шляпа с полями",
            "path1": "M75 98C75 90 90 80 113.5 80C137 80 152 90 152 98C152 100 150 102 146 102H81C77 102 75 100 75 98Z",
            "path2": "M141.875 102H85.125C81.9907 102 79.45 106 79.45 110C79.45 114 81.9907 118 85.125 118H141.875C145.009 118 147.55 114 147.55 110C147.55 106 145.009 102 141.875 102Z",
        },
        # Шапка с помпоном
        {
            "name": "Шапка с помпоном",
            "path1": "M113.5 82C90.8 82 79.45 100 79.45 112H147.55C147.55 100 136.2 82 113.5 82Z",
            "path2": "M113.5 76C118 76 122 80 122 84C122 88 118 92 113.5 92C109 92 105 88 105 84C105 80 109 76 113.5 76Z",
        },
    ],
    "редкий": [
        # Ковбойская шляпа
        {
            "name": "Ковбойская шляпа",
            "path1": "M70 94C70 86 90 75 113.5 75C137 75 157 86 157 94C157 96 155 98 151 98H76C72 98 70 96 70 94Z",
            "path2": "M113.5 75C106 75 100 84 100 84C100 84 108 90 113.5 90C119 90 127 84 127 84C127 84 121 75 113.5 75Z",
        },
        # Цилиндр
        {
            "name": "Цилиндр",
            "path1": "M100 85C100 77 106 70 113.5 70C121 70 127 77 127 85V105H100V85Z",
            "path2": "M92 105C92 105 97 110 113.5 110C130 110 135 105 135 105H92Z",
        },
    ],
    "эпический": [
        # Корона
        {
            "name": "Корона",
            "path1": "M85 100L95 80L105 95L113.5 75L122 95L132 80L142 100H85Z",
            "path2": "M85 100H142V110H85V100Z",
        },
        # Шлем рыцаря
        {
            "name": "Шлем рыцаря",
            "path1": "M113.5 75C90 75 80 90 80 110C80 114 85 120 90 120H137C142 120 147 114 147 110C147 90 137 75 113.5 75Z",
            "path2": "M113.5 75V95M103.5 85H123.5",
        },
    ],
    "легендарный": [
        # Волшебная шляпа
        {
            "name": "Волшебная шляпа",
            "path1": "M75 110C75 90 90 65 113.5 65C137 65 152 90 152 110H75Z",
            "path2": "M113.5 65C110 55 116 45 125 40C130 55 123 60 113.5 65Z",
        },
        # Космический шлем
        {
            "name": "Космический шлем",
            "path1": "M85 114C85 90 97 75 113.5 75C130 75 142 90 142 114C142 118 137 120 131 120H96C90 120 85 118 85 114Z",
            "path2": "M90 100C90 90 100 85 113.5 85C127 85 137 90 137 100V110H90V100Z",
        },
    ]
}


def select_by_rarity():
    """Выбирает редкость на основе весов"""
    rarities = list(RARITY_WEIGHTS.keys())
    weights = list(RARITY_WEIGHTS.values())
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    return chosen_rarity


def load_svg(file_path):
    """Загружает SVG файл как текст"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def modify_svg_colors(svg_content):
    """Изменяет цвета в SVG с учетом редкости"""
    # Выбираем редкость для каждого элемента
    body_rarity = select_by_rarity()
    stroke_rarity = select_by_rarity()

    # Выбираем случайные цвета из соответствующих палитр по редкости
    body_color = random.choice(COLOR_PALETTES["body"][body_rarity])
    stroke_color = random.choice(COLOR_PALETTES["stroke"][stroke_rarity])

    # Заменяем цвета в градиенте (основной цвет тела)
    modified_svg = re.sub(
        r'<stop offset="1" stop-color="#E39D3A"/>',
        f'<stop offset="1" stop-color="{body_color}"/>',
        svg_content
    )

    # Заменяем цвет обводки
    modified_svg = re.sub(
        r'stroke="#8A5C1E"',
        f'stroke="{stroke_color}"',
        modified_svg
    )

    return modified_svg, {
        "body": {"color": body_color, "rarity": body_rarity},
        "stroke": {"color": stroke_color, "rarity": stroke_rarity}
    }


def replace_hat(svg_content, hat_rarity=None):
    """Заменяет шапку на новую с учетом редкости и смещением по вертикали"""
    if hat_rarity is None:
        hat_rarity = select_by_rarity()

    # Выбираем случайную шапку из соответствующей категории редкости
    hat_variant = random.choice(HAT_VARIANTS[hat_rarity])
    hat_name = hat_variant["name"]

    # Выбираем цвет шапки соответствующий её типу и редкости
    hat_color = random.choice(HAT_COLORS[hat_name][hat_rarity])
    hat_stroke_color = "#AAAAAA"

    # Добавляем смещение по вертикали в зависимости от типа шапки
    y_offset = {
        "Классическая шапка": 0,
        "Простая кепка": -5,
        "Шляпа с полями": 10,
        "Шапка с помпоном": 10,
        "Ковбойская шляпа": 15,
        "Цилиндр": 5,
        "Корона": 10,
        "Шлем рыцаря": 5,
        "Волшебная шляпа": 15,
        "Космический шлем": 15
    }.get(hat_name, 0)

    # Применяем смещение к SVG с помощью группы и трансформации
    hat_group = f'<g transform="translate(0, {y_offset})">'
    hat_paths = f'<path d="{hat_variant["path1"]}" fill="{hat_color}" stroke="{hat_stroke_color}" stroke-width="3"/>'
    hat_paths += f'<path d="{hat_variant["path2"]}" fill="{hat_color}" stroke="{hat_stroke_color}" stroke-width="3"/>'
    hat_group += hat_paths + '</g>'

    # Заменяем старые пути шапки на новую группу с трансформацией
    modified_svg = re.sub(
        r'<path d="M113.5 84C90.8 84 79.45 102 79.45 114H147.55C147.55 102 136.2 84 113.5 84Z"[^/]+/>\s*<path d="M141.875 108H85.125C81.9907 108[^/]+/>',
        hat_group,
        svg_content
    )

    return modified_svg, {"name": hat_name, "rarity": hat_rarity, "color": hat_color}

def generate_mascot_variations(input_svg_path, output_dir, count=5):
    """Генерирует несколько вариаций маскота с учетом редкости элементов"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    svg_content = load_svg(input_svg_path)

    for i in range(count):
        # Модифицируем цвета
        modified_svg, color_info = modify_svg_colors(svg_content)

        # Выбираем редкость шапки
        hat_rarity = select_by_rarity()

        # Заменяем шапку специфическими цветами
        modified_svg, hat_info = replace_hat(modified_svg, hat_rarity)

        # Сохраняем новый SVG
        output_file = os.path.join(output_dir, f"mascot_variation_{i + 1}.svg")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(modified_svg)

        # Выводим информацию о созданном маскоте и его элементах
        print(f"Создан новый маскот #{i + 1}: {output_file}")
        print(f"  Шапка: {hat_info['name']} ({hat_info['rarity'].capitalize()}) - цвет: {hat_info['color']}")
        print(f"  Цвет тела: {color_info['body']['color']} ({color_info['body']['rarity'].capitalize()})")
        print(f"  Цвет обводки: {color_info['stroke']['color']} ({color_info['stroke']['rarity'].capitalize()})")


if __name__ == "__main__":
    input_svg = "маскот-1.svg"
    output_directory = "generated_mascots"

    # Количество маскотов для генерации
    mascot_count = 10

    # Генерируем новые вариации маскота
    generate_mascot_variations(input_svg, output_directory, mascot_count)
    print(f"\nСгенерировано {mascot_count} новых маскотов в папке: {output_directory}")