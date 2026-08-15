def get_ai_response(message, memory):
    text = message.strip()
    clean = text.replace("؟", "").replace("?", "").strip()

    # ===== ASK NAME =====
    if "اسمي" in clean and ("ايه" in clean or "إيه" in clean):
        for item in memory:
            if item.startswith("اسم المستخدم: "):
                return "اسمك " + item.replace("اسم المستخدم: ", "")
        return "لسه مش عارفة اسمك."

    # ===== ASK WHAT USER IS LEARNING =====
    if "بتعلم" in clean and ("ايه" in clean or "إيه" in clean):
        for item in reversed(memory):
            if item.startswith("معلومة: ") and "بتعلم" in item:
                info = item.replace("معلومة: ", "").strip()

                if "أنا بتعلم " in info:
                    return "أنت بتتعلم " + info.split("أنا بتعلم ", 1)[1]

                if "انا بتعلم " in info:
                    return "أنت بتتعلم " + info.split("انا بتعلم ", 1)[1]

        return "لسه مش عارفة إنت بتتعلم إيه."

    # ===== ASK WHAT USER LIKES =====
    if "بحب ايه" in clean or "بحب إيه" in clean:
        for item in reversed(memory):
            if item.startswith("حاجة بحبها: "):
                return "أنت بتحب " + item.replace("حاجة بحبها: ", "")
        return "لسه مش عارفة إنت بتحب إيه."

    # ===== SAVE NAME =====
    if text.startswith("اسمي "):
        name = text[5:].strip()

        if name:
            memory[:] = [
                item for item in memory
                if not item.startswith("اسم المستخدم:")
            ]

            memory.append("اسم المستخدم: " + name)
            return "تمام، هفتكر إن اسمك " + name

    # ===== SAVE LEARNING =====
    if "بتعلم" in text or "بتدرس" in text:
        memory[:] = [
            item for item in memory
            if not item.startswith("معلومة: ")
        ]

        memory.append("معلومة: " + text)
        return "تمام، هفتكر المعلومة دي."

    # ===== SAVE LIKES =====
    if "بحب " in text:
        thing = text.split("بحب ", 1)[1].strip()

        if thing:
            memory[:] = [
                item for item in memory
                if not item.startswith("حاجة بحبها:")
            ]

            memory.append("حاجة بحبها: " + thing)
            return "تمام، هفتكر إنك بتحب " + thing

    # ===== GREETINGS =====
    if clean in ["اهلا", "أهلا", "السلام عليكم", "سلام عليكم"]:
        return "أهلاً! أنا بيرلا."

    # ===== ABOUT PERLA =====
    if "اسمك" in text or "مين انتي" in text or "من انتي" in text:
        return "أنا بيرلا، مساعدتك الشخصية."

    # ===== HOW ARE YOU =====
    if "اخبارك" in text or "عاملة ايه" in text or "عامله ايه" in text:
        return "تمام، جاهزة."

    # ===== SHOW MEMORY =====
    if "ذاكرة" in text or "فاكرة ايه" in text:
        if not memory:
            return "لسه مفيش ذكريات محفوظة."

        return "أنا فاكرة: " + " | ".join(memory)

    # ===== ENGLISH =====
    if clean.lower() in ["hello", "hi"]:
        return "Hello! Perla is here."

    if clean.lower() == "who are you":
        return "I'm Perla, your personal AI assistant."

    return "فهمت كلامك، لكن عقلي الذكي الحقيقي لسه مش متوصل."