import re


class PerlaRouter:

    def choose(
        self,
        message="",
        has_image=False,
        has_audio=False,
        has_video=False
    ):

        message = (message or "").lower().strip()

        if has_audio:
            return "audio"

        if has_video:
            return "vision"

        if has_image:
            return "vision"

        word_patterns = [
            "ملف وورد", "وورد", "مستند وورد", "docx",
            "اعمل ملف وورد", "ابعتلي وورد", "اكتبه في وورد",
            "حول ده لوورد", "طلعلي وورد",
        ]

        if self._contains_any(message, word_patterns):
            return "file_word"

        pdf_patterns = [
            "بي دي اف", "بي دى اف", "pdf",
            "ملف pdf", "اعمل ملف pdf", "طلعلي pdf", "حوله pdf",
        ]

        if self._contains_any(message, pdf_patterns):
            return "file_pdf"

        pptx_patterns = [
            "باوربوينت", "بوربوينت", "بور بوينت", "بريزنتيشن",
            "عرض تقديمي", "pptx", "سلايدات", "سلايد شو",
            "اعمل عرض", "اعمل برزنتيشن",
        ]

        if self._contains_any(message, pptx_patterns):
            return "file_pptx"

        image_gen_patterns = [
            "ولد صورة", "ولدلي صورة", "اعملي صورة", "اعمل صورة",
            "صمملي صورة", "ارسم", "ارسملي", "طلعلي صورة",
            "generate image", "image generation",
        ]

        if self._contains_any(message, image_gen_patterns):
            return "image_generate"

        coding_patterns = [
            r"\bpython\b",
            r"\bjavascript\b",
            r"\btypescript\b",
            r"\bhtml\b",
            r"\bcss\b",
            r"\bfastapi\b",
            r"\bapi\b",
            r"\bjson\b",
            r"\bsql\b",
            r"\bgithub\b",
            r"\bcode\b",
            r"\bbug\b",
            r"\bdebug\b",
            r"\berror\b",
            "كود",
            "الكود",
            "برمجة",
            "برنامج",
            "سكريبت",
            "بايثون",
            "جافاسكربت",
            "تايب سكريبت",
            "فاست اي بي اي",
            "خطأ في الكود",
            "صلح الكود",
            "اصلح الكود",
            "عدّل الكود",
            "عدل الكود",
            "اكتب كود",
            "اعمل كود",
            "برمج",
        ]

        if self._contains_any(message, coding_patterns):
            return "coding"

        math_patterns = [
            r"(?<!\d)\d{1,6}\s*[\+\-\*/]\s*\d{1,6}(?!\d)",
            r"\d+\s*%\s*(من|of)?\s*\d+",
            r"\d+\s*÷\s*\d+",
            r"\d+\s*×\s*\d+",
            "احسب",
            "احسبي",
            "حساب",
            "معادلة",
            "نسبة مئوية",
            "نسبه مئويه",
            "بالمية",
            "بالمئه",
            "في المية",
            "في المئه",
            "مساحة",
            "مساحه",
            "حجم الشكل",
            "محيط الشكل",
            "متوسط الأرقام",
            "جذر تربيعي",
            "احتمال رياضي",
        ]

        if self._contains_any(message, math_patterns):
            return "math"

        research_patterns = [
            "ابحث",
            "إبحث",
            "بحث",
            "دور على",
            "دورلي",
            "دور لي",
            "هاتلي معلومات",
            "هات لي معلومات",
            "معلومات عن",
            "مصادر",
            "مصدر",
            "آخر الأخبار",
            "اخر الاخبار",
            "أحدث",
            "احدث",
            "السوق",
            "المنافسين",
            "المنافسة",
            "منافسة",
            "دراسة السوق",
            "أسعار",
            "اسعار",
            "سعر اليوم",
            "آخر سعر",
            "اخر سعر",
        ]

        if self._contains_any(message, research_patterns):
            return "research"

        reasoning_patterns = [
            "حلل",
            "حللي",
            "تحليل",
            "قارن",
            "مقارنة",
            "خطط",
            "تخطيط",
            "خطة",
            "استراتيجية",
            "استراتيجيه",
            "دراسة جدوى",
            "تمويل المشروع",
            "قرار استثماري",
            "أيه الأفضل",
            "ايه الأفضل",
            "إيه الأفضل",
            "ايه الاحسن",
            "إيه الأحسن",
            "بالتفصيل",
            "بعمق",
            "حل المشكلة",
            "ساعدني أقرر",
            "ساعدني اقرر",
            "فكر معايا",
            "فكرلي",
            "اعمل تحليل",
            "اعمل مقارنة",
        ]

        if self._contains_any(message, reasoning_patterns):
            return "reasoning"

        creative_patterns = [
            "اكتبلي",
            "اكتب لي",
            "اكتبلي بوست",
            "اكتب بوست",
            "صمم",
            "تصميم",
            "كريتيف",
            "إبداع",
            "ابداع",
            "اسم براند",
            "اسم للبراند",
            "لوجو",
            "شعار",
            "إعلان",
            "اعلان",
            "سيناريو",
            "قصة",
            "فكرة إعلان",
            "فكرة اعلان",
            "محتوى",
            "كونتنت",
        ]

        if self._contains_any(message, creative_patterns):
            return "creative"

        word_count = len(message.split())

        if word_count >= 25:
            return "reasoning"

        return "fast"

    @staticmethod
    def _contains_any(message, patterns):
        for pattern in patterns:
            try:
                if re.search(pattern, message, re.IGNORECASE):
                    return True
            except re.error:
                if pattern in message:
                    return True
        return False


router = PerlaRouter()
