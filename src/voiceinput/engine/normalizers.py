import re

CN = "零〇一二两三四五六七八九十百千万亿点"
DIGITS = dict(zip("零一二三四五六七八九", range(10))) | {"〇": 0, "两": 2}


def chinese_number(text):
    if "点" in text:
        a, b = text.split("点", 1)
        if not a or not b or any(c not in DIGITS for c in b):
            raise ValueError("不完整的小数")
        return chinese_number(a) + "." + "".join(str(DIGITS[c]) for c in b)
    if all(c in DIGITS for c in text):
        return "".join(str(DIGITS[c]) for c in text)
    total = section = digit = 0
    for c in text:
        if c in DIGITS:
            digit = DIGITS[c]
        elif c in "十百千":
            section += (digit or 1) * {"十": 10, "百": 100, "千": 1000}[c]
            digit = 0
        else:
            section += digit
            total = (total + section) * {"万": 10000, "亿": 100000000}[c]
            section = digit = 0
    return str(total + section + digit)


def number_normalizer(text):
    def convert(m):
        try:
            return chinese_number(m.group(0))
        except (KeyError, ValueError):
            return m.group(0)
    def percent(m):
        try:
            return chinese_number(m[1]) + "%"
        except (KeyError, ValueError):
            return m[0]
    def interval(m):
        try:
            return chinese_number(m[1]) + "～" + chinese_number(m[2])
        except (KeyError, ValueError):
            return m[0]
    text = re.sub(f"百分之([{CN}]+)", percent, text)
    text = re.sub(f"([{CN}]+)(?:到|至)([{CN}]+)", interval, text)
    if re.fullmatch(f"[{CN}]+", text):
        return convert(re.match(f"[{CN}]+", text))
    units = "摄氏度|度|标准立方米每小时|标方每小时|毫升每分钟|克每立方厘米|兆焦每平方米|分钟|小时|秒|米|毫升|千克|克|℃|Nm³/h|mL/min|g/cm³|MJ/m²|%"
    return re.sub(f"[{CN}]+(?=\\s*(?:{units}))", convert, text)


UNITS = {"标准立方米每小时": "Nm³/h", "标方每小时": "Nm³/h", "毫升每分钟": "mL/min", "克每立方厘米": "g/cm³", "兆焦每平方米": "MJ/m²", "摄氏度": "℃", "分钟": "min"}


def unit_normalizer(text):
    for source, target in UNITS.items():
        text = text.replace(source, target)
    text = re.sub(r"(温度(?:为|是)?\s*\d+(?:\.\d+)?(?:～\d+(?:\.\d+)?)?)度", r"\1℃", text)
    text = re.sub(r"(\d)\s*℃(?:到|至|～)\s*(\d+(?:\.\d+)?)\s*℃", r"\1～\2 ℃", text)
    return re.sub(r"(\d)\s*(Nm³/h|mL/min|g/cm³|MJ/m²|℃|min)", r"\1 \2", text)


def punctuation_filter(text):
    text = re.sub(r"(?<=[\u4e00-\u9fff]),", "，", text)
    text = re.sub(r"([，。！？；])\1+", r"\1", text).strip()
    if text and text[-1] not in "。！？.!?…：:；;":
        text += "。"
    return text
